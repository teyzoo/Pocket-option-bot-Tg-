from __future__ import annotations

import pandas as pd

from config import MIN_SIGNAL_CONFIRMATIONS
from indicators import calculate_indicators
from models import BacktestResult


def _safe_float(
    value,
) -> float | None:
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

    close = _safe_float(
        row.get("close")
    )

    ema_fast = _safe_float(
        row.get("ema_fast")
    )

    ema_slow = _safe_float(
        row.get("ema_slow")
    )

    ema_trend = _safe_float(
        row.get("ema_trend")
    )

    rsi = _safe_float(
        row.get("rsi")
    )

    macd = _safe_float(
        row.get("macd")
    )

    macd_signal = _safe_float(
        row.get("macd_signal")
    )

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
        row.get(
            "bullish",
            False,
        )
    )

    bearish = bool(
        row.get(
            "bearish",
            False,
        )
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
        return (
            None,
            0,
            0.0,
            [],
        )

    # ============================================================
    # EMA
    # ============================================================

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

    # ============================================================
    # TREND
    # ============================================================

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

    # ============================================================
    # RSI
    # ============================================================

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

    # ============================================================
    # MACD
    # ============================================================

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

    # ============================================================
    # BOLLINGER
    # ============================================================

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

    # ============================================================
    # STOCHASTIC
    # ============================================================

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

    # ============================================================
    # PRICE ACTION
    # ============================================================

    if bullish:
        score += 5.0

    elif bearish:
        score -= 5.0

    # ============================================================
    # DIRECTION
    # ============================================================

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

    confidence = max(
        0.0,
        min(
            100.0,
            confidence,
        ),
    )

    if direction is None:
        return (
            None,
            confirmations,
            confidence,
            reasons,
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
    """
    Исторический backtest.

    Важно:
    - не использует свечи из будущего для принятия решения;
    - решение принимается на candle[index];
    - результат проверяется на candle[index + expiry];
    """

    if df is None or df.empty:
        return BacktestResult(
            total=0,
            wins=0,
            losses=0,
            draws=0,
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
        data = calculate_indicators(
            df
        )
    except Exception:
        return BacktestResult(
            total=0,
            wins=0,
            losses=0,
            draws=0,
        )

    if data is None or data.empty:
        return BacktestResult(
            total=0,
            wins=0,
            losses=0,
            draws=0,
        )

    # Для EMA50 + остальных индикаторов
    # безопасно начинать после 60 свечей.
    minimum_history = 60

    if len(data) <= (
        minimum_history + expiry
    ):
        return BacktestResult(
            total=0,
            wins=0,
            losses=0,
            draws=0,
        )

    total = 0
    wins = 0
    losses = 0
    draws = 0

    last_index = (
        len(data)
        - expiry
    )

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
        ) = _evaluate_row(
            row
        )

        if direction is None:
            continue

        if (
            confirmations
            < MIN_SIGNAL_CONFIRMATIONS
        ):
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

        close_price = _safe_float(
            future_row.get("close")
        )

        if close_price is None:
            continue

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
