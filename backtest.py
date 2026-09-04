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

    scores = {
        "UP": 0.0,
        "DOWN": 0.0,
    }

    confirmations = {
        "UP": 0,
        "DOWN": 0,
    }

    reasons = {
        "UP": [],
        "DOWN": [],
    }

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
        scores["UP"] += 15
        confirmations["UP"] += 1
        reasons["UP"].append(
            "EMA"
        )
    elif ema_fast < ema_slow:
        scores["DOWN"] += 15
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "EMA"
        )

    if close > ema_trend:
        scores["UP"] += 15
        confirmations["UP"] += 1
        reasons["UP"].append(
            "TREND"
        )
    elif close < ema_trend:
        scores["DOWN"] += 15
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "TREND"
        )

    if rsi >= 55:
        scores["UP"] += 10
        confirmations["UP"] += 1
        reasons["UP"].append(
            "RSI"
        )
    elif rsi <= 45:
        scores["DOWN"] += 10
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "RSI"
        )

    if macd > macd_signal:
        scores["UP"] += 15
        confirmations["UP"] += 1
        reasons["UP"].append(
            "MACD"
        )
    elif macd < macd_signal:
        scores["DOWN"] += 15
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "MACD"
        )

    if close > bb_middle:
        scores["UP"] += 10
        confirmations["UP"] += 1
        reasons["UP"].append(
            "BB"
        )
    elif close < bb_middle:
        scores["DOWN"] += 10
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "BB"
        )

    if stoch_k > stoch_d:
        scores["UP"] += 10
        confirmations["UP"] += 1
        reasons["UP"].append(
            "STOCHASTIC"
        )
    elif stoch_k < stoch_d:
        scores["DOWN"] += 10
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "STOCHASTIC"
        )

    if bullish:
        scores["UP"] += 15
        confirmations["UP"] += 1
        reasons["UP"].append(
            "PRICE_ACTION"
        )
    elif bearish:
        scores["DOWN"] += 15
        confirmations["DOWN"] += 1
        reasons["DOWN"].append(
            "PRICE_ACTION"
        )

    if (
        scores["UP"] <= 0
        and scores["DOWN"] <= 0
    ):
        return None, 0, 0.0, []

    direction = (
        "UP"
        if scores["UP"] > scores["DOWN"]
        else "DOWN"
    )

    if scores["UP"] == scores["DOWN"]:
        return None, 0, 0.0, []

    score = scores[direction]
    confirmation_count = confirmations[direction]

    if confirmation_count < MIN_SIGNAL_CONFIRMATIONS:
        return (
            None,
            confirmation_count,
            0.0,
            reasons[direction],
        )

    confidence = min(
        100.0,
        50.0 + (
            score / 100.0 * 50.0
        ),
    )

    return (
        direction,
        confirmation_count,
        confidence,
        reasons[direction],
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
    direction: str | None = None,
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
            predicted,
            confirmations,
            confidence,
            _,
        ) = _evaluate_row(row)

        if predicted is None:
            continue

        if direction is not None:
            if predicted != direction:
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
        elif actual == predicted:
            wins += 1
        else:
            losses += 1

    return BacktestResult(
        total=total,
        wins=wins,
        losses=losses,
        draws=draws,
    )
