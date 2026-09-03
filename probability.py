from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtest import run_backtest


@dataclass(slots=True)
class ProbabilityEstimate:
    winrate: float
    trades: int
    wins: int
    losses: int
    draws: int
    reliable: bool


class ProbabilityCalibrator:
    """
    Оценивает исторический winrate по реальным свечам.

    Важно:
    результат 75% означает, что на доступной истории
    стратегия показала >=75% WIN среди завершённых
    тестовых сделок. Это не является гарантией будущего.
    """

    def __init__(
        self,
        minimum_trades: int = 30,
    ) -> None:
        self.minimum_trades = max(
            1,
            minimum_trades,
        )

    def estimate(
        self,
        df: pd.DataFrame,
        expiry_minutes: int,
    ) -> ProbabilityEstimate:
        result = run_backtest(
            df=df,
            expiry_minutes=expiry_minutes,
        )

        reliable = (
            result.total_trades
            >= self.minimum_trades
        )

        return ProbabilityEstimate(
            winrate=result.winrate,
            trades=result.total_trades,
            wins=result.wins,
            losses=result.losses,
            draws=result.draws,
            reliable=reliable,
        )

    def meets_minimum(
        self,
        estimate: ProbabilityEstimate,
        minimum_winrate: float = 75.0,
    ) -> bool:
        return (
            estimate.reliable
            and estimate.winrate
            >= max(
                75.0,
                minimum_winrate,
            )
        )


probability_calibrator = ProbabilityCalibrator(
    minimum_trades=30
)
