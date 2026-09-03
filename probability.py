from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


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
    ) -> None:
        self.minimum_trades = max(
            1,
            minimum_trades,
        )

    @staticmethod
    def _direction(
        row: pd.Series,
    ) -> str | None:
        bullish = 0
        bearish = 0

        if row["ema_fast"] > row["ema_slow"]:
            bullish += 1
        elif row["ema_fast"] < row["ema_slow"]:
            bearish += 1

        if row["close"] > row["ema_trend"]:
            bullish += 1
        elif row["close"] < row["ema_trend"]:
            bearish += 1

        if row["macd"] > row["macd_signal"]:
            bullish += 1
        elif row["macd"] < row["macd_signal"]:
            bearish += 1

        if row["rsi"] >= 55:
            bullish += 1
        elif row["rsi"] <= 45:
            bearish += 1

        if row["stochastic_k"] > row[
            "stochastic_d"
        ]:
            bullish += 1
        elif row["stochastic_k"] < row[
            "stochastic_d"
        ]:
            bearish += 1

        if bullish >= 4 and bullish > bearish:
            return "UP"

        if bearish >= 4 and bearish > bullish:
            return "DOWN"

        return None

    def estimate(
        self,
        df: pd.DataFrame,
        expiry_minutes: int,
    ) -> ProbabilityEstimate:
        from indicators import (
            calculate_indicators,
        )

        calculated = calculate_indicators(df)

        wins = 0
        losses = 0
        draws = 0

        max_index = (
            len(calculated)
            - expiry_minutes
        )

        if max_index <= 0:
            return ProbabilityEstimate(
                winrate=0,
                trades=0,
                wins=0,
                losses=0,
                draws=0,
                reliable=False,
            )

        for index in range(max_index):
            row = calculated.iloc[index]

            direction = self._direction(
                row
            )

            if direction is None:
                continue

            entry = float(
                row["close"]
            )

            future = calculated.iloc[
                index + expiry_minutes
            ]

            close = float(
                future["close"]
            )

            if close == entry:
                draws += 1
                continue

            if (
                direction == "UP"
                and close > entry
            ):
                wins += 1

            elif (
                direction == "DOWN"
                and close < entry
            ):
                wins += 1

            else:
                losses += 1

        trades = (
            wins
            + losses
            + draws
        )

        if trades == 0:
            winrate = 0
        else:
            winrate = (
                wins
                / trades
                * 100
            )

        return ProbabilityEstimate(
            winrate=winrate,
            trades=trades,
            wins=wins,
            losses=losses,
            draws=draws,
            reliable=(
                trades
                >= self.minimum_trades
            ),
        )


probability_calibrator = (
    ProbabilityCalibrator()
)
