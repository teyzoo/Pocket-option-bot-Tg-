from __future__ import annotations

from candle_filter import candle_filter
from chart_generator import chart_generator
from config import MAX_CANDLES
from market import MarketClient
from pair_selector import pair_selector
from signal_engine import SignalEngine


class AnalysisService:
    def __init__(
        self,
        market: MarketClient,
        engine: SignalEngine,
    ) -> None:
        self.market = market
        self.engine = engine

    async def analyze(
        self,
        pair: str,
        market: str,
        expiry_minutes: int = 5,
    ):
        if not pair_selector.is_allowed(
            pair,
            market,
        ):
            return None, None

        df = await self.market.get_candles(
            pair,
            interval="1min",
            outputsize=MAX_CANDLES,
        )

        filtered = candle_filter.apply(
            df
        )

        if len(filtered) < 80:
            return None, filtered

        candidate = self.engine.analyze(
            pair=pair,
            market=market,
            df=filtered,
            expiry_minutes=expiry_minutes,
            source="analysis",
        )

        if candidate is not None:
            candidate.chart_path = (
                chart_generator.generate(
                    filtered,
                    candidate,
                )
            )

        return candidate, filtered
