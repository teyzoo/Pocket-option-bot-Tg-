from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pandas as pd

from config import (
    MAX_CANDLES,
    TWELVE_DATA_API_KEY,
    TWELVE_DATA_BASE_URL,
    TWELVE_DATA_TIMEOUT,
)


class MarketError(Exception):
    pass


class MarketClient:
    def __init__(self) -> None:
        self.base_url = TWELVE_DATA_BASE_URL.rstrip("/")
        self.api_key = TWELVE_DATA_API_KEY
        self.timeout = TWELVE_DATA_TIMEOUT

    async def _request(
        self,
        params: dict[str, str],
    ) -> dict:
        params = {
            **params,
            "apikey": self.api_key,
        }

        async with httpx.AsyncClient(
            timeout=self.timeout
        ) as client:
            response = await client.get(
                f"{self.base_url}/time_series",
                params=params,
            )

        if response.status_code != 200:
            raise MarketError(
                f"Twelve Data HTTP {response.status_code}"
            )

        data = response.json()

        if "status" in data and data["status"] == "error":
            raise MarketError(
                data.get("message", "Ошибка Twelve Data")
            )

        return data

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1min",
        outputsize: int = MAX_CANDLES,
    ) -> pd.DataFrame:
        data = await self._request(
            {
                "symbol": symbol,
                "interval": interval,
                "outputsize": str(outputsize),
                "format": "JSON",
            }
        )

        values = data.get("values")

        if not values:
            raise MarketError(
                f"Нет свечей для {symbol} / {interval}"
            )

        rows = []

        for item in reversed(values):
            rows.append(
                {
                    "datetime": item["datetime"],
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(
                        item.get("volume", 0) or 0
                    ),
                }
            )

        df = pd.DataFrame(rows)

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            utc=True,
        )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close",
            ]
        )

        df = df.reset_index(drop=True)

        return df

    async def get_price(
        self,
        symbol: str,
    ) -> float:
        data = await self._request(
            {
                "symbol": symbol,
                "interval": "1min",
                "outputsize": "1",
                "format": "JSON",
            }
        )

        values = data.get("values")

        if not values:
            raise MarketError(
                f"Нет текущей цены для {symbol}"
            )

        return float(values[0]["close"])

    async def get_multiple_timeframes(
        self,
        symbol: str,
    ) -> dict[str, pd.DataFrame]:
        intervals = {
            "1min": "1min",
            "5min": "5min",
            "15min": "15min",
        }

        tasks = [
            self.get_candles(
                symbol,
                interval,
                MAX_CANDLES,
            )
            for interval in intervals.values()
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        output: dict[str, pd.DataFrame] = {}

        for (name, _), result in zip(
            intervals.items(),
            results,
        ):
            if isinstance(result, Exception):
                continue

            output[name] = result

        return output
