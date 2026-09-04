from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from config import MIN_SIGNAL_CONFIRMATIONS
from indicators import calculate_indicators


@dataclass
class BacktestResult:
    total: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def decisive_trades(self) -> int:
        return self.wins + self.losses

    @property
    def winrate(self) -> float:
        decisive = self.decisive_trades

        if decisive <= 0:
            return 0.0

        return self.wins / decisive * 100.0

    @property
    def reliable(self) -> bool:
        return self.decisive_trades >= 10


def _series(
    df: pd.DataFrame,
    column: str,
    default: float = 0.0,
) -> pd.Series:

    if column not in df.columns:
        return pd.Series(
            default,
            index=df.index,
            dtype=float,
        )

    return (
        pd.to_numeric(
            df[column],
            errors="coerce",
        )
        .fillna(default)
    )


def _bool_series(
    df: pd.DataFrame,
    column: str,
) -> pd.Series:

    if column not in df.columns:
        return pd.Series(
            False,
            index=df.index,
            dtype=bool,
        )

    return (
        df[column]
        .fillna(False)
        .astype(bool)
    )


def evaluate_row(row: pd.Series):
    up = 0.0
    down = 0.0
    confirmations = 0
    reasons = []

    ema_fast = float(row.get("ema_fast", 0) or 0)
    ema_slow = float(row.get("ema_slow", 0) or 0)

    if ema_fast > ema_slow:
        up += 15
        confirmations += 1
        reasons.append("EMA")

    elif ema_fast < ema_slow:
        down += 15
        confirmations += 1
        reasons.append("EMA")

    close = float(row.get("close", 0) or 0)
    ema_trend = float(row.get("ema_trend", 0) or 0)

    if close > ema_trend:
        up += 15
        confirmations += 1
        reasons.append("TREND")

    elif close < ema_trend:
        down += 15
        confirmations += 1
        reasons.append("TREND")

    rsi = float(row.get("rsi", 50) or 50)

    if rsi >= 55:
        up += 10
        confirmations += 1
        reasons.append("RSI")

    elif rsi <= 45:
        down += 10
        confirmations += 1
        reasons.append("RSI")

    macd = float(row.get("macd", 0) or 0)
    macd_signal = float(
        row.get("macd_signal", 0) or 0
    )

    if macd > macd_signal:
        up += 15
        confirmations += 1
        reasons.append("MACD")

    elif macd < macd_signal:
        down += 15
        confirmations += 1
        reasons.append("MACD")

    bb = float(
        row.get(
            "bollinger_middle",
            row.get("bb_middle", 0),
        )
        or 0
    )

    if bb and close > bb:
        up += 10
        confirmations += 1
        reasons.append("BB")

    elif bb and close < bb:
        down += 10
        confirmations += 1
        reasons.append("BB")

    k = float(
        row.get("stochastic_k", 50) or 50
    )

    d = float(
        row.get("stochastic_d", 50) or 50
    )

    if k > d:
        up += 10
        confirmations += 1
        reasons.append("STOCHASTIC")

    elif k < d:
        down += 10
        confirmations += 1
        reasons.append("STOCHASTIC")

    bullish = bool(
        row.get("bullish", False)
    )

    bearish = bool(
        row.get("bearish", False)
    )

    if bullish:
        up += 15
        confirmations += 1
        reasons.append("PRICE_ACTION")

    elif bearish:
        down += 15
        confirmations += 1
        reasons.append("PRICE_ACTION")

    if up == down:
        return None, confirmations, 0.0, reasons

    if up > down:
        direction = "UP"
        score = up
    else:
        direction = "DOWN"
        score = down

    confidence = min(
        100.0,
        50.0 + score * 0.5,
    )

    if confirmations < MIN_SIGNAL_CONFIRMATIONS:
        return None, confirmations, confidence, reasons

    return (
        direction,
        confirmations,
        confidence,
        reasons,
    )


def _prepare(df: pd.DataFrame) -> pd.DataFrame:

    data = df.copy()

    if "datetime" in data.columns:
        data["datetime"] = pd.to_datetime(
            data["datetime"],
            utc=True,
            errors="coerce",
        )

        data = data.sort_values(
            "datetime"
        )

    data = data.reset_index(drop=True)

    required = {
        "ema_fast",
        "ema_slow",
        "ema_trend",
        "rsi",
        "macd",
        "macd_signal",
        "bollinger_middle",
        "stochastic_k",
        "stochastic_d",
        "bullish",
        "bearish",
    }

    if not required.issubset(
        set(data.columns)
    ):
        data = calculate_indicators(data)

    return data


