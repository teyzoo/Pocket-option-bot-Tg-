from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pandas as pd

from config import (
    MAX_CANDLES,
    TWELVE_DATA_API_KEY,
    TWELVE_DATA_BASE_URL,
    TWELVE_DATA_TIMEOUT,
)


class MarketAPIError(Exception):
    pass


class MarketClient:
    def __init__(self) -> None:
        self.base_url = (
            TWELVE_DATA_BASE_URL.rstrip("/")
        )

        self.timeout = httpx.Timeout(
            TWELVE_DATA_TIMEOUT
        )

        self._lock = asyncio.Lock()

    async def _request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        request_params = dict(params)

        request_params["apikey"] = (
            TWELVE_DATA_API_KEY
        )

        async with self._lock:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.get(
                    f"{self.base_url}/time_series",
                    params=request_params,
                )

        response.raise_for_status()

        data = response.json()

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

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1min",
        outputsize: int = MAX_CANDLES,
    ) -> pd.DataFrame:
        outputsize = max(
            1,
            min(
                MAX_CANDLES,
                outputsize,
            ),
        )

        data = await self._request(
            {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "timezone": "UTC",
                "format": "JSON",
            }
        )

        values = data["values"]

        rows = []

        for item in values:
            rows.append(
                {
                    "datetime": pd.to_datetime(
                        item["datetime"],
                        utc=True,
                    ),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(
                        item.get(
                            "volume",
                            0,
                        )
                    ),
                }
            )

        df = pd.DataFrame(rows)

        if df.empty:
            raise MarketAPIError(
                f"No candles for {symbol}"
            )

        df = df.sort_values(
            "datetime"
        ).reset_index(drop=True)

        return df

    async def get_price(
        self,
        symbol: str,
    ) -> float:
        df = await self.get_candles(
            symbol=symbol,
            interval="1min",
            outputsize=1,
        )

        return float(
            df.iloc[-1]["close"]
        )


market_client = MarketClient()
