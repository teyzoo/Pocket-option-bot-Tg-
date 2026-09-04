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
    """
    Историческая оценка вероятности сигнала.

    ВАЖНО:
    reliable означает только то, что исторической выборки
    достаточно для базовой оценки.

    Сам WINRATE по-прежнему должен проходить отдельный
    фильтр MIN_SIGNAL_WINRATE в SignalEngine.
    """

    def __init__(
        self,
        minimum_trades: int = 10,
        minimum_winrate: float = 75.0,
    ) -> None:
        # 10 сделок — минимальная техническая выборка.
        #
        # Само значение WINRATE всё равно проверяется отдельно.
        # Это не означает, что бот будет выдавать сигнал с WINRATE ниже
        # установленного порога.
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
            return ProbabilityEstimate(
                winrate=0.0,
                trades=0,
                wins=0,
                losses=0,
                draws=0,
                reliable=False,
            )

        try:
            result: BacktestResult = run_backtest(
                df,
                expiry,
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

        return ProbabilityEstimate(
            winrate=float(
                result.winrate or 0.0
            ),
            trades=trades,
            wins=wins,
            losses=losses,
            draws=draws,
            reliable=(
                trades >= self.minimum_trades
            ),
        )

    def meets_minimum(
        self,
        estimate: ProbabilityEstimate,
    ) -> bool:
        if estimate is None:
            return False

        if not estimate.reliable:
            return False

        return (
            float(estimate.winrate)
            >= self.minimum_winrate
        )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

probability_calibrator = ProbabilityCalibrator(
    minimum_trades=10,
    minimum_winrate=75.0,
)
