from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, List, Optional

import pandas as pd

from chart import create_signal_chart
from market import market_client
from models import SignalCandidate
from pair_selector import pair_selector
from signal_engine import SignalEngine


logger = logging.getLogger("signal_scanner")


# Не перегружаем Twelve Data и CPU Render Free.
ANALYSIS_CONCURRENCY = 3

# Количество свечей для анализа.
CANDLE_OUTPUTSIZE = 500

# Максимальное количество пар за один автоматический скан.
DEFAULT_MAX_PAIRS = 10


class SignalScanner:
    """
    Главный сканер рынка.

    Поддерживает:

    - одну конкретную пару;
    - все пары;
    - expiry 1..20;
    - "any";
    - автоматический режим;
    - ручной режим;
    - выбор лучшего кандидата;
    - построение графика;
    - передачу графика дальше в signal_service.
    """

    def __init__(
        self,
        market=None,
        engine: Optional[SignalEngine] = None,
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

        self._semaphore = asyncio.Semaphore(
            ANALYSIS_CONCURRENCY
        )

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _normalize_pair(
        pair: str,
    ) -> str:

        value = str(pair).strip().upper()

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
    def _normalize_expiry(
        expiry_minutes,
    ) -> Optional[int]:

        if expiry_minutes is None:
            return None

        if isinstance(
            expiry_minutes,
            str,
        ):

            value = expiry_minutes.strip().lower()

            if value in {
                "any",
                "auto",
                "anytime",
                "любое",
                "любое время",
            }:
                return None

        try:
            value = int(
                expiry_minutes
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if value < 1 or value > 20:
            return None

        return value

    @staticmethod
    def _is_any_expiry(
        expiry_minutes,
    ) -> bool:

        if expiry_minutes is None:
            return True

        if isinstance(
            expiry_minutes,
            str,
        ):

            return (
                expiry_minutes.strip().lower()
                in {
                    "any",
                    "auto",
                    "anytime",
                    "любое",
                    "любое время",
                }
            )

        return False

    @staticmethod
    def _best(
        candidates: Iterable[
            Optional[SignalCandidate]
        ],
    ) -> Optional[SignalCandidate]:

        valid = [
            item
            for item in candidates
            if item is not None
        ]

        if not valid:
            return None

        # Основной приоритет:
        #
        # 1. качество
        # 2. исторический winrate
        # 3. confidence
        # 4. количество подтверждений
        # 5. количество исторических сделок
        #
        # Таким образом бот не выбирает просто
        # сигнал с большим количеством сделок,
        # если качество хуже.

        valid.sort(
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
                int(
                    getattr(
                        item,
                        "winrate_trades",
                        0,
                    )
                    or 0
                ),
            ),
            reverse=True,
        )

        return valid[0]

    # ==========================================================
    # MARKET DATA
    # ==========================================================

    async def _load_data(
        self,
        pairs: List[str],
    ) -> Dict[
        str,
        pd.DataFrame,
    ]:

        if not pairs:
            return {}

        normalized_pairs = list(
            dict.fromkeys(
                self._normalize_pair(
                    pair
                )
                for pair in pairs
            )
        )

        logger.info(
            "Loading market data for %d pairs",
            len(normalized_pairs),
        )

        try:

            data = (
                await self.market.get_candles_many(
                    normalized_pairs,
                    interval="1min",
                    outputsize=CANDLE_OUTPUTSIZE,
                    force_refresh=True,
                )
            )

        except Exception:
            logger.exception(
                "Failed to load market data"
            )

            return {}

        normalized_data: Dict[
            str,
            pd.DataFrame,
        ] = {}

        for key, dataframe in (
            data or {}
        ).items():

            normalized_key = (
                self._normalize_pair(
                    key
                )
            )

            if (
                dataframe is None
                or dataframe.empty
            ):
                continue

            normalized_data[
                normalized_key
            ] = dataframe

        logger.info(
            "Market data loaded: %d/%d",
            len(normalized_data),
            len(normalized_pairs),
        )

        return normalized_data

    # ==========================================================
    # ENGINE
    # ==========================================================

    async def _analyze(
        self,
        pair: str,
        market_type: str,
        dataframe: pd.DataFrame,
        expiry: int,
        source: str,
    ) -> Optional[
        SignalCandidate
    ]:

        async with self._semaphore:

            try:

                return await asyncio.to_thread(
                    self.engine.analyze,
                    pair,
                    market_type,
                    dataframe,
                    expiry,
                    source,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "%s | engine analysis failed",
                    pair,
                )

                return None

    async def _analyze_any(
        self,
        pair: str,
        market_type: str,
        dataframe: pd.DataFrame,
        source: str,
    ) -> Optional[
        SignalCandidate
    ]:

        async with self._semaphore:

            try:

                return await asyncio.to_thread(
                    self.engine.analyze_any_time,
                    pair,
                    market_type,
                    dataframe,
                    source,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "%s | any-time engine analysis failed",
                    pair,
                )

                return None

    # ==========================================================
    # CHART
    # ==========================================================

    @staticmethod
    def _attach_chart(
        candidate: Optional[SignalCandidate],
        dataframe: Optional[pd.DataFrame],
    ) -> Optional[SignalCandidate]:

        if candidate is None:
            return None

        if (
            dataframe is None
            or dataframe.empty
        ):
            return candidate

        try:

            chart_path = (
                create_signal_chart(
                    df=dataframe,
                    pair=candidate.pair,
                    direction=candidate.direction,
                    expiry_minutes=int(
                        candidate.expiry_minutes
                    ),
                    entry_price=float(
                        candidate.entry_price
                    ),
                )
            )

            if chart_path:

                candidate.chart_path = (
                    chart_path
                )

                metadata = getattr(
                    candidate,
                    "metadata",
                    None,
                )

                if not isinstance(
                    metadata,
                    dict,
                ):
                    metadata = {}

                metadata[
                    "chart_path"
                ] = chart_path

                candidate.metadata = (
                    metadata
                )

                logger.info(
                    "%s | chart attached: %s",
                    candidate.pair,
                    chart_path,
                )

        except Exception:
            logger.exception(
                "%s | chart creation failed",
                candidate.pair,
            )

        return candidate

    # ==========================================================
    # ONE PAIR
    # ==========================================================

    async def scan_pair(
        self,
        pair: str,
        expiry_minutes="any",
        market: str = "regular",
        source: str = "manual",
    ) -> Optional[
        SignalCandidate
    ]:

        # ------------------------------------------------------
        # ALL PAIRS
        # ------------------------------------------------------

        if str(pair).strip().upper() in {
            "ALL",
            "__ALL__",
            "ALL_PAIRS",
        }:

            return await self.scan(
                market=market,
                expiry_minutes=expiry_minutes,
                max_pairs=DEFAULT_MAX_PAIRS,
                source=source,
            )

        normalized_pair = (
            self._normalize_pair(
                pair
            )
        )

        logger.info(
            "Starting single-pair scan: "
            "pair=%s market=%s expiry=%s source=%s",
            normalized_pair,
            market,
            expiry_minutes,
            source,
        )

        data = await self._load_data(
            [normalized_pair]
        )

        dataframe = data.get(
            normalized_pair
        )

        if (
            dataframe is None
            or dataframe.empty
        ):
            logger.warning(
                "%s | no candle data",
                normalized_pair,
            )

            return None

        # ------------------------------------------------------
        # ANY EXPIRY
        # ------------------------------------------------------

        if self._is_any_expiry(
            expiry_minutes
        ):

            candidate = (
                await self._analyze_any(
                    normalized_pair,
                    market,
                    dataframe,
                    source,
                )
            )

        # ------------------------------------------------------
        # FIXED EXPIRY
        # ------------------------------------------------------

        else:

            expiry = (
                self._normalize_expiry(
                    expiry_minutes
                )
            )

            if expiry is None:
                logger.warning(
                    "%s | invalid expiry=%s",
                    normalized_pair,
                    expiry_minutes,
                )

                return None

            candidate = await self._analyze(
                normalized_pair,
                market,
                dataframe,
                expiry,
                source,
            )

        return self._attach_chart(
            candidate,
            dataframe,
        )

    # ==========================================================
    # ALL PAIRS
    # ==========================================================

    async def scan(
        self,
        pairs: Optional[
            Iterable[str]
        ] = None,
        market: str = "regular",
        expiry_minutes="any",
        max_pairs: int = DEFAULT_MAX_PAIRS,
        source: str = "manual",
    ) -> Optional[
        SignalCandidate
    ]:

        market_name = (
            str(market)
            .strip()
            .lower()
        )

        # ------------------------------------------------------
        # PAIRS
        # ------------------------------------------------------

        if pairs is None:

            try:
                available = (
                    pair_selector.available_pairs(
                        market_name
                    )
                )

            except Exception:
                logger.exception(
                    "Failed to get available pairs"
                )

                available = ()

            pair_list = list(
                available
            )

        else:

            pair_list = list(
                pairs
            )

        # Убираем дубли.
        pair_list = list(
            dict.fromkeys(
                self._normalize_pair(
                    pair
                )
                for pair in pair_list
            )
        )

        # Ограничиваем количество.
        try:
            limit = int(
                max_pairs
            )
        except (
            TypeError,
            ValueError,
        ):
            limit = DEFAULT_MAX_PAIRS

        limit = max(
            1,
            min(
                10,
                limit,
            ),
        )

        pair_list = (
            pair_list[:limit]
        )

        if not pair_list:

            logger.warning(
                "No pairs available for market=%s",
                market_name,
            )

            return None

        logger.info(
            "Starting scan: "
            "market=%s pairs=%d expiry=%s source=%s",
            market_name,
            len(pair_list),
            expiry_minutes,
            source,
        )

        # ------------------------------------------------------
        # DATA
        # ------------------------------------------------------

        data = await self._load_data(
            pair_list
        )

        if not data:

            logger.warning(
                "No market data available"
            )

            return None

        # ------------------------------------------------------
        # ANALYSIS
        # ------------------------------------------------------

        tasks = []

        any_expiry = (
            self._is_any_expiry(
                expiry_minutes
            )
        )

        fixed_expiry = None

        if not any_expiry:

            fixed_expiry = (
                self._normalize_expiry(
                    expiry_minutes
                )
            )

            if fixed_expiry is None:

                logger.warning(
                    "Invalid expiry=%s",
                    expiry_minutes,
                )

                return None

        for pair in pair_list:

            dataframe = data.get(
                pair
            )

            if (
                dataframe is None
                or dataframe.empty
            ):
                continue

            if any_expiry:

                tasks.append(
                    self._analyze_any(
                        pair,
                        market_name,
                        dataframe,
                        source,
                    )
                )

            else:

                tasks.append(
                    self._analyze(
                        pair,
                        market_name,
                        dataframe,
                        fixed_expiry,
                        source,
                    )
                )

        if not tasks:

            logger.warning(
                "No analyzable pairs"
            )

            return None

        results = await asyncio.gather(
            *tasks
        )

        candidate = self._best(
            results
        )

        if candidate is None:

            logger.info(
                "No qualifying candidate: "
                "market=%s pairs=%d expiry=%s",
                market_name,
                len(pair_list),
                expiry_minutes,
            )

            return None

        # ------------------------------------------------------
        # CHART
        # ------------------------------------------------------

        dataframe = data.get(
            self._normalize_pair(
                candidate.pair
            )
        )

        candidate = (
            self._attach_chart(
                candidate,
                dataframe,
            )
        )

        logger.info(
            "BEST SIGNAL: "
            "%s | %s | %sm | "
            "quality=%.2f | confidence=%.2f | "
            "winrate=%.2f | confirmations=%s",
            candidate.pair,
            candidate.direction,
            candidate.expiry_minutes,
            float(
                candidate.quality
                or 0
            ),
            float(
                candidate.confidence
                or 0
            ),
            float(
                candidate.winrate
                or 0
            ),
            int(
                candidate.confirmations
                or 0
            ),
        )

        return candidate

    # ==========================================================
    # COMPATIBILITY
    # ==========================================================

    async def scan_market(
        self,
        market: str = "regular",
        expiry_minutes="any",
        max_pairs: int = DEFAULT_MAX_PAIRS,
        source: str = "manual",
    ) -> Optional[
        SignalCandidate
    ]:

        return await self.scan(
            market=market,
            expiry_minutes=expiry_minutes,
            max_pairs=max_pairs,
            source=source,
        )
