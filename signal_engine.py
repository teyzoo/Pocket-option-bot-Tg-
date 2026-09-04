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
        minimum_trades: int = 10,
        minimum_winrate: float = 75.0,
    ) -> None:
        self.minimum_trades = max(
            1,
            int(minimum_trades),
        )

        self.minimum_winrate = max(
            0.0,
            min(
                100.0,
                float(minimum_winrate),
            ),
        )

    def estimate(
        self,
        df: pd.DataFrame,
        expiry_minutes: int,
        direction: str | None = None,
    ) -> ProbabilityEstimate:

        if df is None or df.empty:
            return ProbabilityEstimate(
                winrate=0.0,
                trades=0,
                wins=0,
                losses=0,
                draws=0,
                reliable=False,
            )

        try:
            expiry = max(
                1,
                int(expiry_minutes),
            )
        except (
            TypeError,
            ValueError,
        ):
            expiry = 1

        try:
            result: BacktestResult = run_backtest(
                df,
                expiry,
                direction=direction,
            )
        except Exception:
            return ProbabilityEstimate(
                winrate=0.0,
                trades=0,
                wins=0,
                losses=0,
                draws=0,
                reliable=False,
            )

        trades = max(
            0,
            int(result.decisive_trades),
        )

        wins = max(
            0,
            int(result.wins),
        )

        losses = max(
            0,
            int(result.losses),
        )

        draws = max(
            0,
            int(result.draws),
        )

        winrate = float(
            result.winrate or 0.0
        )

        reliable = (
            trades >= self.minimum_trades
        )

        return ProbabilityEstimate(
            winrate=winrate,
            trades=trades,
            wins=wins,
            losses=losses,
            draws=draws,
            reliable=reliable,
        )

    def meets_minimum(
        self,
        estimate: ProbabilityEstimate,
    ) -> bool:

        if estimate is None:
            return False

        return (
            estimate.reliable
            and float(estimate.winrate)
            >= self.minimum_winrate
        )


probability_calibrator = ProbabilityCalibrator(
    minimum_trades=10,
    minimum_winrate=75.0,
)
