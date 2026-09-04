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
    """
    Быстрый сканер рынка.

    Основные возможности:

    - одна конкретная пара;
    - все пары;
    - конкретная экспирация 1-20 минут;
    - любое время 1-20 минут;
    - параллельная загрузка свечей;
    - параллельный анализ экспираций;
    - выбор лучшего сигнала;
    - сохранение совместимости со старым API.
    """

    # Максимальное количество CPU-анализов одновременно.

    # Слишком большое значение может перегрузить бесплатный
    # Render-инстанс, поэтому держим разумный предел.
    ANALYSIS_CONCURRENCY = 8

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

        self._analysis_semaphore = (
            asyncio.Semaphore(
                self.ANALYSIS_CONCURRENCY
            )
        )

    # ========================================================
    # NORMALIZATION
    # ========================================================

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
            expiry_minutes.strip().lower()
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
            str(pair).strip().upper()
            in ALL_PAIRS_VALUES
        )

    # ========================================================
    # LOAD ONE PAIR
    # ========================================================

    async def _load_pair(
        self,
        pair: str,
        market: str,
    ):
        """
        Загружает свечи одной пары.

        Метод сохранён для совместимости.
        """

        if not pair_selector.is_allowed(
            pair,
            market,
        ):
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
                "pair=%s error=%s",
                pair,
                type(exc).__name__,
            )
            return None

        if df is None or df.empty:
            return None

        try:
            filtered = await candle_filter_service.apply(
                df
            )

        except Exception as exc:
            logger.exception(
                "Candle filter failed: "
                "pair=%s error=%s",
                pair,
                type(exc).__name__,
            )
            return None

        if filtered is None:
            return None

        if len(filtered) < MIN_CANDLES_REQUIRED:
            return None

        return filtered

    # ========================================================
    # LOAD MANY PAIRS
    # ========================================================

    async def _load_pairs(
        self,
        pair_list: list[str],
        market: str,
    ) -> dict[str, object]:
        """
        Загружает свечи всех пар максимально быстро.

        Если MarketClient поддерживает get_candles_many(),
        используется единый параллельный загрузчик.

        Есть fallback на обычные запросы для совместимости
        с кастомными MarketClient.
        """

        allowed_pairs = [
            pair
            for pair in pair_list
            if pair_selector.is_allowed(
                pair,
                market,
            )
        ]

        if not allowed_pairs:
            return {}

        # ----------------------------------------------------
        # FAST PATH
        # ----------------------------------------------------

        get_many = getattr(
            self.market,
            "get_candles_many",
            None,
        )

        if callable(get_many):
            try:
                raw_data = await get_many(
                    symbols=allowed_pairs,
                    interval="1min",
                    outputsize=MAX_CANDLES,
                )

                if raw_data is None:
                    raw_data = {}

            except Exception as exc:
                logger.exception(
                    "Parallel candle loading failed: "
                    "error=%s",
                    type(exc).__name__,
                )
                raw_data = {}

        else:
            raw_data = {}

            async def load_fallback(
                pair: str,
            ) -> tuple[str, object | None]:

                try:
                    df = await self.market.get_candles(
                        symbol=pair,
                        interval="1min",
                        outputsize=MAX_CANDLES,
                    )

                    return pair, df

                except Exception as exc:
                    logger.exception(
                        "Failed to load candles: "
                        "pair=%s error=%s",
                        pair,
                        type(exc).__name__,
                    )

                    return pair, None

            results = await asyncio.gather(
                *(
                    load_fallback(pair)
                    for pair in allowed_pairs
                ),
                return_exceptions=False,
            )

            raw_data = {
                pair: df
                for pair, df in results
                if df is not None
            }

        # ----------------------------------------------------
        # FILTER IN PARALLEL
        # ----------------------------------------------------

        async def filter_pair(
            pair: str,
            df,
        ) -> tuple[str, object | None]:

            if df is None:
                return pair, None

            try:
                if df.empty:
                    return pair, None

            except Exception:
                return pair, None

            try:
                filtered = await candle_filter_service.apply(
                    df
                )

            except Exception as exc:
                logger.exception(
                    "Candle filter failed: "
                    "pair=%s error=%s",
                    pair,
                    type(exc).__name__,
                )
                return pair, None

            if filtered is None:
                return pair, None

            try:
                if len(filtered) < MIN_CANDLES_REQUIRED:
                    return pair, None

            except Exception:
                return pair, None

            return pair, filtered

        filter_results = await asyncio.gather(
            *(
                filter_pair(
                    pair,
                    raw_data.get(pair),
                )
                for pair in allowed_pairs
            ),
            return_exceptions=False,
        )

        return {
            pair: df
            for pair, df in filter_results
            if df is not None
        }

    # ========================================================
    # ENGINE ANALYSIS
    # ========================================================

    async def _run_engine(
        self,
        pair: str,
        market: str,
        df,
        expiry: int,
        source: str,
    ) -> SignalCandidate | None:
        """
        Запускает синхронный SignalEngine в отдельном потоке.

        Это важно, потому что analyze() выполняет pandas/
        backtest и может блокировать event loop.
        """

        async with self._analysis_semaphore:

            try:
                return await asyncio.to_thread(
                    self.engine.analyze,
                    pair=pair,
                    market=market,
                    df=df,
                    expiry_minutes=expiry,
                    source=source,
                )

            except Exception as exc:
                logger.exception(
                    "Engine analysis failed: "
                    "pair=%s expiry=%s error=%s",
                    pair,
                    expiry,
                    type(exc).__name__,
                )

                return None

    # ========================================================
    # ANY EXPIRY
    # ========================================================

    async def _analyze_pair_any(
        self,
        pair: str,
        market: str,
        source: str,
        df=None,
    ) -> list[SignalCandidate]:
        """
        Проверяет ВСЕ экспирации 1-20 минут параллельно.

        Раньше:

            1 -> ждём
            2 -> ждём
            3 -> ждём
            ...
            20 -> ждём

        Теперь:

            1 ─┐
            2 ─┤
            3 ─┤
            ...
            20 ─┘
               ↓
            лучший результат
        """

        if df is None:
            df = await self._load_pair(
                pair,
                market,
            )

        if df is None:
            return []

        expiries = list(
            range(
                MIN_EXPIRY_MINUTES,
                MAX_EXPIRY_MINUTES + 1,
            )
        )

        tasks = [
            self._run_engine(
                pair=pair,
                market=market,
                df=df,
                expiry=expiry,
                source=source,
            )
            for expiry in expiries
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=False,
        )

        return [
            candidate
            for candidate in results
            if candidate is not None
        ]

    # ========================================================
    # FIXED EXPIRY
    # ========================================================

    async def _analyze_pair_fixed(
        self,
        pair: str,
        market: str,
        expiry: int,
        source: str,
        df=None,
    ) -> SignalCandidate | None:

        if df is None:
            df = await self._load_pair(
                pair,
                market,
            )

        if df is None:
            return None

        return await self._run_engine(
            pair=pair,
            market=market,
            df=df,
            expiry=expiry,
            source=source,
        )

    # ========================================================
    # SINGLE PAIR
    # ========================================================

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
                source=source,
            )

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is not None:
            return await self._analyze_pair_fixed(
                pair=pair,
                market=market,
                expiry=expiry,
                source=source,
            )

        if self._is_any_expiry(
            expiry_minutes
        ):
            candidates = (
                await self._analyze_pair_any(
                    pair=pair,
                    market=market,
                    source=source,
                )
            )

            return self._select_best(
                candidates
            )

        return None

    # ========================================================
    # FULL SCAN
    # ========================================================

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
            dict.fromkeys(
                str(pair)
                for pair in pairs
                if pair
            )
        )

        # ----------------------------------------------------
        # LIMIT
        # ----------------------------------------------------

        if max_pairs is not None:
            try:
                limit = int(
                    max_pairs
                )

            except (
                TypeError,
                ValueError,
            ):
                limit = len(pair_list)

            if limit > 0:
                pair_list = pair_list[:limit]

        if not pair_list:
            logger.warning(
                "No pairs available: market=%s",
                market,
            )
            return None

        logger.info(
            "Starting scan: market=%s "
            "pairs=%d expiry=%s source=%s",
            market,
            len(pair_list),
            expiry_minutes,
            source,
        )

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        # ====================================================
        # LOAD ALL PAIRS ONCE
        # ====================================================

        loaded = await self._load_pairs(
            pair_list=pair_list,
            market=market,
        )

        if not loaded:
            logger.info(
                "No valid market data: "
                "market=%s pairs=%d",
                market,
                len(pair_list),
            )
            return None

        # ====================================================
        # FIXED EXPIRY
        # ====================================================

        if expiry is not None:

            tasks = [
                self._analyze_pair_fixed(
                    pair=pair,
                    market=market,
                    expiry=expiry,
                    source=source,
                    df=loaded.get(pair),
                )
                for pair in loaded
            ]

            results = await asyncio.gather(
                *tasks,
                return_exceptions=False,
            )

            candidates = [
                candidate
                for candidate in results
                if candidate is not None
            ]

            best = self._select_best(
                candidates
            )

            if best is None:
                logger.info(
                    "Fixed scan produced no candidate: "
                    "market=%s pairs=%d expiry=%d",
                    market,
                    len(pair_list),
                    expiry,
                )

            else:
                logger.info(
                    "Best fixed signal: "
                    "pair=%s direction=%s "
                    "expiry=%s quality=%.2f "
                    "confidence=%.2f winrate=%.2f",
                    best.pair,
                    best.direction,
                    best.expiry_minutes,
                    best.quality,
                    best.confidence,
                    best.winrate,
                )

            return best

        # ====================================================
        # ANY EXPIRY
        # ====================================================

        if self._is_any_expiry(
            expiry_minutes
        ):

            tasks = [
                self._analyze_pair_any(
                    pair=pair,
                    market=market,
                    source=source,
                    df=loaded.get(pair),
                )
                for pair in loaded
            ]

            results = await asyncio.gather(
                *tasks,
                return_exceptions=False,
            )

            candidates: list[
                SignalCandidate
            ] = []

            for result in results:
                if result:
                    candidates.extend(
                        result
                    )

            best = self._select_best(
                candidates
            )

            if best is None:
                logger.info(
                    "ANY scan produced no candidate: "
                    "market=%s pairs=%d",
                    market,
                    len(pair_list),
                )

            else:
                logger.info(
                    "Best ANY signal: "
                    "pair=%s direction=%s "
                    "expiry=%s quality=%.2f "
                    "confidence=%.2f winrate=%.2f",
                    best.pair,
                    best.direction,
                    best.expiry_minutes,
                    best.quality,
                    best.confidence,
                    best.winrate,
                )

            return best

        return None

    # ========================================================
    # SELECT BEST
    # ========================================================

    @staticmethod
    def _select_best(
        candidates: list[SignalCandidate],
    ) -> SignalCandidate | None:

        if not candidates:
            return None

        # Сначала качество.
        # Затем исторический WINRATE.
        # Затем confidence.
        # Затем количество подтверждений.

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
