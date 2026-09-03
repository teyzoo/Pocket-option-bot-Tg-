from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    ATR_PERIOD,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    EMA_FAST,
    EMA_SLOW,
    EMA_TREND,
    MACD_FAST,
    MACD_SIGNAL,
    MACD_SLOW,
    RSI_PERIOD,
    STOCHASTIC_PERIOD,
    STOCHASTIC_SMOOTH,
)


def calculate_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    result = df.copy()

    required = {
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing = required - set(result.columns)

    if missing:
        raise ValueError(
            f"Missing candle columns: {sorted(missing)}"
        )

    result["datetime"] = pd.to_datetime(
        result["datetime"],
        utc=True,
        errors="coerce",
    )

    for column in (
        "open",
        "high",
        "low",
        "close",
        "volume",
    ):
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    result = result.dropna(
        subset=[
            "datetime",
            "open",
            "high",
            "low",
            "close",
        ]
    ).copy()

    result = result.sort_values(
        "datetime"
    ).reset_index(drop=True)

    close = result["close"]
    high = result["high"]
    low = result["low"]

    result["ema_fast"] = close.ewm(
        span=EMA_FAST,
        adjust=False,
        min_periods=EMA_FAST,
    ).mean()

    result["ema_slow"] = close.ewm(
        span=EMA_SLOW,
        adjust=False,
        min_periods=EMA_SLOW,
    ).mean()

    result["ema_trend"] = close.ewm(
        span=EMA_TREND,
        adjust=False,
        min_periods=EMA_TREND,
    ).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
        min_periods=RSI_PERIOD,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
        min_periods=RSI_PERIOD,
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan,
    )

    result["rsi"] = 100 - (
        100 / (1 + rs)
    )

    result["rsi"] = result["rsi"].fillna(
        np.where(
            avg_loss == 0,
            100,
            50,
        )
    )

    ema_macd_fast = close.ewm(
        span=MACD_FAST,
        adjust=False,
        min_periods=MACD_FAST,
    ).mean()

    ema_macd_slow = close.ewm(
        span=MACD_SLOW,
        adjust=False,
        min_periods=MACD_SLOW,
    ).mean()

    result["macd"] = (
        ema_macd_fast
        - ema_macd_slow
    )

    result["macd_signal"] = result[
        "macd"
    ].ewm(
        span=MACD_SIGNAL,
        adjust=False,
        min_periods=MACD_SIGNAL,
    ).mean()

    result["macd_histogram"] = (
        result["macd"]
        - result["macd_signal"]
    )

    result["bollinger_middle"] = close.rolling(
        BOLLINGER_PERIOD,
        min_periods=BOLLINGER_PERIOD,
    ).mean()

    std = close.rolling(
        BOLLINGER_PERIOD,
        min_periods=BOLLINGER_PERIOD,
    ).std()

    result["bollinger_upper"] = (
        result["bollinger_middle"]
        + std * BOLLINGER_STD
    )

    result["bollinger_lower"] = (
        result["bollinger_middle"]
        - std * BOLLINGER_STD
    )

    lowest_low = low.rolling(
        STOCHASTIC_PERIOD,
        min_periods=STOCHASTIC_PERIOD,
    ).min()

    highest_high = high.rolling(
        STOCHASTIC_PERIOD,
        min_periods=STOCHASTIC_PERIOD,
    ).max()

    denominator = (
        highest_high - lowest_low
    ).replace(
        0,
        np.nan,
    )

    result["stochastic_k"] = (
        (
            close - lowest_low
        )
        / denominator
        * 100
    )

    result["stochastic_d"] = (
        result["stochastic_k"]
        .rolling(
            STOCHASTIC_SMOOTH,
            min_periods=STOCHASTIC_SMOOTH,
        )
        .mean()
    )

    previous_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1,
    ).max(axis=1)

    result["atr"] = true_range.ewm(
        alpha=1 / ATR_PERIOD,
        adjust=False,
        min_periods=ATR_PERIOD,
    ).mean()

    result["candle_body"] = (
        result["close"]
        - result["open"]
    ).abs()

    result["upper_wick"] = (
        result["high"]
        - result[
            ["open", "close"]
        ].max(axis=1)
    )

    result["lower_wick"] = (
        result[
            ["open", "close"]
        ].min(axis=1)
        - result["low"]
    )

    result["bullish"] = (
        result["close"]
        > result["open"]
    )

    result["bearish"] = (
        result["close"]
        < result["open"]
    )

    return result


def latest_indicators(
    df: pd.DataFrame,
) -> dict[str, float | bool | None]:
    if df.empty:
        return {}

    row = df.iloc[-1]

    values: dict[
        str,
        float | bool | None,
    ] = {}

    columns = (
        "ema_fast",
        "ema_slow",
        "ema_trend",
        "rsi",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bollinger_middle",
        "bollinger_upper",
        "bollinger_lower",
        "stochastic_k",
        "stochastic_d",
        "atr",
        "candle_body",
        "upper_wick",
        "lower_wick",
        "bullish",
        "bearish",
    )

    for column in columns:
        value = row.get(column)

        if isinstance(value, (
            bool,
            np.bool_,
        )):
            values[column] = bool(value)
            continue

        if pd.isna(value):
            values[column] = None
            continue

        try:
            values[column] = float(value)
        except (TypeError, ValueError):
            values[column] = None

    return values
