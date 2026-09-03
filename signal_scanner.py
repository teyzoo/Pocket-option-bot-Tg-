from __future__ import annotations

import asyncio
import random

from config import (
    POCKET_OPTION_REGULAR_PAIRS,
    SIGNAL_TYPE_ANY,
    SIGNAL_TYPE_REGULAR,
)
from market import MarketClient, MarketError
from models import SignalCandidate
from signal_engine import SignalEngine


class SignalScanner:
    def __init__(
        self,
        market: MarketClient,
        engine: SignalEngine,
    ) -> None:
        self.market = market
        self.engine = engine

    def get_available_pairs(
        self,
        market_type: str = SIGNAL_TYPE_REGULAR,
    ) -> list[str]:
        if market_type in {
            SIGNAL_TYPE_REGULAR,
            SIGNAL_TYPE_ANY,
        }:
            return list(
                POCKET_OPTION_REGULAR_PAIRS
            )

        return []

    async def scan_pair(
        self,
        pair: str,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:
        try:
            data = await self.market.get_candles(
                pair,
                interval="1min",
            )
        except MarketError:
            return None
        except Exception:
            return None

        return self.engine.analyze(
            pair=pair,
            df=data,
            expiry_minutes=expiry_minutes,
            source=source,
        )

    async def scan(
        self,
        expiry_minutes: int,
        market_type: str = SIGNAL_TYPE_REGULAR,
        source: str = "manual",
    ) -> SignalCandidate | None:
        pairs = self.get_available_pairs(
            market_type
        )

        if not pairs:
            return None

        shuffled = pairs.copy()
        random.shuffle(shuffled)

        # За один цикл не перебираем весь рынок,
        # чтобы не сжигать API-лимит.
        selected = shuffled[:2]

        tasks = [
            self.scan_pair(
                pair=pair,
                expiry_minutes=expiry_minutes,
                source=source,
            )
            for pair in selected
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        candidates = [
            item
            for item in results
            if isinstance(
                item,
                SignalCandidate,
            )
        ]

        if not candidates:
            return None

        candidates.sort(
            key=lambda signal: (
                signal.confidence,
                signal.quality,
            ),
            reverse=True,
        )

        return candidates[0]
