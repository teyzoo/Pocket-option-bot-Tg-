from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from indicators import calculate_indicators


@dataclass(slots=True)
class BacktestResult:
    total_trades: int
    wins: int
    losses: int
    draws: int
    winrate: float


def _direction_from_row(
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

    if row["stochastic_k"] >= row["stochastic_d"]:
        bullish += 1
    elif row["stochastic_k"] < row["stochastic_d"]:
        bearish += 1

    if bullish >= 4 and bullish > bearish:
        return "UP"

    if bearish >= 4 and bearish > bullish:
        return "DOWN"

    return None


def run_backtest(
    df: pd.DataFrame,
    expiry_minutes: int,
) -> BacktestResult:
    if expiry_minutes < 1:
        raise ValueError(
            "expiry_minutes must be >= 1"
        )

    calculated = calculate_indicators(df)

    wins = 0
    losses = 0
    draws = 0

    total = len(calculated) - expiry_minutes

    if total <= 0:
        return BacktestResult(
            total_trades=0,
            wins=0,
            losses=0,
            draws=0,
            winrate=0.0,
        )

    for index in range(total):
        row = calculated.iloc[index]

        direction = _direction_from_row(row)

        if direction is None:
            continue

        entry = float(row["close"])

        future = calculated.iloc[
            index + expiry_minutes
        ]

        close = float(future["close"])

        if direction == "UP":
            if close > entry:
                wins += 1
            elif close < entry:
                losses += 1
            else:
                draws += 1

        else:
            if close < entry:
                wins += 1
            elif close > entry:
                losses += 1
            else:
                draws += 1

    evaluated = wins + losses + draws

    if evaluated == 0:
        winrate = 0.0
    else:
        winrate = (
            wins
            / evaluated
            * 100
        )

    return BacktestResult(
        total_trades=evaluated,
        wins=wins,
        losses=losses,
        draws=draws,
        winrate=winrate,
    )
