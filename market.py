from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Iterable, List, Optional

import httpx
import pandas as pd

from config import TWELVE_DATA_API_KEY


logger = logging.getLogger("market")


TWELVE_DATA_URL = (
    "https://api.twelvedata.com/time_series"
)

MAX_CONCURRENT_REQUESTS = 4
REQUEST_TIMEOUT = 25.0
MAX_RETRIES = 3
CACHE_TTL_SECONDS = 12.0

DEFAULT_INTERVAL = "1min"
DEFAULT_OUTPUTSIZE = 500


class MarketClient:
    """
    Клиент Twelve Data.

    Возможности:
    - получение свечей;
    - получение текущей цены;
    - batch-загрузка;
    - TTL-кэш;
    - ограничение параллельных запросов;
    - повтор сетевых ошибок;
    - защита от перегрузки Twelve Data.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_concurrent_requests: int = (
            MAX_CONCURRENT_REQUESTS
        ),
    ) -> None:

        self.api_key = (
            api_key
            or TWELVE_DATA_API_KEY
        )

        if not self.api_key:
            raise RuntimeError(
                "TWELVE_DATA_API_KEY is not configured"
            )

        self._client: Optional[
            httpx.AsyncClient
        ] = None

        self._semaphore = asyncio.Semaphore(
            max(
                1,
                int(max_concurrent_requests),
            )
        )

        self._cache: Dict[
            str,
            tuple[float, pd.DataFrame],
        ] = {}

        self._cache_lock = asyncio.Lock()
        self._client_lock = asyncio.Lock()

    async def _get_client(
        self,
    ) -> httpx.AsyncClient:

        if self._client is not None:
            return self._client

        async with self._client_lock:

            if self._client is None:

                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=10.0,
                        read=REQUEST_TIMEOUT,
                        write=10.0,
                        pool=10.0,
                    ),
                    limits=httpx.Limits(
                        max_connections=(
                            MAX_CONCURRENT_REQUESTS
                        ),
                        max_keepalive_connections=(
                            MAX_CONCURRENT_REQUESTS
                        ),
                        keepalive_expiry=20.0,
                    ),
                    headers={
                        "User-Agent": (
                            "TEYZOO-Signal-Bot/2.0"
                        ),
                        "Accept": (
                            "application/json"
                        ),
                    },
                    follow_redirects=True,
                )

        return self._client

    @staticmethod
    def normalize_symbol(
        symbol: str,
    ) -> str:

        value = str(symbol).strip().upper()

        value = value.replace(
            "-",
            "/",
        )

        value = value.replace(
            "_",
            "/",
        )

        if (
            "/" not in value
            and len(value) == 6
        ):
            value = (
                f"{value[:3]}/"
                f"{value[3:]}"
            )

        return value

    @staticmethod
    def _cache_key(
        symbol: str,
        interval: str,
        outputsize: int,
    ) -> str:

        return (
            f"{symbol.upper()}|"
            f"{interval}|"
            f"{int(outputsize)}"
        )

    async def _get_cached(
        self,
        key: str,
    ) -> Optional[pd.DataFrame]:

        async with self._cache_lock:

            item = self._cache.get(key)

            if item is None:
                return None

            timestamp, dataframe = item

            if (
                time.monotonic()
                - timestamp
                > CACHE_TTL_SECONDS
            ):
                self._cache.pop(
                    key,
                    None,
                )

                return None

            return dataframe.copy()

    async def _set_cached(
        self,
        key: str,
        dataframe: pd.DataFrame,
    ) -> None:

        async with self._cache_lock:

            self._cache[key] = (
                time.monotonic(),
                dataframe.copy(),
            )

    @staticmethod
    def _is_retryable_exception(
        exc: Exception,
    ) -> bool:

        return isinstance(
            exc,
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
                httpx.NetworkError,
                httpx.PoolTimeout,
            ),
        )

    @staticmethod
    def _parse_retry_after(
        response: httpx.Response,
    ) -> Optional[float]:

        value = response.headers.get(
            "Retry-After"
        )

        if not value:
            return None

        try:
            return max(
                0.0,
                float(value),
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

    async def _request(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
    ) -> Dict[str, Any]:

        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": int(outputsize),
            "apikey": self.api_key,
            "timezone": "UTC",
        }

        client = await self._get_client()

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:

                async with self._semaphore:

                    response = await client.get(
                        TWELVE_DATA_URL,
                        params=params,
                    )

                status = response.status_code

                if status == 429:

                    retry_after = (
                        self._parse_retry_after(
                            response
                        )
                    )

                    if retry_after is None:
                        retry_after = float(
                            min(
                                8,
                                2 ** attempt,
                            )
                        )

                    logger.warning(
                        "%s | Twelve Data "
                        "rate limit | attempt %s/%s",
                        symbol,
                        attempt,
                        MAX_RETRIES,
                    )

                    if attempt < MAX_RETRIES:

                        await asyncio.sleep(
                            retry_after
                        )

                        continue

                    response.raise_for_status()

                if 500 <= status <= 599:

                    logger.warning(
                        "%s | Twelve Data HTTP %s "
                        "| attempt %s/%s",
                        symbol,
                        status,
                        attempt,
                        MAX_RETRIES,
                    )

                    if attempt < MAX_RETRIES:

                        await asyncio.sleep(
                            min(
                                8.0,
                                2 ** attempt,
                            )
                        )

                        continue

                    response.raise_for_status()

                response.raise_for_status()

                payload = response.json()

                if not isinstance(
                    payload,
                    dict,
                ):
                    raise RuntimeError(
                        "Twelve Data returned "
                        "invalid JSON"
                    )

                if payload.get(
                    "status"
                ) == "error":

                    message = payload.get(
                        "message",
                        "Unknown Twelve Data error",
                    )

                    code = payload.get(
                        "code"
                    )

                    if (
                        code in {429, "429"}
                        or "rate limit"
                        in str(message).lower()
                    ):

                        if attempt < MAX_RETRIES:

                            await asyncio.sleep(
                                min(
                                    8.0,
                                    2 ** attempt,
                                )
                            )

                            continue

                    raise RuntimeError(
                        "Twelve Data error: "
                        f"{message}"
                    )

                return payload

            except asyncio.CancelledError:
                raise

            except Exception as exc:

                if (
                    self._is_retryable_exception(
                        exc
                    )
                    and attempt < MAX_RETRIES
                ):

                    delay = min(
                        8.0,
                        2 ** attempt,
                    )

                    logger.warning(
                        "%s | temporary network "
                        "error: %s | retry %.1fs",
                        symbol,
                        type(exc).__name__,
                        delay,
                    )

                    await asyncio.sleep(
                        delay
                    )

                    continue

                logger.error(
                    "%s | Twelve Data request "
                    "failed: %s",
                    symbol,
                    exc,
                )

                raise

        raise RuntimeError(
            f"{symbol}: Twelve Data request failed"
        )

    @staticmethod
    def _payload_to_dataframe(
        payload: Dict[str, Any],
        symbol: str,
    ) -> pd.DataFrame:

        values = payload.get(
            "values"
        )

        if not values:

            raise ValueError(
                f"{symbol}: Twelve Data "
                "returned no candle data"
            )

        rows: List[
            Dict[str, Any]
        ] = []

        for item in values:

            if not isinstance(
                item,
                dict,
            ):
                continue

            rows.append(
                {
                    "datetime": item.get(
                        "datetime"
                    ),
                    "open": item.get(
                        "open"
                    ),
                    "high": item.get(
                        "high"
                    ),
                    "low": item.get(
                        "low"
                    ),
                    "close": item.get(
                        "close"
                    ),
                    "volume": item.get(
                        "volume",
                        0,
                    ),
                }
            )

        if not rows:

            raise ValueError(
                f"{symbol}: no valid candle rows"
            )

        dataframe = pd.DataFrame(
            rows
        )

        dataframe["datetime"] = (
            pd.to_datetime(
                dataframe["datetime"],
                utc=True,
                errors="coerce",
            )
        )

        for column in (
            "open",
            "high",
            "low",
            "close",
            "volume",
        ):

            dataframe[column] = (
                pd.to_numeric(
                    dataframe[column],
                    errors="coerce",
                )
            )

        dataframe = dataframe.dropna(
            subset=[
                "datetime",
                "open",
                "high",
                "low",
                "close",
            ]
        )

        dataframe = (
            dataframe
            .drop_duplicates(
                subset=["datetime"],
                keep="last",
            )
            .sort_values(
                "datetime"
            )
            .reset_index(
                drop=True
            )
        )

        if dataframe.empty:

            raise ValueError(
                f"{symbol}: dataframe is empty"
            )

        return dataframe

    async def get_candles(
        self,
        symbol: str,
        interval: str = DEFAULT_INTERVAL,
        outputsize: int = DEFAULT_OUTPUTSIZE,
        force_refresh: bool = False,
    ) -> pd.DataFrame:

        symbol = self.normalize_symbol(
            symbol
        )

        key = self._cache_key(
            symbol,
            interval,
            outputsize,
        )

        if not force_refresh:

            cached = await self._get_cached(
                key
            )

            if cached is not None:
                return cached

        payload = await self._request(
            symbol=symbol,
            interval=interval,
            outputsize=outputsize,
        )

        dataframe = (
            self._payload_to_dataframe(
                payload,
                symbol,
            )
        )

        await self._set_cached(
            key,
            dataframe,
        )

        logger.info(
            "%s | Twelve Data OK | candles=%s",
            symbol,
            len(dataframe),
        )

        return dataframe.copy()

    async def get_candles_many(
        self,
        symbols: Iterable[str],
        interval: str = DEFAULT_INTERVAL,
        outputsize: int = DEFAULT_OUTPUTSIZE,
        force_refresh: bool = False,
    ) -> Dict[
        str,
        pd.DataFrame,
    ]:

        unique_symbols = list(
            dict.fromkeys(
                self.normalize_symbol(
                    symbol
                )
                for symbol in symbols
            )
        )

        async def load(
            symbol: str,
        ):

            try:

                dataframe = (
                    await self.get_candles(
                        symbol=symbol,
                        interval=interval,
                        outputsize=outputsize,
                        force_refresh=(
                            force_refresh
                        ),
                    )
                )

                return (
                    symbol,
                    dataframe,
                )

            except asyncio.CancelledError:
                raise

            except Exception as exc:

                logger.error(
                    "%s | failed to load candles: %s",
                    symbol,
                    exc,
                )

                return (
                    symbol,
                    None,
                )

        results = await asyncio.gather(
            *(
                load(symbol)
                for symbol in unique_symbols
            )
        )

        output: Dict[
            str,
            pd.DataFrame,
        ] = {}

        for symbol, dataframe in results:

            if dataframe is not None:
                output[symbol] = dataframe

        return output

    async def get_price(
        self,
        symbol: str,
    ) -> Optional[float]:

        symbol = self.normalize_symbol(
            symbol
        )

        try:

            dataframe = (
                await self.get_candles(
                    symbol=symbol,
                    interval=DEFAULT_INTERVAL,
                    outputsize=1,
                    force_refresh=True,
                )
            )

            if dataframe.empty:
                return None

            return float(
                dataframe.iloc[-1]["close"]
            )

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            logger.error(
                "%s | failed to get price: %s",
                symbol,
                exc,
            )

            return None

    async def get_prices_many(
        self,
        symbols: Iterable[str],
    ) -> Dict[
        str,
        float,
    ]:

        unique_symbols = list(
            dict.fromkeys(
                self.normalize_symbol(
                    symbol
                )
                for symbol in symbols
            )
        )

        async def load(
            symbol: str,
        ):

            return (
                symbol,
                await self.get_price(
                    symbol
                ),
            )

        results = await asyncio.gather(
            *(
                load(symbol)
                for symbol in unique_symbols
            )
        )

        output: Dict[
            str,
            float,
        ] = {}

        for symbol, price in results:

            if price is not None:
                output[symbol] = price

        return output

    async def clear_cache(
        self,
    ) -> None:

        async with self._cache_lock:
            self._cache.clear()

    async def close(
        self,
    ) -> None:

        client = self._client
        self._client = None

        if client is not None:

            try:
                await client.aclose()
            except Exception:
                logger.exception(
                    "Failed to close MarketClient"
                )


market = MarketClient()
