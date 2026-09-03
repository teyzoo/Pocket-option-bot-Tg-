from __future__ import annotations

from typing import Iterable

import pandas as pd

from config import (
    BOLLINGER_SCORE,
    EMA_SCORE,
    MACD_SCORE,
    MIN_SIGNAL_CONFIDENCE,
    MIN_SIGNAL_CONFIRMATIONS,
    MIN_SIGNAL_QUALITY,
    MIN_SIGNAL_WINRATE,
    PRICE_ACTION_SCORE,
    RSI_SCORE,
    STOCHASTIC_SCORE,
    TREND_SCORE,
)
from indicators import latest_indicators
from models import SignalCandidate
from probability import probability_calibrator
from time_utils import calculate_expiry, utc_now
from utils import clamp


class SignalEngine:
    def analyze(
        self,
        pair: str,
        market: str,
        df: pd.DataFrame,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:
        if len(df) < 80:
            return None

        indicators = latest_indicators(df)

        bullish_score = 0.0
        bearish_score = 0.0

        confirmations: list[str] = []
        reasons: list[str] = []

        if (
            indicators.ema_fast
            > indicators.ema_slow
        ):
            bullish_score += EMA_SCORE
            confirmations.append(
                "EMA 9 выше EMA 21"
            )
        elif (
            indicators.ema_fast
            < indicators.ema_slow
        ):
            bearish_score += EMA_SCORE
            confirmations.append(
                "EMA 9 ниже EMA 21"
            )

        if (
            indicators.price
            > indicators.ema_trend
        ):
            bullish_score += TREND_SCORE
            confirmations.append(
                "Цена выше EMA 50"
            )
        elif (
            indicators.price
            < indicators.ema_trend
        ):
            bearish_score += TREND_SCORE
            confirmations.append(
                "Цена ниже EMA 50"
            )

        if indicators.rsi >= 55:
            bullish_score += RSI_SCORE
            confirmations.append(
                f"RSI {indicators.rsi:.1f} bullish"
            )
        elif indicators.rsi <= 45:
            bearish_score += RSI_SCORE
            confirmations.append(
                f"RSI {indicators.rsi:.1f} bearish"
            )

        if (
            indicators.macd
            > indicators.macd_signal
            and indicators.macd_histogram > 0
        ):
            bullish_score += MACD_SCORE
            confirmations.append(
                "MACD bullish"
            )
        elif (
            indicators.macd
            < indicators.macd_signal
            and indicators.macd_histogram < 0
        ):
            bearish_score += MACD_SCORE
            confirmations.append(
                "MACD bearish"
            )

        if (
            indicators.price
            > indicators.bb_middle
        ):
            bullish_score += BOLLINGER_SCORE
            confirmations.append(
                "Цена выше средней BB"
            )
        elif (
            indicators.price
            < indicators.bb_middle
        ):
            bearish_score += BOLLINGER_SCORE
            confirmations.append(
                "Цена ниже средней BB"
            )

        if (
            indicators.stochastic_k
            > indicators.stochastic_d
        ):
            bullish_score += STOCHASTIC_SCORE
            confirmations.append(
                "Stochastic bullish"
            )
        elif (
            indicators.stochastic_k
            < indicators.stochastic_d
        ):
            bearish_score += STOCHASTIC_SCORE
            confirmations.append(
                "Stochastic bearish"
            )

        calculated_body = (
            df.iloc[-1]["close"]
            - df.iloc[-1]["open"]
        )

        if calculated_body > 0:
            bullish_score += PRICE_ACTION_SCORE
            confirmations.append(
                "Последняя свеча bullish"
            )
        elif calculated_body < 0:
            bearish_score += PRICE_ACTION_SCORE
            confirmations.append(
                "Последняя свеча bearish"
            )

        if bullish_score == bearish_score:
            return None

        if bullish_score > bearish_score:
            direction = "UP"
            score = bullish_score
            opposite = bearish_score
        else:
            direction = "DOWN"
            score = bearish_score
            opposite = bullish_score

        conflict = opposite / max(
            score,
            1,
        )

        quality = clamp(
            score - conflict * 15,
            0,
            100,
        )

        confidence = clamp(
            (
                score
                / 85
                * 100
            ),
            0,
            100,
        )

        probability = (
            probability_calibrator.estimate(
                df,
                expiry_minutes,
            )
        )

        winrate = probability.winrate

        if not probability.reliable:
            return None

        if winrate < MIN_SIGNAL_WINRATE:
            return None

        if confidence < MIN_SIGNAL_CONFIDENCE:
            return None

        if quality < MIN_SIGNAL_QUALITY:
            return None

        if len(confirmations) < MIN_SIGNAL_CONFIRMATIONS:
            return None

        reasons.extend(confirmations)

        created_at = utc_now()

        return SignalCandidate(
            pair=pair,
            market=market,
            direction=direction,
            expiry_minutes=expiry_minutes,
            confidence=confidence,
            quality=quality,
            winrate=winrate,
            entry_price=indicators.price,
            created_at=created_at,
            expires_at=calculate_expiry(
                expiry_minutes,
                created_at,
            ),
            source=source,
            reasons=reasons,
            confirmations=confirmations,
            indicators=indicators,
        )
