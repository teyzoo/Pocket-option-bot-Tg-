from __future__ import annotations

from typing import Iterable

from candle_filter import candle_filter
from config import (
    MAX_CANDLES,
    MIN_CANDLES_REQUIRED,
)
from market import MarketClient
from models import SignalCandidate
from pair_selector import pair_selector
from signal_engine import SignalEngine


class SignalScanner:
    def __init__(
        self,
        market: MarketClient,
        engine: SignalEngine,
    ) -> None:
        self.market = market
        self.engine = engine

    async def scan_pair(
        self,
        pair: str,
        market: str,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:
        if not pair_selector.is_allowed(
            pair,
            market,
        ):
            return None

        df = await self.market.get_candles(
            pair,
            interval="1min",
            outputsize=MAX_CANDLES,
        )

        filtered = candle_filter.apply(df)

        if len(filtered) < MIN_CANDLES_REQUIRED:
            return None

        return self.engine.analyze(
            pair=pair,
            market=market,
            df=filtered,
            expiry_minutes=expiry_minutes,
            source=source,
        )

    async def scan(
        self,
        market: str,
        expiry_minutes: int,
        pairs: Iterable[str] | None = None,
        source: str = "manual",
    ) -> SignalCandidate | None:
        if pairs is None:
            pairs = pair_selector.available_pairs(
                market
            )

        candidates: list[SignalCandidate] = []

        for pair in pairs:
            try:
                candidate = await self.scan_pair(
                    pair=pair,
                    market=market,
                    expiry_minutes=expiry_minutes,
                    source=source,
                )

                if candidate:
                    candidates.append(
                        candidate
                    )

            except Exception:
                continue

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
                item.winrate,
                item.confidence,
                item.quality,
            ),
        )
