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
    ema_fast: float | None = None
    ema_slow: float | None = None
    ema_trend: float | None = None

    rsi: float | None = None

    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None

    bollinger_middle: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None

    stochastic_k: float | None = None
    stochastic_d: float | None = None

    atr: float | None = None

    candle_body: float | None = None
    upper_wick: float | None = None
    lower_wick: float | None = None

    bullish: bool = False
    bearish: bool = False


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
    market: str = "regular"

    reasons: list[str] = field(default_factory=list)
    confirmations: int = 0

    indicators: dict[str, Any] = field(
        default_factory=dict
    )

    chart_path: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    winrate_trades: int = 0
    winrate_wins: int = 0
    winrate_losses: int = 0
    winrate_draws: int = 0


@dataclass(slots=True)
class PairInfo:
    symbol: str
    market: str
    enabled: bool = True


@dataclass(slots=True)
class BacktestResult:
    total: int
    wins: int
    losses: int
    draws: int

    @property
    def decisive_trades(self) -> int:
        return max(
            0,
            int(self.wins) + int(self.losses),
        )

    @property
    def winrate(self) -> float:
        decisive = self.decisive_trades

        if decisive <= 0:
            return 0.0

        return (
            float(self.wins)
            / float(decisive)
            * 100.0
        )

    @property
    def reliable(self) -> bool:
        # Минимальная выборка для исторической оценки.
        # Сам порог WINRATE проверяется отдельно.
        return self.decisive_trades >= 10
