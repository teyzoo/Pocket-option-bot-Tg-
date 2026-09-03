from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
    ema_fast: float
    ema_slow: float
    ema_trend: float

    rsi: float

    macd: float
    macd_signal: float
    macd_histogram: float

    bb_upper: float
    bb_middle: float
    bb_lower: float

    stochastic_k: float
    stochastic_d: float

    atr: float

    price: float


@dataclass(slots=True)
class SignalCandidate:
    pair: str
    direction: str

    expiry_minutes: int

    confidence: float
    quality: float
    winrate: float

    entry_price: float

    created_at: datetime
    expires_at: datetime

    source: str = "manual"

    reasons: list[str] = field(default_factory=list)
    confirmations: list[str] = field(default_factory=list)

    indicators: IndicatorSnapshot | None = None

    market: str = "regular"

    chart_path: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PairInfo:
    symbol: str
    market: str
    enabled: bool = True
    display_name: str | None = None

    @property
    def name(self) -> str:
        return self.display_name or self.symbol
