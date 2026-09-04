from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class StrategySignal:
    name: str
    direction: Optional[str]
    score: float
    confidence: float
    reason: str


@dataclass
class StrategyAnalysis:
    direction: Optional[str]
    score_up: float
    score_down: float
    confidence: float
    confirmations: int
    strategies: List[StrategySignal] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


def _num(row: pd.Series, name: str, default: float = 0.0) -> float:
    try:
        value = row.get(name, default)
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(row: pd.Series, name: str) -> bool:
    try:
        value = row.get(name, False)
        if pd.isna(value):
            return False
        return bool(value)
    except Exception:
        return False


def _signal(
    name: str,
    direction: Optional[str],
    score: float,
    reason: str,
) -> StrategySignal:
    confidence = min(100.0, max(0.0, 50.0 + score * 2.0))

    return StrategySignal(
        name=name,
        direction=direction,
        score=float(score),
        confidence=float(confidence),
        reason=reason,
    )


def strategy_ema(row: pd.Series) -> StrategySignal:
    fast = _num(row, "ema_fast")
    slow = _num(row, "ema_slow")
    trend = _num(row, "ema_trend")
    close = _num(row, "close")

    if fast > slow and close > trend:
        return _signal(
            "EMA TREND",
            "UP",
            10,
            "EMA fast выше EMA slow и цена выше трендовой EMA",
        )

    if fast < slow and close < trend:
        return _signal(
            "EMA TREND",
            "DOWN",
            10,
            "EMA fast ниже EMA slow и цена ниже трендовой EMA",
        )

    if fast > slow:
        return _signal(
            "EMA TREND",
            "UP",
            5,
            "EMA fast выше EMA slow",
        )

    if fast < slow:
        return _signal(
            "EMA TREND",
            "DOWN",
            5,
            "EMA fast ниже EMA slow",
        )

    return _signal(
        "EMA TREND",
        None,
        0,
        "EMA не даёт направления",
    )


def strategy_rsi(row: pd.Series) -> StrategySignal:
    rsi = _num(row, "rsi", 50.0)

    if rsi >= 60:
        return _signal(
            "RSI",
            "UP",
            8,
            f"RSI {rsi:.1f} подтверждает бычий импульс",
        )

    if rsi <= 40:
        return _signal(
            "RSI",
            "DOWN",
            8,
            f"RSI {rsi:.1f} подтверждает медвежий импульс",
        )

    if rsi >= 55:
        return _signal(
            "RSI",
            "UP",
            4,
            f"RSI {rsi:.1f} выше нейтральной зоны",
        )

    if rsi <= 45:
        return _signal(
            "RSI",
            "DOWN",
            4,
            f"RSI {rsi:.1f} ниже нейтральной зоны",
        )

    return _signal(
        "RSI",
        None,
        0,
        f"RSI {rsi:.1f} нейтрален",
    )


def strategy_macd(row: pd.Series) -> StrategySignal:
    macd = _num(row, "macd")
    signal = _num(row, "macd_signal")
    histogram = _num(row, "macd_histogram")

    if macd > signal and histogram > 0:
        return _signal(
            "MACD",
            "UP",
            9,
            "MACD выше signal, histogram положительная",
        )

    if macd < signal and histogram < 0:
        return _signal(
            "MACD",
            "DOWN",
            9,
            "MACD ниже signal, histogram отрицательная",
        )

    if macd > signal:
        return _signal(
            "MACD",
            "UP",
            5,
            "MACD выше signal",
        )

    if macd < signal:
        return _signal(
            "MACD",
            "DOWN",
            5,
            "MACD ниже signal",
        )

    return _signal(
        "MACD",
        None,
        0,
        "MACD нейтрален",
    )


def strategy_bollinger(row: pd.Series) -> StrategySignal:
    close = _num(row, "close")
    middle = _num(row, "bollinger_middle")
    upper = _num(row, "bollinger_upper")
    lower = _num(row, "bollinger_lower")

    if middle == 0:
        return _signal(
            "BOLLINGER",
            None,
            0,
            "Недостаточно данных Bollinger",
        )

    if close > middle and close < upper:
        return _signal(
            "BOLLINGER",
            "UP",
            6,
            "Цена выше средней полосы Bollinger",
        )

    if close < middle and close > lower:
        return _signal(
            "BOLLINGER",
            "DOWN",
            6,
            "Цена ниже средней полосы Bollinger",
        )

    if close <= lower:
        return _signal(
            "BOLLINGER",
            "UP",
            5,
            "Цена у нижней полосы Bollinger",
        )

    if close >= upper:
        return _signal(
            "BOLLINGER",
            "DOWN",
            5,
            "Цена у верхней полосы Bollinger",
        )

    return _signal(
        "BOLLINGER",
        None,
        0,
        "Bollinger не даёт сильного направления",
    )