def run_backtest(
    df: pd.DataFrame,
    expiry_minutes: int,
    direction: Optional[str] = None,
) -> BacktestResult:

    try:
        expiry = int(expiry_minutes)
    except (
        TypeError,
        ValueError,
    ):
        return BacktestResult()

    if expiry < 1:
        return BacktestResult()

    if df is None or df.empty:
        return BacktestResult()

    data = _prepare(df)

    if len(data) < 60 + expiry:
        return BacktestResult()

    close = _series(
        data,
        "close",
    )

    ema_fast = _series(
        data,
        "ema_fast",
    )

    ema_slow = _series(
        data,
        "ema_slow",
    )

    ema_trend = _series(
        data,
        "ema_trend",
    )

    rsi = _series(
        data,
        "rsi",
        50,
    )

    macd = _series(
        data,
        "macd",
    )

    macd_signal = _series(
        data,
        "macd_signal",
    )

    bb = _series(
        data,
        "bollinger_middle",
    )

    k = _series(
        data,
        "stochastic_k",
        50,
    )

    d = _series(
        data,
        "stochastic_d",
        50,
    )

    bullish = _bool_series(
        data,
        "bullish",
    )

    bearish = _bool_series(
        data,
        "bearish",
    )

    up_ema = ema_fast > ema_slow
    down_ema = ema_fast < ema_slow

    up_trend = close > ema_trend
    down_trend = close < ema_trend

    up_rsi = rsi >= 55
    down_rsi = rsi <= 45

    up_macd = macd > macd_signal
    down_macd = macd < macd_signal

    up_bb = close > bb
    down_bb = close < bb

    up_stoch = k > d
    down_stoch = k < d

    up_action = bullish
    down_action = bearish

    up_score = (
        up_ema.astype(float) * 15
        + up_trend.astype(float) * 15
        + up_rsi.astype(float) * 10
        + up_macd.astype(float) * 15
        + up_bb.astype(float) * 10
        + up_stoch.astype(float) * 10
        + up_action.astype(float) * 15
    )

    down_score = (
        down_ema.astype(float) * 15
        + down_trend.astype(float) * 15
        + down_rsi.astype(float) * 10
        + down_macd.astype(float) * 15
        + down_bb.astype(float) * 10
        + down_stoch.astype(float) * 10
        + down_action.astype(float) * 15
    )

    confirmations = (
        up_ema.astype(int)
        + down_ema.astype(int)
        + up_trend.astype(int)
        + down_trend.astype(int)
        + up_rsi.astype(int)
        + down_rsi.astype(int)
        + up_macd.astype(int)
        + down_macd.astype(int)
        + up_bb.astype(int)
        + down_bb.astype(int)
        + up_stoch.astype(int)
        + down_stoch.astype(int)
        + up_action.astype(int)
        + down_action.astype(int)
    )

    prediction = pd.Series(
        None,
        index=data.index,
        dtype=object,
    )

    prediction.loc[
        up_score > down_score
    ] = "UP"

    prediction.loc[
        down_score > up_score
    ] = "DOWN"

    score = pd.concat(
        [
            up_score,
            down_score,
        ],
        axis=1,
    ).max(axis=1)

    confidence = (
        50.0 + score * 0.5
    ).clip(
        upper=100.0
    )

    mask = (
        prediction.notna()
        & (
            confirmations
            >= MIN_SIGNAL_CONFIRMATIONS
        )
        & (
            confidence >= 75.0
        )
    )

    if direction:

        normalized = str(
            direction
        ).upper().strip()

        if normalized not in {
            "UP",
            "DOWN",
        }:
            return BacktestResult()

        mask &= (
            prediction == normalized
        )

    start = 60
    end = len(data) - expiry

    valid_range = pd.Series(
        False,
        index=data.index,
    )

    valid_range.iloc[
        start:end
    ] = True

    mask &= valid_range

    future = close.shift(
        -expiry
    )

    mask &= future.notna()

    if not bool(mask.any()):
        return BacktestResult()

    current = close.loc[mask]
    future_values = future.loc[mask]
    predicted = prediction.loc[mask]

    up_mask = predicted == "UP"
    down_mask = predicted == "DOWN"

    wins = int(
        (
            (up_mask & (future_values > current))
            | (
                down_mask
                & (future_values < current)
            )
        ).sum()
    )

    losses = int(
        (
            (up_mask & (future_values < current))
            | (
                down_mask
                & (future_values > current)
            )
        ).sum()
    )

    draws = int(
        (
            future_values == current
        ).sum()
    )

    return BacktestResult(
        total=wins + losses + draws,
        wins=wins,
        losses=losses,
        draws=draws,
    )
