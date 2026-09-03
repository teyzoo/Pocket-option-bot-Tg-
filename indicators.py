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
    STOCHASTIC_PERIOD,
    STOCHASTIC_SMOOTHING,
)
from models import IndicatorSnapshot


REQUIRED_COLUMNS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


def _validate_dataframe(
    df: pd.DataFrame,
) -> None:
    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing candle columns: "
            + ", ".join(missing)
        )

    if len(df) < 2:
        raise ValueError(
            "At least two candles are required"
        )


def calculate_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    _validate_dataframe(df)

    result = df.copy()

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
            "open",
            "high",
            "low",
            "close",
        ]
    )

    result["ema_fast"] = (
        result["close"]
        .ewm(
            span=EMA_FAST_PERIOD,
            adjust=False,
            min_periods=EMA_FAST_PERIOD,
        )
        .mean()
    )

    result["ema_slow"] = (
        result["close"]
        .ewm(
            span=EMA_SLOW_PERIOD,
            adjust=False,
            min_periods=EMA_SLOW_PERIOD,
        )
        .mean()
    )

    result["ema_trend"] = (
        result["close"]
        .ewm(
            span=EMA_TREND_PERIOD,
            adjust=False,
            min_periods=EMA_TREND_PERIOD,
        )
        .mean()
    )

    delta = result["close"].diff()

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

    result.loc[
        (avg_loss == 0) & (avg_gain > 0),
        "rsi",
    ] = 100

    result.loc[
        (avg_gain == 0) & (avg_loss > 0),
        "rsi",
    ] = 0

    result["rsi"] = result["rsi"].fillna(50)

    ema_macd_fast = (
        result["close"]
        .ewm(
            span=MACD_FAST_PERIOD,
            adjust=False,
        )
        .mean()
    )

    ema_macd_slow = (
        result["close"]
        .ewm(
            span=MACD_SLOW_PERIOD,
            adjust=False,
        )
        .mean()
    )

    result["macd"] = (
        ema_macd_fast - ema_macd_slow
    )

    result["macd_signal"] = (
        result["macd"]
        .ewm(
            span=MACD_SIGNAL_PERIOD,
            adjust=False,
        )
        .mean()
    )

    result["macd_histogram"] = (
        result["macd"]
        - result["macd_signal"]
    )

    result["bb_middle"] = (
        result["close"]
        .rolling(
            BOLLINGER_PERIOD,
            min_periods=BOLLINGER_PERIOD,
        )
        .mean()
    )

    bb_std = (
        result["close"]
        .rolling(
            BOLLINGER_PERIOD,
            min_periods=BOLLINGER_PERIOD,
        )
        .std()
    )

    result["bb_upper"] = (
        result["bb_middle"]
        + BOLLINGER_STD * bb_std
    )

    result["bb_lower"] = (
        result["bb_middle"]
        - BOLLINGER_STD * bb_std
    )

    lowest_low = (
        result["low"]
        .rolling(
            STOCHASTIC_PERIOD,
            min_periods=STOCHASTIC_PERIOD,
        )
        .min()
    )

    highest_high = (
        result["high"]
        .rolling(
            STOCHASTIC_PERIOD,
            min_periods=STOCHASTIC_PERIOD,
        )
        .max()
    )

    denominator = (
        highest_high - lowest_low
    ).replace(0, np.nan)

    result["stochastic_k"] = (
        100
        * (
            result["close"]
            - lowest_low
        )
        / denominator
    )

    result["stochastic_d"] = (
        result["stochastic_k"]
        .rolling(
            STOCHASTIC_SMOOTHING,
            min_periods=STOCHASTIC_SMOOTHING,
        )
        .mean()
    )

    prev_close = result["close"].shift(1)

    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - prev_close).abs(),
            (result["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["atr"] = (
        true_range
        .ewm(
            alpha=1 / ATR_PERIOD,
            adjust=False,
            min_periods=ATR_PERIOD,
        )
        .mean()
    )

    result["body"] = (
        result["close"] - result["open"]
    )

    result["body_size"] = (
        result["body"].abs()
    )

    result["upper_wick"] = (
        result["high"]
        - result[["open", "close"]].max(axis=1)
    )

    result["lower_wick"] = (
        result[["open", "close"]].min(axis=1)
        - result["low"]
    )

    result["bullish_candle"] = (
        result["close"] > result["open"]
    )

    result["bearish_candle"] = (
        result["close"] < result["open"]
    )

    return result


def latest_indicators(
    df: pd.DataFrame,
) -> IndicatorSnapshot:
    calculated = calculate_indicators(df)

    row = calculated.iloc[-1]

    def number(
        column: str,
        default: float = 0.0,
    ) -> float:
        value = row[column]

        if pd.isna(value):
            return default

        return float(value)

    return IndicatorSnapshot(
        ema_fast=number("ema_fast"),
        ema_slow=number("ema_slow"),
        ema_trend=number("ema_trend"),
        rsi=number("rsi", 50.0),
        macd=number("macd"),
        macd_signal=number("macd_signal"),
        macd_histogram=number("macd_histogram"),
        bb_upper=number("bb_upper"),
        bb_middle=number("bb_middle"),
        bb_lower=number("bb_lower"),
        stochastic_k=number(
            "stochastic_k",
            50.0,
        ),
        stochastic_d=number(
            "stochastic_d",
            50.0,
        ),
        atr=number("atr"),
        price=number("close"),
    )