def strategy_stochastic(row: pd.Series) -> StrategySignal:
    k = _num(row, "stochastic_k", 50)
    d = _num(row, "stochastic_d", 50)

    if k > d and k < 80:
        return _signal(
            "STOCHASTIC",
            "UP",
            7,
            "Stochastic K выше D",
        )

    if k < d and k > 20:
        return _signal(
            "STOCHASTIC",
            "DOWN",
            7,
            "Stochastic K ниже D",
        )

    if k <= 20 and k > d:
        return _signal(
            "STOCHASTIC",
            "UP",
            8,
            "Выход из зоны перепроданности",
        )

    if k >= 80 and k < d:
        return _signal(
            "STOCHASTIC",
            "DOWN",
            8,
            "Выход из зоны перекупленности",
        )

    return _signal(
        "STOCHASTIC",
        None,
        0,
        "Stochastic нейтрален",
    )


def strategy_price_action(row: pd.Series) -> StrategySignal:
    bullish = _bool(row, "bullish")
    bearish = _bool(row, "bearish")

    body = abs(_num(row, "candle_body"))
    upper_wick = abs(_num(row, "upper_wick"))
    lower_wick = abs(_num(row, "lower_wick"))

    if bullish:
        if body > upper_wick and body > lower_wick:
            return _signal(
                "PRICE ACTION",
                "UP",
                9,
                "Сильная бычья свеча",
            )

        return _signal(
            "PRICE ACTION",
            "UP",
            6,
            "Бычья свеча",
        )

    if bearish:
        if body > upper_wick and body > lower_wick:
            return _signal(
                "PRICE ACTION",
                "DOWN",
                9,
                "Сильная медвежья свеча",
            )

        return _signal(
            "PRICE ACTION",
            "DOWN",
            6,
            "Медвежья свеча",
        )

    return _signal(
        "PRICE ACTION",
        None,
        0,
        "Price Action нейтрален",
    )


def strategy_support_resistance(
    dataframe: pd.DataFrame,
) -> StrategySignal:
    if dataframe is None or len(dataframe) < 20:
        return _signal(
            "SUPPORT/RESISTANCE",
            None,
            0,
            "Недостаточно свечей",
        )

    recent = dataframe.tail(20)

    close = float(recent.iloc[-1]["close"])

    high = float(recent["high"].max())
    low = float(recent["low"].min())

    distance_high = abs(high - close)
    distance_low = abs(close - low)

    range_size = max(high - low, 1e-12)

    near_low = distance_low / range_size < 0.20
    near_high = distance_high / range_size < 0.20

    if near_low and not near_high:
        return _signal(
            "SUPPORT/RESISTANCE",
            "UP",
            6,
            "Цена находится близко к локальной поддержке",
        )

    if near_high and not near_low:
        return _signal(
            "SUPPORT/RESISTANCE",
            "DOWN",
            6,
            "Цена находится близко к локальному сопротивлению",
        )

    if close > (low + high) / 2:
        return _signal(
            "SUPPORT/RESISTANCE",
            "UP",
            3,
            "Цена выше середины локального диапазона",
        )

    if close < (low + high) / 2:
        return _signal(
            "SUPPORT/RESISTANCE",
            "DOWN",
            3,
            "Цена ниже середины локального диапазона",
        )

    return _signal(
        "SUPPORT/RESISTANCE",
        None,
        0,
        "Уровни нейтральны",
    )


class StrategyEngine:
    """
    Объединяет стратегии.

    Максимальный вес:
    EMA              10
    RSI               8
    MACD              9
    Bollinger         6
    Stochastic        8
    Price Action      9
    S/R               6

    Вместо требования полного совпадения
    всех индикаторов используется консенсус.
    """

    def analyze(
        self,
        dataframe: pd.DataFrame,
    ) -> StrategyAnalysis:

        if dataframe is None or dataframe.empty:
            return StrategyAnalysis(
                direction=None,
                score_up=0,
                score_down=0,
                confidence=0,
                confirmations=0,
            )

        row = dataframe.iloc[-1]

        strategies = [
            strategy_ema(row),
            strategy_rsi(row),
            strategy_macd(row),
            strategy_bollinger(row),
            strategy_stochastic(row),
            strategy_price_action(row),
            strategy_support_resistance(dataframe),
        ]

        score_up = 0.0
        score_down = 0.0

        up_count = 0
        down_count = 0

        reasons: List[str] = []

        for strategy in strategies:

            if strategy.direction == "UP":
                score_up += strategy.score
                up_count += 1
                reasons.append(
                    f"{strategy.name}: UP — {strategy.reason}"
                )

            elif strategy.direction == "DOWN":
                score_down += strategy.score
                down_count += 1
                reasons.append(
                    f"{strategy.name}: DOWN — {strategy.reason}"
                )

        if score_up > score_down:
            direction = "UP"
            winning_score = score_up
            confirmations = up_count

        elif score_down > score_up:
            direction = "DOWN"
            winning_score = score_down
            confirmations = down_count

        else:
            direction = None
            winning_score = 0.0
            confirmations = 0

        total_score = score_up + score_down

        if total_score <= 0:
            confidence = 0.0

        else:
            dominance = (
                winning_score / total_score
            )

            confidence = min(
                100.0,
                50.0 + dominance * 50.0,
            )

        return StrategyAnalysis(
            direction=direction,
            score_up=round(score_up, 2),
            score_down=round(score_down, 2),
            confidence=round(confidence, 2),
            confirmations=confirmations,
            strategies=strategies,
            reasons=reasons,
        )
