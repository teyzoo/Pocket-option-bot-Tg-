from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd

from config import (
    MIN_SIGNAL_CONFIRMATIONS,
)
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

        return (
            self.wins
            / decisive
            * 100.0
        )

    @property
    def reliable(self) -> bool:
        return self.decisive_trades >= 10


def _safe_float(
    value,
    default: float = 0.0,
) -> float:
    try:
        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _evaluate_row(
    row: pd.Series,
) -> Tuple[
    Optional[str],
    int,
    float,
    List[str],
]:
    """
    Оценка одной свечи.

    Возвращает:
        direction,
        confirmations,
        confidence,
        reasons
    """

    up_score = 0.0
    down_score = 0.0

    confirmations = 0

    reasons_up: List[str] = []
    reasons_down: List[str] = []

    ema_fast = _safe_float(
        row.get("ema_fast")
    )
    ema_slow = _safe_float(
        row.get("ema_slow")
    )

    if ema_fast > ema_slow:
        up_score += 15
        confirmations += 1
        reasons_up.append("EMA")

    elif ema_fast < ema_slow:
        down_score += 15
        confirmations += 1
        reasons_down.append("EMA")

    ema_trend = _safe_float(
        row.get("ema_trend")
    )

    price = _safe_float(
        row.get("close", row.get("price"))
    )

    if price > ema_trend:
        up_score += 15
        confirmations += 1
        reasons_up.append("TREND")

    elif price < ema_trend:
        down_score += 15
        confirmations += 1
        reasons_down.append("TREND")

    rsi = _safe_float(
        row.get("rsi"),
        50.0,
    )

    if rsi >= 55:
        up_score += 10
        confirmations += 1
        reasons_up.append("RSI")

    elif rsi <= 45:
        down_score += 10
        confirmations += 1
        reasons_down.append("RSI")

    macd = _safe_float(
        row.get("macd")
    )

    macd_signal = _safe_float(
        row.get("macd_signal")
    )

    if macd > macd_signal:
        up_score += 15
        confirmations += 1
        reasons_up.append("MACD")

    elif macd < macd_signal:
        down_score += 15
        confirmations += 1
        reasons_down.append("MACD")

    bb_upper = _safe_float(
        row.get("bollinger_upper")
    )

    bb_lower = _safe_float(
        row.get("bollinger_lower")
    )

    bb_middle = _safe_float(
        row.get(
            "bollinger_middle",
            row.get("bb_middle"),
        )
    )

    if (
        bb_middle != 0.0
        and price > bb_middle
    ):
        up_score += 10
        confirmations += 1
        reasons_up.append("BB")

    elif (
        bb_middle != 0.0
        and price < bb_middle
    ):
        down_score += 10
        confirmations += 1
        reasons_down.append("BB")

    stochastic_k = _safe_float(
        row.get("stochastic_k"),
        50.0,
    )

    stochastic_d = _safe_float(
        row.get("stochastic_d"),
        50.0,
    )

    if stochastic_k > stochastic_d:
        up_score += 10
        confirmations += 1
        reasons_up.append("STOCHASTIC")

    elif stochastic_k < stochastic_d:
        down_score += 10
        confirmations += 1
        reasons_down.append("STOCHASTIC")

    bullish = bool(
        row.get("bullish", False)
    )

    bearish = bool(
        row.get("bearish", False)
    )

    if bullish:
        up_score += 15
        confirmations += 1
        reasons_up.append("PRICE_ACTION")

    elif bearish:
        down_score += 15
        confirmations += 1
        reasons_down.append("PRICE_ACTION")

    if up_score == down_score:
        return (
            None,
            confirmations,
            0.0,
            [],
        )

    if up_score > down_score:
        direction = "UP"
        score = up_score
        reasons = reasons_up

    else:
        direction = "DOWN"
        score = down_score
        reasons = reasons_down

    confidence = min(
        100.0,
        50.0 + score * 0.5,
    )

    if confirmations < MIN_SIGNAL_CONFIRMATIONS:
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
) -> Tuple[
    Optional[str],
    int,
    float,
    List[str],
]:
    """
    Публичная совместимая обёртка.
    """

    return _evaluate_row(row)


def _series_bool(
    dataframe: pd.DataFrame,
    column: str,
) -> pd.Series:

    if column not in dataframe.columns:
        return pd.Series(
            False,
            index=dataframe.index,
            dtype=bool,
        )

    return (
        dataframe[column]
        .fillna(False)
        .astype(bool)
    )


def _series_float(
    dataframe: pd.DataFrame,
    column: str,
    default: float = 0.0,
) -> pd.Series:

    if column not in dataframe.columns:
        return pd.Series(
            default,
            index=dataframe.index,
            dtype=float,
        )

    return pd.to_numeric(
        dataframe[column],
        errors="coerce",
    ).fillna(default)


