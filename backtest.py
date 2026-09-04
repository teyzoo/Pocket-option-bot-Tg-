from __future__ import annotations

import pandas as pd

from config import MIN_SIGNAL_CONFIRMATIONS
from indicators import calculate_indicators
from models import BacktestResult


def _safe_float(value) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if pd.isna(result):
        return None

    return result


def _evaluate_row(
    row: pd.Series,
) -> tuple[
    str | None,
    int,
    float,
    list[str],
]:
    score = 0.0
    confirmations = 0
    reasons: list[str] = []

    close = _safe_float(row.get("close"))
    ema_fast = _safe_float(row.get("ema_fast"))
    ema_slow = _safe_float(row.get("ema_slow"))
    ema_trend = _safe_float(row.get("ema_trend"))
    rsi = _safe_float(row.get("rsi"))
    macd = _safe_float(row.get("macd"))
    macd_signal = _safe_float(row.get("macd_signal"))
    bb_middle = _safe_float(
        row.get("bollinger_middle")
    )
    stoch_k = _safe_float(
        row.get("stochastic_k")
    )
    stoch_d = _safe_float(
        row.get("stochastic_d")
    )

    bullish = bool(
        row.get("bullish", False)
    )

    bearish = bool(
        row.get("bearish", False)
    )

    required = (
        close,
        ema_fast,
        ema_slow,
        ema_trend,
        rsi,
        macd,
        macd_signal,
        bb_middle,
        stoch_k,
        stoch_d,
    )

    if any(
        value is None
        for value in required
    ):
        return None, 0, 0.0, []

    if ema_fast > ema_slow:
        score += 15.0
        confirmations += 1
        reasons.append(
            "EMA 9 выше EMA 21"
        )
    elif ema_fast < ema_slow:
        score -= 15.0
        confirmations += 1
        reasons.append(
            "EMA 9 ниже EMA 21"
        )

    if close > ema_trend:
        score += 15.0
        confirmations += 1
        reasons.append(
            "Цена выше EMA 50"
        )
    elif close < ema_trend:
        score -= 15.0
        confirmations += 1
        reasons.append(
            "Цена ниже EMA 50"
        )

    if rsi >= 55.0:
        score += 10.0
        confirmations += 1
        reasons.append(
            "RSI подтверждает рост"
        )
    elif rsi <= 45.0:
        score -= 10.0
        confirmations += 1
        reasons.append(
            "RSI подтверждает снижение"
        )

    if macd > macd_signal:
        score += 15.0
        confirmations += 1
        reasons.append(
            "MACD бычий"
        )
    elif macd < macd_signal:
        score -= 15.0
        confirmations += 1
        reasons.append(
            "MACD медвежий"
        )

    if close > bb_middle:
        score += 10.0
        confirmations += 1
        reasons.append(
            "Цена выше средней Bollinger"
        )
    elif close < bb_middle:
        score -= 10.0
        confirmations += 1
        reasons.append(
            "Цена ниже средней Bollinger"
        )

    if (
        stoch_k > stoch_d
        and stoch_k < 80.0
    ):
        score += 10.0
        confirmations += 1
        reasons.append(
            "Stochastic подтверждает рост"
        )
    elif (
        stoch_k < stoch_d
        and stoch_k > 20.0
    ):
        score -= 10.0
        confirmations += 1
        reasons.append(
            "Stochastic подтверждает снижение"
        )

    if bullish:
        score += 5.0
    elif bearish:
        score -= 5.0

    if score > 0:
        direction = "UP"
    elif score < 0:
        direction = "DOWN"
    else:
        return (
            None,
            confirmations,
            50.0,
            reasons,
        )

    confidence = (
        50.0
        + abs(score) / 95.0 * 50.0
    )

    confidence = max(
        0.0,
        min(
            100.0,
            confidence,
        ),
    )

    if confirmations < MIN_SIGNAL_CONFIRMATIONS:
        return (
            None,
            confirmations,
            confidence,
            reasons,
        )

    if confidence < 75.0:
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
) -> tuple[
    str | None,
    int,
    float,
    list[str],
]:
    return _evaluate_row(row)


def run_backtest(
    df: pd.DataFrame,
    expiry_minutes: int,
) -> BacktestResult:

    empty = BacktestResult(
        total=0,
        wins=0,
        losses=0,
        draws=0,
    )

    if df is None or df.empty:
        return empty

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
        data = calculate_indicators(df)
    except Exception:
        return empty

    if data is None or data.empty:
        return empty

    minimum_history = 60

    if len(data) <= (
        minimum_history + expiry
    ):
        return empty

    total = 0
    wins = 0
    losses = 0
    draws = 0

    last_index = len(data) - expiry

    for index in range(
        minimum_history,
        last_index,
    ):
        row = data.iloc[index]

        (
            direction,
            confirmations,
            confidence,
            _,
        ) = _evaluate_row(row)

        if direction is None:
            continue

        if confirmations < MIN_SIGNAL_CONFIRMATIONS:
            continue

        if confidence < 75.0:
            continue

        entry = _safe_float(
            row.get("close")
        )

        if entry is None:
            continue

        future_row = data.iloc[
            index + expiry
        ]

        future_close = _safe_float(
            future_row.get("close")
        )

        if future_close is None:
            continue

        total += 1

        if future_close > entry:
            actual = "UP"
        elif future_close < entry:
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
