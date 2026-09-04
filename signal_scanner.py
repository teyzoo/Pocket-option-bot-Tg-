from __future__ import annotations

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
            value = int(expiry_minutes)
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
                "all",
                "любое",
                "любое время",
            }
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
            return None

        df = await self.market.get_candles(
            symbol=pair,
            interval="1min",
            outputsize=MAX_CANDLES,
        )

        if df is None or df.empty:
            return None

        filtered = await candle_filter_service.apply(
            df
        )

        if filtered is None:
            return None

        if len(filtered) < MIN_CANDLES_REQUIRED:
            return None

        return filtered

    async def scan_pair(
        self,
        pair: str,
        market: str,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is None:
            return None

        try:
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

        except Exception:
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

            max_pairs = max(
                1,
                min(
                    max_pairs,
                    len(pair_list),
                ),
            )

            pair_list = pair_list[:max_pairs]

        if not pair_list:
            return None

        candidates: list[SignalCandidate] = []

        # ====================================================
        # ОДНА ЭКСПИРАЦИЯ
        # ====================================================

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is not None:
            for pair in pair_list:
                try:
                    df = await self._load_pair(
                        pair,
                        market,
                    )

                    if df is None:
                        continue

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

                except Exception:
                    continue

            return self._select_best(
                candidates
            )

        # ====================================================
        # ЛЮБОЕ ВРЕМЯ
        # ====================================================

        if self._is_any_expiry(
            expiry_minutes
        ):
            return await self._scan_any_expiry(
                market=market,
                pairs=pair_list,
                source=source,
            )

        return None

    async def _scan_any_expiry(
        self,
        market: str,
        pairs: list[str],
        source: str,
    ) -> SignalCandidate | None:

        candidates: list[SignalCandidate] = []

        # ВАЖНО:
        # свечи получаем ОДИН раз на пару.
        # Затем 1..20 минут анализируются локально.
        # Это предотвращает до 160 запросов API.
        for pair in pairs:
            try:
                df = await self._load_pair(
                    pair,
                    market,
                )

                if df is None:
                    continue

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

                    except Exception:
                        continue

            except Exception:
                continue

        return self._select_best(
            candidates
        )

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
