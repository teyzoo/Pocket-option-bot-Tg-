from __future__ import annotations

import pandas as pd

from config import (
    MIN_SIGNAL_CONFIRMATIONS,
)
from indicators import calculate_indicators
from models import BacktestResult


def _evaluate_row(
    row: pd.Series,
) -> tuple[str | None, int, float, list[str]]:
    score = 0.0
    confirmations = 0
    reasons: list[str] = []

    close = row.get("close")
    ema_fast = row.get("ema_fast")
    ema_slow = row.get("ema_slow")
    ema_trend = row.get("ema_trend")
    rsi = row.get("rsi")
    macd = row.get("macd")
    macd_signal = row.get("macd_signal")
    bb_middle = row.get("bollinger_middle")
    bb_upper = row.get("bollinger_upper")
    bb_lower = row.get("bollinger_lower")
    stoch_k = row.get("stochastic_k")
    stoch_d = row.get("stochastic_d")
    bullish = bool(row.get("bullish", False))
    bearish = bool(row.get("bearish", False))

    required = (
        close,
        ema_fast,
        ema_slow,
        ema_trend,
        rsi,
        macd,
        macd_signal,
        bb_middle,
        bb_upper,
        bb_lower,
        stoch_k,
        stoch_d,
    )

    if any(
        value is None
        or pd.isna(value)
        for value in required
    ):
        return None, 0, 0.0, []

    if ema_fast > ema_slow:
        score += 15
        confirmations += 1
        reasons.append("EMA 9 выше EMA 21")
    elif ema_fast < ema_slow:
        score -= 15
        confirmations += 1
        reasons.append("EMA 9 ниже EMA 21")

    if close > ema_trend:
        score += 15
        confirmations += 1
        reasons.append("Цена выше EMA 50")
    elif close < ema_trend:
        score -= 15
        confirmations += 1
        reasons.append("Цена ниже EMA 50")

    if rsi >= 55:
        score += 10
        confirmations += 1
        reasons.append("RSI подтверждает рост")
    elif rsi <= 45:
        score -= 10
        confirmations += 1
        reasons.append("RSI подтверждает снижение")

    if macd > macd_signal:
        score += 15
        confirmations += 1
        reasons.append("MACD бычий")
    elif macd < macd_signal:
        score -= 15
        confirmations += 1
        reasons.append("MACD медвежий")

    if close > bb_middle:
        score += 10
        confirmations += 1
        reasons.append("Цена выше средней Bollinger")
    elif close < bb_middle:
        score -= 10
        confirmations += 1
        reasons.append("Цена ниже средней Bollinger")

    if stoch_k > stoch_d and stoch_k < 80:
        score += 10
        confirmations += 1
        reasons.append("Stochastic подтверждает рост")
    elif stoch_k < stoch_d and stoch_k > 20:
        score -= 10
        confirmations += 1
        reasons.append("Stochastic подтверждает снижение")

    if bullish:
        score += 5
    elif bearish:
        score -= 5

    if score > 0:
        direction = "UP"
    elif score < 0:
        direction = "DOWN"
    else:
        direction = None

    confidence = (
        50.0
        + abs(score) / 95.0 * 50.0
    )

    if (
        direction is None
        or confirmations < MIN_SIGNAL_CONFIRMATIONS
        or confidence < 75.0
    ):
        return (
            None,
            confirmations,
            confidence,
            reasons,
        )

    return (
        direction,
        confirmations,
        confidence,
        reasons,
    )


def evaluate_row(
    row: pd.Series,
) -> tuple[str | None, int, float, list[str]]:
    return _evaluate_row(row)


def run_backtest(
    df: pd.DataFrame,
    expiry_minutes: int,
) -> BacktestResult:
    if df.empty:
        return BacktestResult(
            total=0,
            wins=0,
            losses=0,
            draws=0,
        )

    expiry_minutes = max(
        1,
        int(expiry_minutes),
    )

    data = calculate_indicators(df)

    total = 0
    wins = 0
    losses = 0
    draws = 0

    minimum_history = 60

    for index in range(
        minimum_history,
        len(data) - expiry_minutes,
    ):
        history = data.iloc[: index + 1]

        row = history.iloc[-1]

        direction, confirmations, confidence, _ = (
            _evaluate_row(row)
        )

        if direction is None:
            continue

        if confirmations < MIN_SIGNAL_CONFIRMATIONS:
            continue

        if confidence < 75.0:
            continue

        entry = float(row["close"])

        future_row = data.iloc[
            index + expiry_minutes
        ]

        close_price = float(
            future_row["close"]
        )

        total += 1

        if close_price > entry:
            actual = "UP"
        elif close_price < entry:
            actual = "DOWN"
        else:
            actual = "DRAW"

        if actual == "DRAW":
            draws += 1
        elif actual == direction:
            wins += 1
        else:
            losses += 1

    return BacktestResult(
        total=total,
        wins=wins,
        losses=losses,
        draws=draws,
    )
