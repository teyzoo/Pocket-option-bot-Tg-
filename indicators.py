from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    ATR_PERIOD,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    EMA_FAST_PERIOD,
    EMA_SLOW_PERIOD,
    EMA_TREND_PERIOD,
    MACD_FAST_PERIOD,
    MACD_SIGNAL_PERIOD,
    MACD_SLOW_PERIOD,
    RSI_PERIOD,
    STOCHASTIC_D_PERIOD,
    STOCHASTIC_K_PERIOD,
)


def calculate_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    result = df.copy()

    close = result["close"]
    high = result["high"]
    low = result["low"]

    result["ema_fast"] = close.ewm(
        span=EMA_FAST_PERIOD,
        adjust=False,
    ).mean()

    result["ema_slow"] = close.ewm(
        span=EMA_SLOW_PERIOD,
        adjust=False,
    ).mean()

    result["ema_trend"] = close.ewm(
        span=EMA_TREND_PERIOD,
        adjust=False,
    ).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.ewm(
        alpha=1 / RSI_PERIOD,
        min_periods=RSI_PERIOD,
        adjust=False,
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / RSI_PERIOD,
        min_periods=RSI_PERIOD,
        adjust=False,
    ).mean()

    rs = average_gain / average_loss.replace(
        0,
        np.nan,
    )

    result["rsi"] = 100 - (
        100 / (1 + rs)
    )

    result["rsi"] = result["rsi"].fillna(50)

    ema_fast_macd = close.ewm(
        span=MACD_FAST_PERIOD,
        adjust=False,
    ).mean()

    ema_slow_macd = close.ewm(
        span=MACD_SLOW_PERIOD,
        adjust=False,
    ).mean()

    result["macd"] = (
        ema_fast_macd - ema_slow_macd
    )

    result["macd_signal"] = result[
        "macd"
    ].ewm(
        span=MACD_SIGNAL_PERIOD,
        adjust=False,
    ).mean()

    result["macd_histogram"] = (
        result["macd"]
        - result["macd_signal"]
    )

    result["bb_middle"] = close.rolling(
        BOLLINGER_PERIOD
    ).mean()

    std = close.rolling(
        BOLLINGER_PERIOD
    ).std()

    result["bb_upper"] = (
        result["bb_middle"]
        + std * BOLLINGER_STD
    )

    result["bb_lower"] = (
        result["bb_middle"]
        - std * BOLLINGER_STD
    )

    lowest_low = low.rolling(
        STOCHASTIC_K_PERIOD
    ).min()

    highest_high = high.rolling(
        STOCHASTIC_K_PERIOD
    ).max()

    denominator = (
        highest_high - lowest_low
    ).replace(0, np.nan)

    result["stochastic_k"] = (
        100
        * (close - lowest_low)
        / denominator
    )

    result["stochastic_d"] = (
        result["stochastic_k"]
        .rolling(STOCHASTIC_D_PERIOD)
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
    ).mean()

    result = result.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    return result


def latest_indicators(
    df: pd.DataFrame,
) -> dict[str, float]:
    data = calculate_indicators(df)

    if data.empty:
        raise ValueError(
            "Невозможно получить индикаторы: DataFrame пуст."
        )

    row = data.iloc[-1]

    required = [
        "close",
        "ema_fast",
        "ema_slow",
        "ema_trend",
        "rsi",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "stochastic_k",
        "stochastic_d",
        "atr",
    ]

    values: dict[str, float] = {}

    for key in required:
        value = row.get(key)

        if pd.isna(value):
            raise ValueError(
                f"Индикатор {key} ещё не рассчитан."
            )

        values[key] = float(value)

    return values
