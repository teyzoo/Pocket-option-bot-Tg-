from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pandas as pd

from backtest import run_backtest
from config import (
    MIN_SIGNAL_CONFIDENCE,
    MIN_SIGNAL_CONFIRMATIONS,
    MIN_SIGNAL_QUALITY,
    MIN_SIGNAL_WINRATE,
)
from indicators import calculate_indicators, latest_indicators
from models import SignalCandidate
from probability import probability_calibrator


class SignalEngine:
    """
    Основной движок анализа торгового сигнала.

    Задача:
        1. Подготовить свечи и индикаторы.
        2. Определить направление.
        3. Проверить историческую вероятность через backtest.
        4. Рассчитать quality/confidence.
        5. Вернуть SignalCandidate только если сигнал
           проходит установленные фильтры.

    Важно:
        Движок НЕ создаёт искусственные сигналы.
        Если условия не выполнены — возвращается None.
    """

    def __init__(
        self,
        min_winrate: float = MIN_SIGNAL_WINRATE,
        min_confidence: float = MIN_SIGNAL_CONFIDENCE,
        min_quality: float = MIN_SIGNAL_QUALITY,
        min_confirmations: int = MIN_SIGNAL_CONFIRMATIONS,
    ) -> None:
        self.min_winrate = float(min_winrate)
        self.min_confidence = float(min_confidence)
        self.min_quality = float(min_quality)
        self.min_confirmations = int(min_confirmations)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def analyze(
        self,
        pair: str,
        market: Any,
        df: pd.DataFrame,
        expiry_minutes: int,
        source: str = "manual",
    ) -> Optional[SignalCandidate]:
        """
        Анализ одной пары.

        Возвращает:
            SignalCandidate — если найден сильный сигнал.
            None — если сигнал не прошёл фильтры.
        """

        if df is None or df.empty:
            return None

        if expiry_minutes < 1 or expiry_minutes > 20:
            return None

        prepared = self._prepare_dataframe(df)

        if prepared is None:
            return None

        if len(prepared) < 60:
            return None

        try:
            current = latest_indicators(prepared)
        except Exception:
            return None

        if not current:
            return None

        direction = self._detect_direction(current)

        if direction is None:
            return None

        # --------------------------------------------------------------
        # Исторический backtest по конкретному направлению
        # --------------------------------------------------------------

        try:
            backtest_result = run_backtest(
                prepared,
                expiry_minutes,
                direction=direction,
            )
        except Exception:
            return None

        if backtest_result is None:
            return None

        decisive_trades = int(
            getattr(backtest_result, "decisive_trades", 0)
        )

        wins = int(getattr(backtest_result, "wins", 0))
        losses = int(getattr(backtest_result, "losses", 0))
        draws = int(getattr(backtest_result, "draws", 0))

        if decisive_trades <= 0:
            return None

        historical_winrate = float(
            getattr(backtest_result, "winrate", 0.0)
        )

        # --------------------------------------------------------------
        # Probability calibrator
        # --------------------------------------------------------------

        try:
            probability = probability_calibrator.estimate(
                prepared,
                expiry_minutes,
                direction=direction,
            )
        except TypeError:
            # Совместимость с более старой реализацией calibrator.
            try:
                probability = probability_calibrator.estimate(
                    prepared,
                    expiry_minutes,
                )
            except Exception:
                probability = None
        except Exception:
            probability = None

        calibrated_probability = self._extract_probability(
            probability,
            historical_winrate,
        )

        # Для итогового winrate используем более консервативное значение.
        effective_winrate = min(
            historical_winrate,
            calibrated_probability,
        )

        # Если calibrator не смог дать значение, не блокируем
        # сигнал только из-за отсутствия калибровки — backtest
        # остаётся главным историческим источником.
        if calibrated_probability <= 0:
            effective_winrate = historical_winrate

        # --------------------------------------------------------------
        # Confidence
        # --------------------------------------------------------------

        confidence = self._calculate_confidence(
            current=current,
            historical_winrate=historical_winrate,
            calibrated_probability=calibrated_probability,
            confirmations=self._count_confirmations(current, direction),
        )

        # --------------------------------------------------------------
        # Quality
        # --------------------------------------------------------------

        quality, reasons, confirmations = self._calculate_quality(
            current=current,
            direction=direction,
            historical_winrate=historical_winrate,
            calibrated_probability=calibrated_probability,
            backtest_result=backtest_result,
        )

        # --------------------------------------------------------------
        # Финальный фильтр
        # --------------------------------------------------------------

        if effective_winrate < self.min_winrate:
            return None

        if confidence < self.min_confidence:
            return None

        if quality < self.min_quality:
            return None

        if confirmations < self.min_confirmations:
            return None

        price = self._safe_float(
            current.get("price"),
            prepared["close"].iloc[-1],
        )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expiry_minutes)

        indicators = self._clean_indicators(current)

        metadata: Dict[str, Any] = {
            "historical_winrate": round(historical_winrate, 2),
            "calibrated_probability": round(
                calibrated_probability,
                2,
            ),
            "effective_winrate": round(
                effective_winrate,
                2,
            ),
            "backtest_trades": decisive_trades,
            "backtest_wins": wins,
            "backtest_losses": losses,
            "backtest_draws": draws,
        }

        return SignalCandidate(
            pair=pair,
            direction=direction,
            expiry_minutes=expiry_minutes,
            confidence=round(confidence, 2),
            quality=round(quality, 2),
            winrate=round(effective_winrate, 2),
            entry_price=price,
            created_at=now,
            expires_at=expires_at,
            source=source,
            market=self._market_name(market),
            reasons=reasons,
            confirmations=confirmations,
            indicators=indicators,
            chart_path=None,
            metadata=metadata,
            winrate_trades=decisive_trades,
            winrate_wins=wins,
            winrate_losses=losses,
            winrate_draws=draws,
        )

    # ------------------------------------------------------------------
    # DATA PREPARATION
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_dataframe(
        df: pd.DataFrame,
    ) -> Optional[pd.DataFrame]:
        try:
            result = df.copy()

            required = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]

            for column in required:
                if column not in result.columns:
                    return None

            result["datetime"] = pd.to_datetime(
                result["datetime"],
                errors="coerce",
            )

            numeric_columns = [
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]

            for column in numeric_columns:
                result[column] = pd.to_numeric(
                    result[column],
                    errors="coerce",
                )

            result = result.dropna(
                subset=required,
            )

            result = result.sort_values(
                "datetime",
            )

            result = result.drop_duplicates(
                subset=["datetime"],
                keep="last",
            )

            result = result.reset_index(
                drop=True,
            )

            if len(result) < 60:
                return None

            result = calculate_indicators(result)

            result = result.replace(
                [float("inf"), float("-inf")],
                pd.NA,
            )

            return result

        except Exception:
            return None

    # ------------------------------------------------------------------
    # DIRECTION
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_direction(
        indicators: Dict[str, Any],
    ) -> Optional[str]:
        """
        Определение направления на основе нескольких подтверждений.

        Используются:
            EMA
            TREND
            RSI
            MACD
            Bollinger
            Stochastic
            Price Action
        """

        bullish = 0
        bearish = 0

        # EMA
        ema_fast = SignalEngine._safe_float(
            indicators.get("ema_fast")
        )
        ema_slow = SignalEngine._safe_float(
            indicators.get("ema_slow")
        )

        if ema_fast is not None and ema_slow is not None:
            if ema_fast > ema_slow:
                bullish += 1
            elif ema_fast < ema_slow:
                bearish += 1

        # TREND / EMA trend
        ema_trend = SignalEngine._safe_float(
            indicators.get("ema_trend")
        )

        price = SignalEngine._safe_float(
            indicators.get("price")
        )

        if ema_trend is not None and price is not None:
            if price > ema_trend:
                bullish += 1
            elif price < ema_trend:
                bearish += 1

        # RSI
        rsi = SignalEngine._safe_float(
            indicators.get("rsi")
        )

        if rsi is not None:
            if rsi >= 52:
                bullish += 1
            elif rsi <= 48:
                bearish += 1

        # MACD
        macd = SignalEngine._safe_float(
            indicators.get("macd")
        )
        macd_signal = SignalEngine._safe_float(
            indicators.get("macd_signal")
        )

        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                bullish += 1
            elif macd < macd_signal:
                bearish += 1

        # Bollinger
        bb_middle = SignalEngine._safe_float(
            indicators.get("bb_middle")
        )

        if price is not None and bb_middle is not None:
            if price > bb_middle:
                bullish += 1
            elif price < bb_middle:
                bearish += 1

        # Stochastic
        stoch_k = SignalEngine._safe_float(
            indicators.get("stoch_k")
        )
        stoch_d = SignalEngine._safe_float(
            indicators.get("stoch_d")
        )

        if stoch_k is not None and stoch_d is not None:
            if stoch_k > stoch_d:
                bullish += 1
            elif stoch_k < stoch_d:
                bearish += 1

        # Price action
        bullish_candle = bool(
            indicators.get("bullish")
        )
        bearish_candle = bool(
            indicators.get("bearish")
        )

        if bullish_candle:
            bullish += 1

        if bearish_candle:
            bearish += 1

        # Требуем явного перевеса.
        if bullish >= 4 and bullish > bearish:
            return "UP"

        if bearish >= 4 and bearish > bullish:
            return "DOWN"

        return None

    # ------------------------------------------------------------------
    # CONFIRMATIONS
    # ------------------------------------------------------------------

    @staticmethod
    def _count_confirmations(
        indicators: Dict[str, Any],
        direction: str,
    ) -> int:
        confirmations = 0

        price = SignalEngine._safe_float(
            indicators.get("price")
        )

        ema_fast = SignalEngine._safe_float(
            indicators.get("ema_fast")
        )

        ema_slow = SignalEngine._safe_float(
            indicators.get("ema_slow")
        )

        ema_trend = SignalEngine._safe_float(
            indicators.get("ema_trend")
        )

        rsi = SignalEngine._safe_float(
            indicators.get("rsi")
        )

        macd = SignalEngine._safe_float(
            indicators.get("macd")
        )

        macd_signal = SignalEngine._safe_float(
            indicators.get("macd_signal")
        )

        bb_middle = SignalEngine._safe_float(
            indicators.get("bb_middle")
        )

        stoch_k = SignalEngine._safe_float(
            indicators.get("stoch_k")
        )

        stoch_d = SignalEngine._safe_float(
            indicators.get("stoch_d")
        )

        if direction == "UP":
            if (
                ema_fast is not None
                and ema_slow is not None
                and ema_fast > ema_slow
            ):
                confirmations += 1

            if (
                price is not None
                and ema_trend is not None
                and price > ema_trend
            ):
                confirmations += 1

            if rsi is not None and rsi >= 52:
                confirmations += 1

            if (
                macd is not None
                and macd_signal is not None
                and macd > macd_signal
            ):
                confirmations += 1

            if (
                price is not None
                and bb_middle is not None
                and price > bb_middle
            ):
                confirmations += 1

            if (
                stoch_k is not None
                and stoch_d is not None
                and stoch_k > stoch_d
            ):
                confirmations += 1

            if indicators.get("bullish"):
                confirmations += 1

        elif direction == "DOWN":
            if (
                ema_fast is not None
                and ema_slow is not None
                and ema_fast < ema_slow
            ):
                confirmations += 1

            if (
                price is not None
                and ema_trend is not None
                and price < ema_trend
            ):
                confirmations += 1

            if rsi is not None and rsi <= 48:
                confirmations += 1

            if (
                macd is not None
                and macd_signal is not None
                and macd < macd_signal
            ):
                confirmations += 1

            if (
                price is not None
                and bb_middle is not None
                and price < bb_middle
            ):
                confirmations += 1

            if (
                stoch_k is not None
                and stoch_d is not None
                and stoch_k < stoch_d
            ):
                confirmations += 1

            if indicators.get("bearish"):
                confirmations += 1

        return confirmations

    # ------------------------------------------------------------------
    # QUALITY
    # ------------------------------------------------------------------

    def _calculate_quality(
        self,
        current: Dict[str, Any],
        direction: str,
        historical_winrate: float,
        calibrated_probability: float,
        backtest_result: Any,
    ) -> tuple[float, list[str], int]:
        confirmations = self._count_confirmations(
            current,
            direction,
        )

        reasons: list[str] = []

        score = 0.0

        # --------------------------------------------------------------
        # Historical probability: 30 points
        # --------------------------------------------------------------

        probability_value = max(
            historical_winrate,
            calibrated_probability,
        )

        probability_component = self._scale(
            probability_value,
            50.0,
            100.0,
        )

        score += probability_component * 30.0

        if probability_value >= 85:
            reasons.append(
                f"Историческая вероятность {probability_value:.1f}%"
            )
        elif probability_value >= 75:
            reasons.append(
                f"Вероятность {probability_value:.1f}%"
            )

        # --------------------------------------------------------------
        # Confirmations: 30 points
        # --------------------------------------------------------------

        confirmation_ratio = confirmations / 7.0
        score += confirmation_ratio * 30.0

        if confirmations >= 6:
            reasons.append(
                f"Сильные подтверждения: {confirmations}/7"
            )
        elif confirmations >= 4:
            reasons.append(
                f"Подтверждения: {confirmations}/7"
            )

        # --------------------------------------------------------------
        # Trend quality: 15 points
        # --------------------------------------------------------------

        if self._trend_matches(
            current,
            direction,
        ):
            score += 15.0
            reasons.append("Тренд подтверждает направление")

        # --------------------------------------------------------------
        # Momentum: 15 points
        # --------------------------------------------------------------

        if self._momentum_matches(
            current,
            direction,
        ):
            score += 15.0
            reasons.append("Импульс подтверждает направление")

        # --------------------------------------------------------------
        # Backtest reliability: 10 points
        # --------------------------------------------------------------

        reliable = bool(
            getattr(
                backtest_result,
                "reliable",
                False,
            )
        )

        if reliable:
            score += 10.0
            reasons.append("Достаточная историческая выборка")

        quality = min(
            100.0,
            max(
                0.0,
                score,
            ),
        )

        if not reasons:
            reasons.append(
                "Недостаточно подтверждений"
            )

        return (
            quality,
            reasons,
            confirmations,
        )

    # ------------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_confidence(
        current: Dict[str, Any],
        historical_winrate: float,
        calibrated_probability: float,
        confirmations: int,
    ) -> float:
        """
        Итоговая confidence.

        Историческая вероятность — основа.
        Индикаторные подтверждения добавляют/убавляют уверенность.
        """

        base = max(
            historical_winrate,
            calibrated_probability,
        )

        confirmation_bonus = (
            confirmations / 7.0
        ) * 10.0

        trend_bonus = (
            5.0
            if SignalEngine._trend_strength(current) >= 1.0
            else 0.0
        )

        confidence = (
            base
            + confirmation_bonus
            + trend_bonus
        )

        return min(
            100.0,
            max(
                0.0,
                confidence,
            ),
        )

    # ------------------------------------------------------------------
    # TREND / MOMENTUM
    # ------------------------------------------------------------------

    @staticmethod
    def _trend_matches(
        indicators: Dict[str, Any],
        direction: str,
    ) -> bool:
        price = SignalEngine._safe_float(
            indicators.get("price")
        )
        ema_fast = SignalEngine._safe_float(
            indicators.get("ema_fast")
        )
        ema_slow = SignalEngine._safe_float(
            indicators.get("ema_slow")
        )
        ema_trend = SignalEngine._safe_float(
            indicators.get("ema_trend")
        )

        if (
            price is None
            or ema_fast is None
            or ema_slow is None
            or ema_trend is None
        ):
            return False

        if direction == "UP":
            return (
                price > ema_fast
                and ema_fast > ema_slow
                and price > ema_trend
            )

        if direction == "DOWN":
            return (
                price < ema_fast
                and ema_fast < ema_slow
                and price < ema_trend
            )

        return False

    @staticmethod
    def _momentum_matches(
        indicators: Dict[str, Any],
        direction: str,
    ) -> bool:
        rsi = SignalEngine._safe_float(
            indicators.get("rsi")
        )

        macd = SignalEngine._safe_float(
            indicators.get("macd")
        )

        macd_signal = SignalEngine._safe_float(
            indicators.get("macd_signal")
        )

        if rsi is None:
            return False

        if macd is None or macd_signal is None:
            return False

        if direction == "UP":
            return (
                rsi >= 52
                and macd > macd_signal
            )

        if direction == "DOWN":
            return (
                rsi <= 48
                and macd < macd_signal
            )

        return False

    @staticmethod
    def _trend_strength(
        indicators: Dict[str, Any],
    ) -> float:
        price = SignalEngine._safe_float(
            indicators.get("price")
        )
        ema_fast = SignalEngine._safe_float(
            indicators.get("ema_fast")
        )
        ema_slow = SignalEngine._safe_float(
            indicators.get("ema_slow")
        )

        if (
            price is None
            or ema_fast is None
            or ema_slow is None
        ):
            return 0.0

        denominator = abs(ema_slow)

        if denominator == 0:
            return 0.0

        distance = abs(
            ema_fast - ema_slow
        ) / denominator

        return distance * 10000.0

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_probability(
        probability: Any,
        fallback: float,
    ) -> float:
        if probability is None:
            return float(fallback)

        if isinstance(
            probability,
            (int, float),
        ):
            return max(
                0.0,
                min(
                    100.0,
                    float(probability),
                ),
            )

        for attr in (
            "probability",
            "winrate",
            "value",
            "estimate",
        ):
            value = getattr(
                probability,
                attr,
                None,
            )

            if value is not None:
                try:
                    return max(
                        0.0,
                        min(
                            100.0,
                            float(value),
                        ),
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

        return float(fallback)

    @staticmethod
    def _clean_indicators(
        indicators: Dict[str, Any],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        for key, value in indicators.items():
            if isinstance(
                value,
                (int, float),
            ):
                if pd.isna(value):
                    continue

                result[key] = round(
                    float(value),
                    8,
                )

            elif isinstance(
                value,
                bool,
            ):
                result[key] = value

            elif value is not None:
                try:
                    if hasattr(value, "item"):
                        result[key] = value.item()
                    else:
                        result[key] = value
                except Exception:
                    result[key] = str(value)

        return result

    @staticmethod
    def _safe_float(
        value: Any,
        default: Any = None,
    ) -> Optional[float]:
        if value is None:
            return default

        try:
            number = float(value)

            if pd.isna(number):
                return default

            return number

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def _scale(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        if maximum <= minimum:
            return 0.0

        normalized = (
            value - minimum
        ) / (
            maximum - minimum
        )

        return max(
            0.0,
            min(
                1.0,
                normalized,
            ),
        )

    @staticmethod
    def _market_name(
        market: Any,
    ) -> str:
        if market is None:
            return "regular"

        if isinstance(
            market,
            str,
        ):
            return market

        for attr in (
            "name",
            "market",
            "market_type",
        ):
            value = getattr(
                market,
                attr,
                None,
            )

            if value:
                return str(value)

        return "regular"
