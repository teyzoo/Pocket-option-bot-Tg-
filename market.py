from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import pandas as pd

from config import (
    MAX_CANDLES,
    TWELVE_DATA_API_KEY,
    TWELVE_DATA_BASE_URL,
    TWELVE_DATA_CACHE_SECONDS,
    TWELVE_DATA_TIMEOUT,
)


class MarketAPIError(Exception):
    """
    Ошибка получения рыночных данных.
    """


class MarketClient:
    """
    Клиент Twelve Data.

    Поддерживает:

    - получение свечей;
    - получение текущей цены;
    - force_refresh;
    - получение цены закрытия на момент expiry;
    - закрытие HTTP-клиента;
    - небольшой TTL-кэш.
    """

    def __init__(self) -> None:
        self.base_url = (
            TWELVE_DATA_BASE_URL.rstrip("/")
        )

        self.timeout = httpx.Timeout(
            TWELVE_DATA_TIMEOUT
        )

        self._lock = asyncio.Lock()

        self._client: httpx.AsyncClient | None = None

        self._cache: dict[
            tuple[str, str, int],
            tuple[float, pd.DataFrame],
        ] = {}

    # ========================================================
    # HTTP CLIENT
    # ========================================================

    def _get_http_client(
        self,
    ) -> httpx.AsyncClient:
        if (
            self._client is None
            or self._client.is_closed
        ):
            self._client = httpx.AsyncClient(
                timeout=self.timeout
            )

        return self._client

    # ========================================================
    # REQUEST
    # ========================================================

    async def _request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        request_params = dict(
            params
        )

        request_params[
            "apikey"
        ] = TWELVE_DATA_API_KEY

        async with self._lock:
            client = self._get_http_client()

            try:
                response = await client.get(
                    f"{self.base_url}/time_series",
                    params=request_params,
                )

                response.raise_for_status()

            except httpx.HTTPError as exc:
                raise MarketAPIError(
                    f"Twelve Data HTTP error: {exc}"
                ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise MarketAPIError(
                "Twelve Data returned invalid JSON"
            ) from exc

        if data.get("status") == "error":
            raise MarketAPIError(
                data.get(
                    "message",
                    "Twelve Data API error",
                )
            )

        if "values" not in data:
            raise MarketAPIError(
                "No market values returned"
            )

        return data

    # ========================================================
    # CANDLES
    # ========================================================

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1min",
        outputsize: int = MAX_CANDLES,
        force_refresh: bool = False,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Получает свечи.

        force_refresh=True полностью игнорирует кэш.

        **kwargs оставлен для совместимости со старыми
        вызовами модулей проекта.
        """

        try:
            outputsize = int(
                outputsize
            )
        except (
            TypeError,
            ValueError,
        ):
            outputsize = MAX_CANDLES

        outputsize = max(
            1,
            min(
                MAX_CANDLES,
                outputsize,
            ),
        )

        cache_key = (
            symbol,
            interval,
            outputsize,
        )

        now = time.monotonic()

        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        if not force_refresh:
            cached = self._cache.get(
                cache_key
            )

            if cached is not None:
                cached_at, cached_df = cached

                if (
                    TWELVE_DATA_CACHE_SECONDS > 0
                    and (
                        now - cached_at
                    )
                    < TWELVE_DATA_CACHE_SECONDS
                ):
                    return cached_df.copy()

        # ----------------------------------------------------
        # REQUEST
        # ----------------------------------------------------

        data = await self._request(
            {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "timezone": "UTC",
                "format": "JSON",
            }
        )

        values = data.get(
            "values",
            [],
        )

        if not values:
            raise MarketAPIError(
                f"No candles for {symbol}"
            )

        rows: list[
            dict[str, Any]
        ] = []

        for item in values:
            try:
                rows.append(
                    {
                        "datetime": pd.to_datetime(
                            item["datetime"],
                            utc=True,
                        ),
                        "open": float(
                            item["open"]
                        ),
                        "high": float(
                            item["high"]
                        ),
                        "low": float(
                            item["low"]
                        ),
                        "close": float(
                            item["close"]
                        ),
                        "volume": float(
                            item.get(
                                "volume",
                                0,
                            )
                            or 0
                        ),
                    }
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                # Пропускаем битую свечу.
                continue

        df = pd.DataFrame(
            rows
        )

        if df.empty:
            raise MarketAPIError(
                f"No valid candles for {symbol}"
            )

        # ----------------------------------------------------
        # SORT
        # ----------------------------------------------------

        df = (
            df.sort_values(
                "datetime"
            )
            .drop_duplicates(
                subset=["datetime"],
                keep="last",
            )
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        if TWELVE_DATA_CACHE_SECONDS > 0:
            self._cache[
                cache_key
            ] = (
                now,
                df.copy(),
            )

        return df

    # ========================================================
    # PRICE
    # ========================================================

    async def get_price(
        self,
        symbol: str,
    ) -> float:
        df = await self.get_candles(
            symbol=symbol,
            interval="1min",
            outputsize=1,
            force_refresh=True,
        )

        return float(
            df.iloc[-1]["close"]
        )

    # ========================================================
    # EXPIRY CLOSE
    # ========================================================

    def get_close_for_expiry(
        self,
        candles: pd.DataFrame,
        expiry,
    ) -> float | None:
        """
        Находит цену закрытия свечи,
        соответствующей времени экспирации.

        Логика:

        1. приводим datetime к UTC;
        2. ищем свечу с timestamp <= expiry;
        3. если её нет — берём ближайшую после expiry;
        4. возвращаем close.
        """

        if (
            candles is None
            or candles.empty
        ):
            return None

        if "datetime" not in candles.columns:
            return None

        if "close" not in candles.columns:
            return None

        try:
            expiry_dt = pd.to_datetime(
                expiry,
                utc=True,
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        df = candles.copy()

        try:
            df["datetime"] = pd.to_datetime(
                df["datetime"],
                utc=True,
            )
        except Exception:
            return None

        df = (
            df.dropna(
                subset=[
                    "datetime",
                    "close",
                ]
            )
            .sort_values(
                "datetime"
            )
            .reset_index(drop=True)
        )

        if df.empty:
            return None

        # ----------------------------------------------------
        # Идеальная свеча.
        # ----------------------------------------------------

        before_or_equal = df[
            df["datetime"] <= expiry_dt
        ]

        if not before_or_equal.empty:
            row = before_or_equal.iloc[-1]

            try:
                return float(
                    row["close"]
                )
            except (
                TypeError,
                ValueError,
            ):
                return None

        # ----------------------------------------------------
        # Если timestamp раньше всех свечей,
        # берём ближайшую доступную.
        # ----------------------------------------------------

        after = df[
            df["datetime"] >= expiry_dt
        ]

        if not after.empty:
            try:
                return float(
                    after.iloc[0]["close"]
                )
            except (
                TypeError,
                ValueError,
            ):
                return None

        return None

    # ========================================================
    # CACHE CONTROL
    # ========================================================

    def clear_cache(self) -> None:
        self._cache.clear()

    # ========================================================
    # CLOSE
    # ========================================================

    async def close(self) -> None:
        """
        Закрывает HTTP-клиент.
        """

        if self._client is not None:
            if not self._client.is_closed:
                await self._client.aclose()

            self._client = None

        self._cache.clear()


# ============================================================
# GLOBAL CLIENT
# ============================================================

market_client = MarketClient()
