from __future__ import annotations

import asyncio
from typing import Iterable

from candle_filter import candle_filter_service
from config import (
    MAX_CANDLES,
    MAX_EXPIRY_MINUTES,
    MIN_CANDLES_REQUIRED,
    MIN_EXPIRY_MINUTES,
)
from market import MarketClient, market_client
from models import SignalCandidate
from pair_selector import pair_selector
from signal_engine import SignalEngine


class SignalScanner:
    """
    Центральный сканер рынка.

    Поддерживает:

    - одну пару;
    - несколько пар;
    - конкретную экспирацию 1..20 минут;
    - автоматический режим "any";
    - ограничение количества пар;
    - сохранение старого API.
    """

    def __init__(
        self,
        market: MarketClient | None = None,
        engine: SignalEngine | None = None,
    ) -> None:
        # ----------------------------------------------------
        # Если зависимости не переданы,
        # используем глобальные экземпляры.
        # ----------------------------------------------------

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

    # ========================================================
    # EXPIRY NORMALIZATION
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

    # ========================================================
    # SCAN ONE PAIR
    # ========================================================

    async def scan_pair(
        self,
        pair: str,
        market: str,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:
        """
        Анализирует одну пару.
        """

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is None:
            return None

        # ----------------------------------------------------
        # Проверка пары.
        # ----------------------------------------------------

        if not pair_selector.is_allowed(
            pair,
            market,
        ):
            return None

        # ----------------------------------------------------
        # Получаем свечи.
        # ----------------------------------------------------

        df = await self.market.get_candles(
            symbol=pair,
            interval="1min",
            outputsize=MAX_CANDLES,
        )

        if df is None or df.empty:
            return None

        # ----------------------------------------------------
        # Candle filter.
        # ----------------------------------------------------

        filtered = await candle_filter_service.apply(
            df
        )

        if filtered is None:
            return None

        if len(filtered) < MIN_CANDLES_REQUIRED:
            return None

        # ----------------------------------------------------
        # Signal Engine.
        # ----------------------------------------------------

        return self.engine.analyze(
            pair=pair,
            market=market,
            df=filtered,
            expiry_minutes=expiry,
            source=source,
        )

    # ========================================================
    # SCAN MANY PAIRS
    # ========================================================

    async def scan(
        self,
        market: str,
        expiry_minutes,
        pairs: Iterable[str] | None = None,
        source: str = "manual",
        max_pairs: int | None = None,
    ) -> SignalCandidate | None:
        """
        Сканирует пары и возвращает лучший сигнал.

        expiry_minutes:
            1..20
            или "any".

        При "any":
            проверяются все экспирации от 1 до 20 минут.
        """

        # ----------------------------------------------------
        # Формируем список пар.
        # ----------------------------------------------------

        if pairs is None:
            pairs = pair_selector.available_pairs(
                market
            )

        pair_list = list(pairs)

        if max_pairs is not None:
            try:
                max_pairs = int(
                    max_pairs
                )
            except (
                TypeError,
                ValueError,
            ):
                max_pairs = None

        if max_pairs is not None:
            max_pairs = max(
                1,
                min(
                    len(pair_list),
                    max_pairs,
                ),
            )

            pair_list = pair_list[
                :max_pairs
            ]

        if not pair_list:
            return None

        # ----------------------------------------------------
        # Режим "Любое время".
        # ----------------------------------------------------

        if (
            isinstance(
                expiry_minutes,
                str,
            )
            and expiry_minutes.strip().lower()
            in {
                "any",
                "all",
                "любое",
                "любое время",
            }
        ):
            return await self._scan_any_expiry(
                market=market,
                pairs=pair_list,
                source=source,
            )

        # ----------------------------------------------------
        # Обычный режим.
        # ----------------------------------------------------

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is None:
            return None

        candidates: list[
            SignalCandidate
        ] = []

        # ----------------------------------------------------
        # Пары анализируем последовательно.
        #
        # Это безопаснее для лимитов Twelve Data.
        # ----------------------------------------------------

        for pair in pair_list:
            try:
                candidate = await self.scan_pair(
                    pair=pair,
                    market=market,
                    expiry_minutes=expiry,
                    source=source,
                )

                if candidate is not None:
                    candidates.append(
                        candidate
                    )

            except Exception:
                # Ошибка одной пары не должна
                # остановить весь поиск.
                continue

        return self._select_best(
            candidates
        )

    # ========================================================
    # ANY EXPIRY
    # ========================================================

    async def _scan_any_expiry(
        self,
        market: str,
        pairs: list[str],
        source: str,
    ) -> SignalCandidate | None:
        """
        Автоматический режим.

        Проверяет экспирации:
            1, 2, 3 ... 20 минут.

        Для каждой пары стараемся не падать
        при ошибке конкретной комбинации.
        """

        candidates: list[
            SignalCandidate
        ] = []

        # ----------------------------------------------------
        # Чтобы не создавать огромный burst запросов,
        # выполняем комбинации контролируемо.
        # ----------------------------------------------------

        for expiry in range(
            MIN_EXPIRY_MINUTES,
            MAX_EXPIRY_MINUTES + 1,
        ):
            # ------------------------------------------------
            # Параллельно проверяем пары для одной экспирации.
            # ------------------------------------------------

            tasks = [
                self._safe_scan_pair(
                    pair=pair,
                    market=market,
                    expiry=expiry,
                    source=source,
                )
                for pair in pairs
            ]

            results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            for result in results:
                if isinstance(
                    result,
                    SignalCandidate,
                ):
                    candidates.append(
                        result
                    )

        return self._select_best(
            candidates
        )

    # ========================================================
    # SAFE SCAN
    # ========================================================

    async def _safe_scan_pair(
        self,
        pair: str,
        market: str,
        expiry: int,
        source: str,
    ) -> SignalCandidate | None:
        try:
            return await self.scan_pair(
                pair=pair,
                market=market,
                expiry_minutes=expiry,
                source=source,
            )
        except Exception:
            return None

    # ========================================================
    # BEST CANDIDATE
    # ========================================================

    @staticmethod
    def _select_best(
        candidates: list[SignalCandidate],
    ) -> SignalCandidate | None:
        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
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
                        "quality",
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
            ),
        )
