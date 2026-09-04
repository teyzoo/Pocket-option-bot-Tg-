from __future__ import annotations

from typing import Iterable

from candle_filter import candle_filter_service
from config import (
    MAX_CANDLES,
    MIN_CANDLES_REQUIRED,
)
from market import MarketClient
from models import SignalCandidate
from pair_selector import pair_selector
from signal_engine import SignalEngine


class SignalScanner:
    """
    Сканер рынка.

    Получает свечи через MarketClient,
    применяет временный CandleFilter,
    затем передаёт данные в SignalEngine.
    """

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
        """
        Анализирует одну валютную пару.

        expiry_minutes:
            1..20 минут.
        """

        # -----------------------------------------------------------
        # Защита срока экспирации.
        # -----------------------------------------------------------

        try:
            expiry_minutes = int(
                expiry_minutes
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if not 1 <= expiry_minutes <= 20:
            return None

        # -----------------------------------------------------------
        # Проверяем разрешённость пары.
        # -----------------------------------------------------------

        if not pair_selector.is_allowed(
            pair,
            market,
        ):
            return None

        # -----------------------------------------------------------
        # Получаем свечи.
        # -----------------------------------------------------------

        df = await self.market.get_candles(
            pair,
            interval="1min",
            outputsize=MAX_CANDLES,
        )

        # -----------------------------------------------------------
        # Применяем временный фильтр последних свечей.
        #
        # candle_filter_service.apply() является async.
        # -----------------------------------------------------------

        filtered = await candle_filter_service.apply(
            df
        )

        if filtered is None:
            return None

        if len(filtered) < MIN_CANDLES_REQUIRED:
            return None

        # -----------------------------------------------------------
        # Передаём данные в SignalEngine.
        # -----------------------------------------------------------

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
        """
        Сканирует несколько пар и возвращает лучший сигнал.
        """

        # -----------------------------------------------------------
        # Защита срока экспирации.
        # -----------------------------------------------------------

        try:
            expiry_minutes = int(
                expiry_minutes
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if not 1 <= expiry_minutes <= 20:
            return None

        # -----------------------------------------------------------
        # Если список пар не передан,
        # используем разрешённые пары выбранного рынка.
        # -----------------------------------------------------------

        if pairs is None:
            pairs = pair_selector.available_pairs(
                market
            )

        candidates: list[
            SignalCandidate
        ] = []

        # -----------------------------------------------------------
        # Анализируем пары по очереди.
        #
        # Ошибка одной пары не должна ломать весь сканер.
        # -----------------------------------------------------------

        for pair in pairs:
            try:
                candidate = await self.scan_pair(
                    pair=pair,
                    expiry_minutes=expiry_minutes,
                    market=market,
                    source=source,
                )

                if candidate is not None:
                    candidates.append(
                        candidate
                    )

            except Exception:
                # Не даём одной проблемной паре
                # остановить анализ остальных.
                continue

        # -----------------------------------------------------------
        # Подходящих сигналов нет.
        # -----------------------------------------------------------

        if not candidates:
            return None

        # -----------------------------------------------------------
        # Выбираем самый сильный кандидат.
        #
        # Приоритет:
        # 1. исторический winrate;
        # 2. confidence;
        # 3. quality.
        # -----------------------------------------------------------

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
                        "confidence",
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
            ),
        )
