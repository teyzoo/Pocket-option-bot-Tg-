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


def calculate_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Missing columns: "
            + ", ".join(sorted(missing))
        )

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

    if result.empty:
        raise ValueError(
            "No valid candles"
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

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    average_gain = gain.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
        min_periods=RSI_PERIOD,
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
        min_periods=RSI_PERIOD,
    ).mean()

    rs = average_gain / average_loss.replace(
        0,
        np.nan,
    )

    result["rsi"] = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    result.loc[
        (average_loss == 0)
        & (average_gain > 0),
        "rsi",
    ] = 100

    result.loc[
        (average_gain == 0)
        & (average_loss > 0),
        "rsi",
    ] = 0

    result["rsi"] = result[
        "rsi"
    ].fillna(50)

    macd_fast = (
        result["close"]
        .ewm(
            span=MACD_FAST_PERIOD,
            adjust=False,
        )
        .mean()
    )

    macd_slow = (
        result["close"]
        .ewm(
            span=MACD_SLOW_PERIOD,
            adjust=False,
        )
        .mean()
    )

    result["macd"] = (
        macd_fast - macd_slow
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

    std = (
        result["close"]
        .rolling(
            BOLLINGER_PERIOD,
            min_periods=BOLLINGER_PERIOD,
        )
        .std()
    )

    result["bb_upper"] = (
        result["bb_middle"]
        + BOLLINGER_STD * std
    )

    result["bb_lower"] = (
        result["bb_middle"]
        - BOLLINGER_STD * std
    )

    lowest = (
        result["low"]
        .rolling(
            STOCHASTIC_PERIOD,
            min_periods=STOCHASTIC_PERIOD,
        )
        .min()
    )

    highest = (
        result["high"]
        .rolling(
            STOCHASTIC_PERIOD,
            min_periods=STOCHASTIC_PERIOD,
        )
        .max()
    )

    denominator = (
        highest - lowest
    ).replace(
        0,
        np.nan,
    )

    result["stochastic_k"] = (
        100
        * (
            result["close"]
            - lowest
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

    previous_close = result[
        "close"
    ].shift(1)

    true_range = pd.concat(
        [
            result["high"]
            - result["low"],
            (
                result["high"]
                - previous_close
            ).abs(),
            (
                result["low"]
                - previous_close
            ).abs(),
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
        result["close"]
        - result["open"]
    )

    result["body_size"] = (
        result["body"].abs()
    )

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

    return result


def latest_indicators(
    df: pd.DataFrame,
) -> IndicatorSnapshot:
    calculated = calculate_indicators(df)

    row = calculated.iloc[-1]

    def number(
        name: str,
        fallback: float = 0.0,
    ) -> float:
        value = row[name]

        if pd.isna(value):
            return fallback

        return float(value)

    return IndicatorSnapshot(
        ema_fast=number("ema_fast"),
        ema_slow=number("ema_slow"),
        ema_trend=number("ema_trend"),
        rsi=number("rsi", 50),
        macd=number("macd"),
        macd_signal=number(
            "macd_signal"
        ),
        macd_histogram=number(
            "macd_histogram"
        ),
        bb_upper=number("bb_upper"),
        bb_middle=number("bb_middle"),
        bb_lower=number("bb_lower"),
        stochastic_k=number(
            "stochastic_k",
            50,
        ),
        stochastic_d=number(
            "stochastic_d",
            50,
        ),
        atr=number("atr"),
        price=number("close"),
    )
