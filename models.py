from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Candle:
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(slots=True)
class IndicatorSnapshot:
    close: float

    ema_fast: float
    ema_slow: float
    ema_trend: float

    rsi: float

    macd: float
    macd_signal: float
    macd_histogram: float

    bb_middle: float
    bb_upper: float
    bb_lower: float

    stochastic_k: float
    stochastic_d: float

    atr: float


@dataclass(slots=True)
class SignalCandidate:
    pair: str
    direction: str
    expiry_minutes: int

    confidence: float
    quality: float

    entry_price: float

    reasons: list[str]

    created_at: datetime
    expires_at: datetime

    source: str = "manual"


@dataclass(slots=True)
class PairInfo:
    symbol: str
    display_name: str
    market_type: str = "regular"
