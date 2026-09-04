from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from candle_filter import candle_filter_service

from config import (
    MAX_CANDLES,
    MAX_EXPIRY_MINUTES,
    MIN_CANDLES_REQUIRED,
    MIN_EXPIRY_MINUTES,
)

from market import (
    MarketClient,
    market_client,
)

from models import SignalCandidate

from pair_selector import pair_selector

from signal_engine import SignalEngine


logger = logging.getLogger(__name__)


ALL_PAIRS_VALUES = {
    "ALL",
    "ALL_PAIRS",
    "ANY_PAIR",
    "ВСЕ",
    "ВСЕ ПАРЫ",
    "__ALL__",
}


class SignalScanner:

    def __init__(
        self,
        market: MarketClient | None = None,
        engine: SignalEngine | None = None,
    ) -> None:
        self.market = (
            market
            if market is not None
            else market_client
        )

        self.engine = (
            engine
            if engine is not None
            else SignalEngine()
        )

    @staticmethod
    def _normalize_expiry(
        expiry_minutes,
    ) -> int | None:
        try:
            value = int(
                expiry_minutes
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if not (
            MIN_EXPIRY_MINUTES
            <= value
            <= MAX_EXPIRY_MINUTES
        ):
            return None

        return value

    @staticmethod
    def _is_any_expiry(
        expiry_minutes,
    ) -> bool:
        if not isinstance(
            expiry_minutes,
            str,
        ):
            return False

        return (
            expiry_minutes
            .strip()
            .lower()
            in {
                "any",
                "любое",
                "любое время",
                "all",
            }
        )

    @staticmethod
    def _is_all_pairs(
        pair: str | None,
    ) -> bool:
        if pair is None:
            return False

        return (
            str(pair)
            .strip()
            .upper()
            in ALL_PAIRS_VALUES
        )

    async def _load_pair(
        self,
        pair: str,
        market: str,
    ):
        if not pair_selector.is_allowed(
            pair,
            market,
        ):
            logger.info(
                "Pair rejected before market load: "
                "pair=%s market=%s reason=not_allowed",
                pair,
                market,
            )
            return None

        try:
            df = await self.market.get_candles(
                symbol=pair,
                interval="1min",
                outputsize=MAX_CANDLES,
            )
        except Exception as exc:
            logger.exception(
                "Failed to load candles: "
                "pair=%s market=%s error=%s",
                pair,
                market,
                type(exc).__name__,
            )
            return None

        if df is None or df.empty:
            logger.info(
                "Pair rejected: pair=%s reason=empty_candles",
                pair,
            )
            return None

        try:
            filtered = await candle_filter_service.apply(
                df
            )
        except Exception as exc:
            logger.exception(
                "Candle filter failed: pair=%s error=%s",
                pair,
                type(exc).__name__,
            )
            return None

        if filtered is None:
            logger.info(
                "Pair rejected: pair=%s reason=candle_filter_none",
                pair,
            )
            return None

        if len(filtered) < MIN_CANDLES_REQUIRED:
            logger.info(
                "Pair rejected: pair=%s reason=not_enough_candles "
                "count=%s required=%s",
                pair,
                len(filtered),
                MIN_CANDLES_REQUIRED,
            )
            return None

        return filtered

    async def scan_pair(
        self,
        pair: str,
        market: str,
        expiry_minutes,
        source: str = "manual",
    ) -> SignalCandidate | None:

        if self._is_all_pairs(pair):
            return await self.scan(
                market=market,
                expiry_minutes=expiry_minutes,
                pairs=pair_selector.available_pairs(
                    market
                ),
                source=source,
                max_pairs=None,
            )

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is not None:
            df = await self._load_pair(
                pair,
                market,
            )

            if df is None:
                return None

            return self.engine.analyze(
                pair=pair,
                market=market,
                df=df,
                expiry_minutes=expiry,
                source=source,
            )

        if self._is_any_expiry(
            expiry_minutes
        ):
            df = await self._load_pair(
                pair,
                market,
            )

            if df is None:
                return None

            candidates: list[
                SignalCandidate
            ] = []

            for expiry in range(
                MIN_EXPIRY_MINUTES,
                MAX_EXPIRY_MINUTES + 1,
            ):
                candidate = self.engine.analyze(
                    pair=pair,
                    market=market,
                    df=df,
                    expiry_minutes=expiry,
                    source=source,
                )

                if candidate is not None:
                    candidates.append(
                        candidate
                    )

            return self._select_best(
                candidates
            )

        return None

    async def _analyze_pair_any(
        self,
        pair: str,
        market: str,
        source: str,
    ) -> list[SignalCandidate]:
        df = await self._load_pair(
            pair,
            market,
        )

        if df is None:
            return []

        candidates: list[
            SignalCandidate
        ] = []

        for expiry in range(
            MIN_EXPIRY_MINUTES,
            MAX_EXPIRY_MINUTES + 1,
        ):
            try:
                candidate = self.engine.analyze(
                    pair=pair,
                    market=market,
                    df=df,
                    expiry_minutes=expiry,
                    source=source,
                )

                if candidate is not None:
                    candidates.append(
                        candidate
                    )

            except Exception as exc:
                logger.exception(
                    "Expiry analysis failed: "
                    "pair=%s expiry=%s error=%s",
                    pair,
                    expiry,
                    type(exc).__name__,
                )

        return candidates

    async def _analyze_pair_fixed(
        self,
        pair: str,
        market: str,
        expiry: int,
        source: str,
    ) -> SignalCandidate | None:
        df = await self._load_pair(
            pair,
            market,
        )

        if df is None:
            return None

        try:
            return self.engine.analyze(
                pair=pair,
                market=market,
                df=df,
                expiry_minutes=expiry,
                source=source,
            )
        except Exception as exc:
            logger.exception(
                "Pair analysis failed: "
                "pair=%s expiry=%s error=%s",
                pair,
                expiry,
                type(exc).__name__,
            )
            return None

    async def scan(
        self,
        market: str,
        expiry_minutes,
        pairs: Iterable[str] | None = None,
        source: str = "manual",
        max_pairs: int | None = None,
    ) -> SignalCandidate | None:

        if pairs is None:
            pairs = pair_selector.available_pairs(
                market
            )

        pair_list = list(pairs)

        if max_pairs is not None:
            try:
                max_pairs = int(max_pairs)
            except (
                TypeError,
                ValueError,
            ):
                max_pairs = len(pair_list)

            if max_pairs > 0:
                pair_list = pair_list[
                    :max_pairs
                ]

        if not pair_list:
            logger.warning(
                "No pairs available: market=%s",
                market,
            )
            return None

        logger.info(
            "Starting scan: market=%s pairs=%d "
            "expiry=%s source=%s",
            market,
            len(pair_list),
            expiry_minutes,
            source,
        )

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is not None:
            tasks = [
                self._analyze_pair_fixed(
                    pair,
                    market,
                    expiry,
                    source,
                )
                for pair in pair_list
            ]

            results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            candidates: list[
                SignalCandidate
            ] = []

            for pair, result in zip(
                pair_list,
                results,
            ):
                if isinstance(
                    result,
                    Exception,
                ):
                    logger.exception(
                        "Concurrent pair scan failed: "
                        "pair=%s error=%s",
                        pair,
                        type(result).__name__,
                    )
                    continue

                if result is not None:
                    candidates.append(result)

            return self._select_best(
                candidates
            )

        if self._is_any_expiry(
            expiry_minutes
        ):
            tasks = [
                self._analyze_pair_any(
                    pair,
                    market,
                    source,
                )
                for pair in pair_list
            ]

            results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            candidates: list[
                SignalCandidate
            ] = []

            for pair, result in zip(
                pair_list,
                results,
            ):
                if isinstance(
                    result,
                    Exception,
                ):
                    logger.error(
                        "Concurrent ANY scan failed: "
                        "pair=%s error=%s",
                        pair,
                        type(result).__name__,
                    )
                    continue

                candidates.extend(
                    result
                )

            best = self._select_best(
                candidates
            )

            if best is not None:
                logger.info(
                    "Best ANY signal: pair=%s "
                    "direction=%s expiry=%s "
                    "quality=%.2f winrate=%.2f",
                    best.pair,
                    best.direction,
                    best.expiry_minutes,
                    best.quality,
                    best.winrate,
                )
            else:
                logger.info(
                    "ANY scan produced no candidate: "
                    "market=%s pairs=%d",
                    market,
                    len(pair_list),
                )

            return best

        logger.warning(
            "Unsupported expiry value: %r",
            expiry_minutes,
        )

        return None

    @staticmethod
    def _select_best(
        candidates: list[
            SignalCandidate
        ],
    ) -> SignalCandidate | None:

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
                float(
                    getattr(
                        item,
                        "quality",
                        0,
                    )
                    or 0
                ),
                float(
                    getattr(
                        item,
                        "winrate",
                        0,
                    )
                    or 0
                ),
                float(
                    getattr(
                        item,
                        "confidence",
                        0,
                    )
                    or 0
                ),
                int(
                    getattr(
                        item,
                        "confirmations",
                        0,
                    )
                    or 0
                ),
            ),
        )
