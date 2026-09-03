from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtest import run_backtest
from models import BacktestResult


@dataclass(slots=True)
class ProbabilityEstimate:
    winrate: float
    trades: int
    wins: int
    losses: int
    draws: int
    reliable: bool


class ProbabilityCalibrator:
    def __init__(
        self,
        minimum_trades: int = 30,
        minimum_winrate: float = 75.0,
    ) -> None:
        self.minimum_trades = max(
            1,
            minimum_trades,
        )

        self.minimum_winrate = max(
            75.0,
            minimum_winrate,
        )

    def estimate(
        self,
        df: pd.DataFrame,
        expiry_minutes: int,
    ) -> ProbabilityEstimate:
        result: BacktestResult = run_backtest(
            df,
            expiry_minutes,
        )

        return ProbabilityEstimate(
            winrate=result.winrate,
            trades=result.decisive_trades,
            wins=result.wins,
            losses=result.losses,
            draws=result.draws,
            reliable=(
                result.decisive_trades
                >= self.minimum_trades
            ),
        )

    def meets_minimum(
        self,
        estimate: ProbabilityEstimate,
    ) -> bool:
        return (
            estimate.reliable
            and estimate.winrate
            >= self.minimum_winrate
        )