def _vectorized_predictions(
    dataframe: pd.DataFrame,
):
    """
    Быстро рассчитывает направление/подтверждения
    для всех исторических свечей.

    Это намного быстрее, чем запускать _evaluate_row
    тысячи раз через Python-цикл.
    """

    ema_fast = _series_float(
        dataframe,
        "ema_fast",
    )

    ema_slow = _series_float(
        dataframe,
        "ema_slow",
    )

    ema_trend = _series_float(
        dataframe,
        "ema_trend",
    )

    close = _series_float(
        dataframe,
        "close",
    )

    rsi = _series_float(
        dataframe,
        "rsi",
        50.0,
    )

    macd = _series_float(
        dataframe,
        "macd",
    )

    macd_signal = _series_float(
        dataframe,
        "macd_signal",
    )

    bb_middle = _series_float(
        dataframe,
        "bollinger_middle",
    )

    if (
        "bollinger_middle"
        not in dataframe.columns
        and "bb_middle"
        in dataframe.columns
    ):
        bb_middle = _series_float(
            dataframe,
            "bb_middle",
        )

    stochastic_k = _series_float(
        dataframe,
        "stochastic_k",
        50.0,
    )

    stochastic_d = _series_float(
        dataframe,
        "stochastic_d",
        50.0,
    )

    bullish = _series_bool(
        dataframe,
        "bullish",
    )

    bearish = _series_bool(
        dataframe,
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

    up_bb = close > bb_middle
    down_bb = close < bb_middle

    up_stoch = stochastic_k > stochastic_d
    down_stoch = stochastic_k < stochastic_d

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

    up_confirmations = (
        up_ema.astype(int)
        + up_trend.astype(int)
        + up_rsi.astype(int)
        + up_macd.astype(int)
        + up_bb.astype(int)
        + up_stoch.astype(int)
        + up_action.astype(int)
    )

    down_confirmations = (
        down_ema.astype(int)
        + down_trend.astype(int)
        + down_rsi.astype(int)
        + down_macd.astype(int)
        + down_bb.astype(int)
        + down_stoch.astype(int)
        + down_action.astype(int)
    )

    # В исходной логике confirmations — это общее
    # количество активных подтверждений.
    confirmations = (
        up_confirmations
        + down_confirmations
    )

    direction = pd.Series(
        None,
        index=dataframe.index,
        dtype=object,
    )

    direction.loc[
        up_score > down_score
    ] = "UP"

    direction.loc[
        down_score > up_score
    ] = "DOWN"

    selected_score = pd.Series(
        np.maximum(
            up_score.to_numpy(),
            down_score.to_numpy(),
        ),
        index=dataframe.index,
    )

    confidence = (
        50.0
        + selected_score * 0.5
    ).clip(
        upper=100.0
    )

    eligible = (
        direction.notna()
        & (
            confirmations
            >= MIN_SIGNAL_CONFIRMATIONS
        )
        & (confidence >= 75.0)
    )

    return (
        direction,
        confirmations,
        confidence,
        eligible,
    )


def run_backtest(
    df: pd.DataFrame,
    expiry_minutes: int,
    direction: Optional[str] = None,
) -> BacktestResult:
    """
    Backtest для конкретной экспирации.

    Важное ускорение:
    если индикаторы уже рассчитаны, они НЕ рассчитываются
    повторно.

    Результаты считаются векторно через pandas/numpy.
    """

    try:
        expiry = int(expiry_minutes)
    except (TypeError, ValueError):
        return BacktestResult()

    if expiry < 1:
        return BacktestResult()

    if df is None or df.empty:
        return BacktestResult()

    data = df.copy()

    if len(data) < 60 + expiry:
        return BacktestResult()

    required_columns = {
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

    if not required_columns.issubset(
        set(data.columns)
    ):
        data = calculate_indicators(data)

    data = (
        data
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    if len(data) < 60 + expiry:
        return BacktestResult()

    (
        predictions,
        confirmations,
        confidence,
        eligible,
    ) = _vectorized_predictions(data)

    start_index = 60

    end_index = (
        len(data) - expiry
    )

    if end_index <= start_index:
        return BacktestResult()

    mask = pd.Series(
        False,
        index=data.index,
    )

    mask.iloc[
        start_index:end_index
    ] = True

    mask &= eligible

    if direction:
        normalized_direction = (
            str(direction)
            .strip()
            .upper()
        )

        if normalized_direction not in {
            "UP",
            "DOWN",
        }:
            return BacktestResult()

        mask &= (
            predictions
            == normalized_direction
        )

    current_close = _series_float(
        data,
        "close",
    )

    future_close = (
        current_close
        .shift(-expiry)
    )

    valid = (
        mask
        & future_close.notna()
    )

    if not bool(valid.any()):
        return BacktestResult()

    predicted = predictions.loc[valid]

    current = current_close.loc[valid]

    future = future_close.loc[valid]

    up_predictions = (
        predicted == "UP"
    )

    down_predictions = (
        predicted == "DOWN"
    )

    up_wins = (
        up_predictions
        & (future > current)
    )

    up_losses = (
        up_predictions
        & (future < current)
    )

    down_wins = (
        down_predictions
        & (future < current)
    )

    down_losses = (
        down_predictions
        & (future > current)
    )

    draws = (
        future == current
    )

    wins = int(
        (up_wins | down_wins).sum()
    )

    losses = int(
        (up_losses | down_losses).sum()
    )

    draw_count = int(
        draws.sum()
    )

    total = (
        wins
        + losses
        + draw_count
    )

    return BacktestResult(
        total=total,
        wins=wins,
        losses=losses,
        draws=draw_count,
    )
