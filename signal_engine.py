from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from config import (
    MIN_CANDLES_REQUIRED,
    MIN_SIGNAL_CONFIDENCE,
    MIN_SIGNAL_QUALITY,
    SIGNAL_DOWN,
    SIGNAL_UP,
)
from indicators import latest_indicators
from models import SignalCandidate


class SignalEngine:
    def analyze(
        self,
        pair: str,
        df: pd.DataFrame,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:
        if len(df) < MIN_CANDLES_REQUIRED:
            return None

        try:
            indicators = latest_indicators(df)
        except ValueError:
            return None

        close = indicators["close"]
        ema_fast = indicators["ema_fast"]
        ema_slow = indicators["ema_slow"]
        ema_trend = indicators["ema_trend"]

        rsi = indicators["rsi"]

        macd = indicators["macd"]
        macd_signal = indicators["macd_signal"]

        bb_upper = indicators["bb_upper"]
        bb_lower = indicators["bb_lower"]
        bb_middle = indicators["bb_middle"]

        stochastic_k = indicators["stochastic_k"]
        stochastic_d = indicators["stochastic_d"]

        bullish = 0.0
        bearish = 0.0

        bullish_reasons: list[str] = []
        bearish_reasons: list[str] = []

        # EMA trend
        if ema_fast > ema_slow:
            bullish += 15
            bullish_reasons.append(
                "EMA показывает восходящий тренд"
            )
        elif ema_fast < ema_slow:
            bearish += 15
            bearish_reasons.append(
                "EMA показывает нисходящий тренд"
            )

        # Long-term trend
        if close > ema_trend:
            bullish += 10
            bullish_reasons.append(
                "Цена выше EMA тренда"
            )
        elif close < ema_trend:
            bearish += 10
            bearish_reasons.append(
                "Цена ниже EMA тренда"
            )

        # RSI
        if 52 <= rsi <= 68:
            bullish += 15
            bullish_reasons.append(
                f"RSI поддерживает рост ({rsi:.1f})"
            )
        elif 32 <= rsi <= 48:
            bearish += 15
            bearish_reasons.append(
                f"RSI поддерживает падение ({rsi:.1f})"
            )
        elif rsi < 30:
            bullish += 8
            bullish_reasons.append(
                f"RSI в зоне перепроданности ({rsi:.1f})"
            )
        elif rsi > 70:
            bearish += 8
            bearish_reasons.append(
                f"RSI в зоне перекупленности ({rsi:.1f})"
            )

        # MACD
        if macd > macd_signal:
            bullish += 15
            bullish_reasons.append(
                "MACD выше сигнальной линии"
            )
        elif macd < macd_signal:
            bearish += 15
            bearish_reasons.append(
                "MACD ниже сигнальной линии"
            )

        # Bollinger
        if close <= bb_lower:
            bullish += 10
            bullish_reasons.append(
                "Цена возле нижней полосы Bollinger"
            )
        elif close >= bb_upper:
            bearish += 10
            bearish_reasons.append(
                "Цена возле верхней полосы Bollinger"
            )
        elif close > bb_middle:
            bullish += 5
        elif close < bb_middle:
            bearish += 5

        # Stochastic
        if (
            stochastic_k > stochastic_d
            and stochastic_k < 80
        ):
            bullish += 10
            bullish_reasons.append(
                "Stochastic поддерживает рост"
            )
        elif (
            stochastic_k < stochastic_d
            and stochastic_k > 20
        ):
            bearish += 10
            bearish_reasons.append(
                "Stochastic поддерживает падение"
            )

        total = bullish + bearish

        if total <= 0:
            return None

        if bullish > bearish:
            direction = SIGNAL_UP
            score = bullish
            reasons = bullish_reasons
        else:
            direction = SIGNAL_DOWN
            score = bearish
            reasons = bearish_reasons

        opposite = min(
            bullish,
            bearish,
        )

        conflict_penalty = opposite * 0.35

        quality = max(
            0.0,
            min(
                100.0,
                score - conflict_penalty,
            ),
        )

        # Чем больше преимущество выбранного направления,
        # тем выше итоговая уверенность.
        dominance = abs(
            bullish - bearish
        )

        confidence = min(
            100.0,
            55.0 + dominance * 1.15,
        )

        confidence = (
            confidence * 0.55
            + quality * 0.45
        )

        confidence = round(
            max(0.0, min(100.0, confidence)),
            2,
        )

        quality = round(
            quality,
            2,
        )

        if confidence < MIN_SIGNAL_CONFIDENCE:
            return None

        if quality < MIN_SIGNAL_QUALITY:
            return None

        now = datetime.now(timezone.utc)

        return SignalCandidate(
            pair=pair,
            direction=direction,
            expiry_minutes=expiry_minutes,
            confidence=confidence,
            quality=quality,
            entry_price=close,
            reasons=reasons[:8],
            created_at=now,
            expires_at=now
            + timedelta(
                minutes=expiry_minutes
            ),
            source=source,
        )
