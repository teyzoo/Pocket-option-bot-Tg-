from __future__ import annotations

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


logger = logging.getLogger(
    __name__
)


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

    # ============================================================
    # NORMALIZATION
    # ============================================================

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

        value = (
            expiry_minutes
            .strip()
            .lower()
        )

        return value in {
            "any",
            "любое",
            "любое время",
            "all",
        }

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

    # ============================================================
    # LOAD CANDLES
    # ============================================================

    async def _load_pair(
        self,
        pair: str,
        market: str,
    ):
        if not pair_selector.is_allowed(
            pair,
            market,
        ):
            logger.debug(
                "Pair %s is not allowed for market %s",
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
        except Exception:
            logger.exception(
                "Failed to load candles: pair=%s market=%s",
                pair,
                market,
            )
            return None

        if df is None or df.empty:
            logger.debug(
                "No candles: pair=%s market=%s",
                pair,
                market,
            )
            return None

        try:
            filtered = await candle_filter_service.apply(
                df
            )
        except Exception:
            logger.exception(
                "Candle filter failed: pair=%s",
                pair,
            )
            return None

        if filtered is None:
            return None

        if len(filtered) < MIN_CANDLES_REQUIRED:
            logger.debug(
                "Not enough candles: pair=%s count=%s required=%s",
                pair,
                len(filtered),
                MIN_CANDLES_REQUIRED,
            )
            return None

        return filtered

    # ============================================================
    # SINGLE PAIR
    # ============================================================

    async def scan_pair(
        self,
        pair: str,
        market: str,
        expiry_minutes,
        source: str = "manual",
    ) -> SignalCandidate | None:

        # --------------------------------------------------------
        # ALL PAIRS
        # --------------------------------------------------------

        if self._is_all_pairs(
            pair
        ):
            return await self.scan(
                market=market,
                expiry_minutes=expiry_minutes,
                pairs=pair_selector.available_pairs(
                    market
                ),
                source=source,
                max_pairs=None,
            )

        # --------------------------------------------------------
        # ONE EXPIRY
        # --------------------------------------------------------

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is not None:
            try:
                df = await self._load_pair(
                    pair,
                    market,
                )

                if df is None:
                    return None

                candidate = self.engine.analyze(
                    pair=pair,
                    market=market,
                    df=df,
                    expiry_minutes=expiry,
                    source=source,
                )

                if candidate is not None:
                    logger.info(
                        "Signal found: pair=%s direction=%s expiry=%s quality=%s winrate=%s",
                        getattr(
                            candidate,
                            "pair",
                            pair,
                        ),
                        getattr(
                            candidate,
                            "direction",
                            "?",
                        ),
                        getattr(
                            candidate,
                            "expiry_minutes",
                            expiry,
                        ),
                        getattr(
                            candidate,
                            "quality",
                            0,
                        ),
                        getattr(
                            candidate,
                            "winrate",
                            0,
                        ),
                    )

                return candidate

            except Exception:
                logger.exception(
                    "Single pair scan failed: pair=%s expiry=%s",
                    pair,
                    expiry,
                )
                return None

        # --------------------------------------------------------
        # ANY EXPIRY
        # --------------------------------------------------------

        if self._is_any_expiry(
            expiry_minutes
        ):
            try:
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
                    try:
                        candidate = (
                            self.engine.analyze(
                                pair=pair,
                                market=market,
                                df=df,
                                expiry_minutes=expiry,
                                source=source,
                            )
                        )

                        if candidate is not None:
                            candidates.append(
                                candidate
                            )

                    except Exception:
                        logger.exception(
                            "Expiry analysis failed: pair=%s expiry=%s",
                            pair,
                            expiry,
                        )

                return self._select_best(
                    candidates
                )

            except Exception:
                logger.exception(
                    "Any-expiry scan failed: pair=%s",
                    pair,
                )
                return None

        return None

    # ============================================================
    # MULTI-PAIR SCAN
    # ============================================================

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

        pair_list = list(
            pairs
        )

        # --------------------------------------------------------
        # max_pairs применяется только если он реально передан.
        #
        # ALL теперь не режется автоматически до 8 пар.
        # --------------------------------------------------------

        if max_pairs is not None:
            try:
                max_pairs = int(
                    max_pairs
                )
            except (
                TypeError,
                ValueError,
            ):
                max_pairs = len(
                    pair_list
                )

            if max_pairs > 0:
                pair_list = pair_list[
                    :max_pairs
                ]

        if not pair_list:
            logger.warning(
                "No pairs available for market=%s",
                market,
            )
            return None

        logger.info(
            "Starting scan: market=%s pairs=%s expiry=%s source=%s",
            market,
            len(pair_list),
            expiry_minutes,
            source,
        )

        # --------------------------------------------------------
        # ONE EXPIRY
        # --------------------------------------------------------

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is not None:
            candidates: list[
                SignalCandidate
            ] = []

            for pair in pair_list:
                try:
                    df = await self._load_pair(
                        pair,
                        market,
                    )

                    if df is None:
                        continue

                    candidate = (
                        self.engine.analyze(
                            pair=pair,
                            market=market,
                            df=df,
                            expiry_minutes=expiry,
                            source=source,
                        )
                    )

                    if candidate is not None:
                        candidates.append(
                            candidate
                        )

                        logger.info(
                            "Candidate: pair=%s direction=%s quality=%.2f confidence=%.2f winrate=%.2f",
                            pair,
                            candidate.direction,
                            candidate.quality,
                            candidate.confidence,
                            candidate.winrate,
                        )

                except Exception:
                    logger.exception(
                        "Pair scan failed: pair=%s",
                        pair,
                    )

            best = self._select_best(
                candidates
            )

            if best is None:
                logger.info(
                    "No candidate found: market=%s expiry=%s",
                    market,
                    expiry,
                )

            return best

        # --------------------------------------------------------
        # ANY EXPIRY
        # --------------------------------------------------------

        if self._is_any_expiry(
            expiry_minutes
        ):
            return await self._scan_any_expiry(
                market=market,
                pairs=pair_list,
                source=source,
            )

        return None

    # ============================================================
    # ANY EXPIRY / ALL PAIRS
    # ============================================================

    async def _scan_any_expiry(
        self,
        market: str,
        pairs: list[str],
        source: str,
    ) -> SignalCandidate | None:

        candidates: list[
            SignalCandidate
        ] = []

        for pair in pairs:
            try:
                df = await self._load_pair(
                    pair,
                    market,
                )

                if df is None:
                    continue

                # Одна загрузка свечей на пару.
                # Экспирации 1..20 считаются локально.
                for expiry in range(
                    MIN_EXPIRY_MINUTES,
                    MAX_EXPIRY_MINUTES + 1,
                ):
                    try:
                        candidate = (
                            self.engine.analyze(
                                pair=pair,
                                market=market,
                                df=df,
                                expiry_minutes=expiry,
                                source=source,
                            )
                        )

                        if candidate is not None:
                            candidates.append(
                                candidate
                            )

                    except Exception:
                        logger.exception(
                            "Expiry failed: pair=%s expiry=%s",
                            pair,
                            expiry,
                        )

            except Exception:
                logger.exception(
                    "Any-expiry pair failed: pair=%s",
                    pair,
                )

        best = self._select_best(
            candidates
        )

        if best is not None:
            logger.info(
                "Best ANY signal: pair=%s direction=%s expiry=%s quality=%.2f winrate=%.2f",
                best.pair,
                best.direction,
                best.expiry_minutes,
                best.quality,
                best.winrate,
            )
        else:
            logger.info(
                "ANY scan produced no candidate: market=%s pairs=%s",
                market,
                len(pairs),
            )

        return best

    # ============================================================
    # SELECT BEST
    # ============================================================

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
