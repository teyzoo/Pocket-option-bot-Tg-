from __future__ import annotations

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

from indicators import calculate_indicators, latest_indicators

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

        if df is None or df.empty:

            return None

        if len(df) < 80:

            return None

        try:

            prepared = calculate_indicators(df)

            indicators = latest_indicators(prepared)

        except Exception:

            return None

        if not indicators:

            return None

        def number(

            key: str,

        ) -> float | None:

            value = indicators.get(key)

            if value is None:

                return None

            try:

                value = float(value)

            except (

                TypeError,

                ValueError,

            ):

                return None

            if pd.isna(value):

                return None

            return value

        ema_fast = number("ema_fast")

        ema_slow = number("ema_slow")

        ema_trend = number("ema_trend")

        rsi = number("rsi")

        macd = number("macd")

        macd_signal = number("macd_signal")

        macd_histogram = number("macd_histogram")

        bb_middle = number("bollinger_middle")

        stochastic_k = number("stochastic_k")

        stochastic_d = number("stochastic_d")

        price = number("price")

        if any(

            value is None

            for value in (

                ema_fast,

                ema_slow,

                ema_trend,

                rsi,

                macd,

                macd_signal,

                macd_histogram,

                bb_middle,

                stochastic_k,

                stochastic_d,

                price,

            )

        ):

            return None

        bullish_score = 0.0

        bearish_score = 0.0

        confirmations: list[str] = []

        # EMA

        if ema_fast > ema_slow:

            bullish_score += EMA_SCORE

            confirmations.append(

                "EMA 9 выше EMA 21"

            )

        elif ema_fast < ema_slow:

            bearish_score += EMA_SCORE

            confirmations.append(

                "EMA 9 ниже EMA 21"

            )

        # Trend

        if price > ema_trend:

            bullish_score += TREND_SCORE

            confirmations.append(

                "Цена выше EMA 50"

            )

        elif price < ema_trend:

            bearish_score += TREND_SCORE

            confirmations.append(

                "Цена ниже EMA 50"

            )

        # RSI

        if rsi >= 55:

            bullish_score += RSI_SCORE

            confirmations.append(

                f"RSI {rsi:.1f} bullish"

            )

        elif rsi <= 45:

            bearish_score += RSI_SCORE

            confirmations.append(

                f"RSI {rsi:.1f} bearish"

            )

        # MACD

        if (

            macd > macd_signal

            and macd_histogram > 0

        ):

            bullish_score += MACD_SCORE

            confirmations.append(

                "MACD bullish"

            )

        elif (

            macd < macd_signal

            and macd_histogram < 0

        ):

            bearish_score += MACD_SCORE

            confirmations.append(

                "MACD bearish"

            )

        # Bollinger

        if price > bb_middle:

            bullish_score += BOLLINGER_SCORE

            confirmations.append(

                "Цена выше средней BB"

            )

        elif price < bb_middle:

            bearish_score += BOLLINGER_SCORE

            confirmations.append(

                "Цена ниже средней BB"

            )

        # Stochastic

        if stochastic_k > stochastic_d:

            bullish_score += STOCHASTIC_SCORE

            confirmations.append(

                "Stochastic bullish"

            )

        elif stochastic_k < stochastic_d:

            bearish_score += STOCHASTIC_SCORE

            confirmations.append(

                "Stochastic bearish"

            )

        # Price action

        last_open = float(

            prepared.iloc[-1]["open"]

        )

        last_close = float(

            prepared.iloc[-1]["close"]

        )

        if last_close > last_open:

            bullish_score += PRICE_ACTION_SCORE

            confirmations.append(

                "Последняя свеча bullish"

            )

        elif last_close < last_open:

            bearish_score += PRICE_ACTION_SCORE

            confirmations.append(

                "Последняя свеча bearish"

            )

        if bullish_score <= 0 and bearish_score <= 0:

            return None

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

        conflict = opposite / max(score, 1.0)

        quality = clamp(

            score - conflict * 15.0,

            0.0,

            100.0,

        )

        confidence = clamp(

            score / 85.0 * 100.0,

            0.0,

            100.0,

        )

        try:

            probability = probability_calibrator.estimate(

                prepared,

                int(expiry_minutes),

            )

        except Exception:

            return None

        winrate = float(

            probability.winrate or 0

        )

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

        created_at = utc_now()

        metadata = {

            "winrate_trades": int(

                probability.trades

            ),

            "winrate_wins": int(

                probability.wins

            ),

            "winrate_losses": int(

                probability.losses

            ),

            "winrate_draws": int(

                probability.draws

            ),

        }

        return SignalCandidate(

            pair=pair,

            market=market,

            direction=direction,

            expiry_minutes=int(expiry_minutes),

            confidence=float(confidence),

            quality=float(quality),

            winrate=winrate,

            entry_price=float(price),

            created_at=created_at,

            expires_at=calculate_expiry(

                created_at,

                int(expiry_minutes),

            ),

            source=source,

            reasons=list(confirmations),

            confirmations=len(confirmations),

            indicators=indicators,

            metadata=metadata,

        )
