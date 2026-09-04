from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pandas as pd

from backtest import evaluate_row, run_backtest
from config import (
    MAX_EXPIRY_MINUTES,
    MIN_CANDLES,
    MIN_SIGNAL_CONFIDENCE,
    MIN_SIGNAL_QUALITY,
    MIN_SIGNAL_WINRATE,
)
from indicators import calculate_indicators
from models import SignalCandidate
from probability import ProbabilityCalibrator


logger = logging.getLogger("signal_engine")


class SignalEngine:
    """
    Главный движок сигналов.

    Логика:
    1. Проверяем свежие свечи.
    2. Рассчитываем индикаторы.
    3. Определяем направление по текущей свече.
    4. Проверяем количество подтверждений.
    5. Проверяем исторический backtest именно для выбранного
       направления и конкретной экспирации.
    6. Требуем минимум 10 результативных исторических сделок.
    7. Требуем исторический WINRATE >= 75%.
    8. Возвращаем лучший подтверждённый сигнал.

    Никаких искусственных сигналов ради заполнения ленты.
    """

    def __init__(
        self,
        calibrator: Optional[
            ProbabilityCalibrator
        ] = None,
    ) -> None:

        self.calibrator = (
            calibrator
            or ProbabilityCalibrator()
        )

    @staticmethod
    def _normalize_expiry(
        expiry_minutes: int,
    ) -> Optional[int]:

        try:
            expiry = int(expiry_minutes)
        except (TypeError, ValueError):
            return None

        if expiry < 1:
            return None

        if expiry > MAX_EXPIRY_MINUTES:
            return None

        return expiry

    @staticmethod
    def _prepare_dataframe(
        df: pd.DataFrame,
    ) -> Optional[pd.DataFrame]:

        if df is None or df.empty:
            return None

        data = df.copy()

        required_price_columns = {
            "open",
            "high",
            "low",
            "close",
        }

        if not required_price_columns.issubset(
            set(data.columns)
        ):
            logger.warning(
                "SignalEngine: missing OHLC columns"
            )
            return None

        if "datetime" in data.columns:
            data["datetime"] = pd.to_datetime(
                data["datetime"],
                utc=True,
                errors="coerce",
            )

        for column in [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]:
            if column in data.columns:
                data[column] = pd.to_numeric(
                    data[column],
                    errors="coerce",
                )

        data = data.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close",
            ]
        )

        if data.empty:
            return None

        if "datetime" in data.columns:
            data = (
                data
                .sort_values("datetime")
                .drop_duplicates(
                    subset=["datetime"],
                    keep="last",
                )
                .reset_index(drop=True)
            )
        else:
            data = (
                data
                .reset_index(drop=True)
            )

        if len(data) < MIN_CANDLES:
            return None

        # Не рассчитываем индикаторы второй раз,
        # если scanner/market уже передал подготовленный DF.
        indicator_columns = {
            "ema_fast",
            "ema_slow",
            "ema_trend",
            "rsi",
            "macd",
            "macd_signal",
            "bollinger_middle",
            "stochastic_k",
            "stochastic_d",
            "atr",
        }

        if not indicator_columns.issubset(
            set(data.columns)
        ):
            data = calculate_indicators(data)

        if len(data) < MIN_CANDLES:
            return None

        return data

    @staticmethod
    def _quality_score(
        confidence: float,
        winrate: float,
        confirmations: int,
    ) -> float:
        """
        Итоговый Quality Score.

        Это не заменяет исторический WINRATE.
        Исторический WINRATE остаётся обязательным фильтром.
        """

        confidence_component = min(
            100.0,
            max(
                0.0,
                float(confidence),
            ),
        )

        winrate_component = min(
            100.0,
            max(
                0.0,
                float(winrate),
            ),
        )

        confirmation_component = min(
            100.0,
            max(
                0.0,
                float(confirmations)
                / 7.0
                * 100.0,
            ),
        )

        quality = (
            confidence_component * 0.35
            + winrate_component * 0.50
            + confirmation_component * 0.15
        )

        return round(
            min(100.0, quality),
            2,
        )

    @staticmethod
    def _candidate_sort_key(
        candidate: SignalCandidate,
    ):
        return (
            float(candidate.winrate),
            float(candidate.quality),
            float(candidate.confidence),
            int(candidate.confirmations),
            int(candidate.winrate_trades),
        )

    def analyze(
        self,
        pair: str,
        market: str,
        df: pd.DataFrame,
        expiry_minutes: int,
        source: str = "manual",
    ) -> Optional[SignalCandidate]:

        expiry = self._normalize_expiry(
            expiry_minutes
        )

        if expiry is None:
            logger.warning(
                "%s | invalid expiry=%s",
                pair,
                expiry_minutes,
            )
            return None

        prepared = self._prepare_dataframe(df)

        if prepared is None:
            logger.info(
                "%s | insufficient/invalid candle data",
                pair,
            )
            return None

        try:
            current_row = prepared.iloc[-1]

            (
                direction,
                confirmations,
                confidence,
                reasons,
            ) = evaluate_row(
                current_row
            )

            if direction is None:
                logger.info(
                    "%s | no direction from current candle",
                    pair,
                )
                return None

            if (
                confirmations
                < MIN_SIGNAL_CONFIRMATIONS
            ):
                logger.info(
                    "%s | rejected: confirmations=%s < %s",
                    pair,
                    confirmations,
                    MIN_SIGNAL_CONFIRMATIONS,
                )
                return None

            if (
                confidence
                < MIN_SIGNAL_CONFIDENCE
            ):
                logger.info(
                    "%s | rejected: confidence=%.2f < %.2f",
                    pair,
                    confidence,
                    MIN_SIGNAL_CONFIDENCE,
                )
                return None

            # ---------------------------------------------------------
            # HISTORICAL BACKTEST
            # ---------------------------------------------------------
            #
            # Проверяем именно то направление, которое показывает
            # текущая свеча.
            #
            # Это важнее общего winrate пары.
            # ---------------------------------------------------------

            backtest = run_backtest(
                prepared,
                expiry_minutes=expiry,
                direction=direction,
            )

            trades = (
                backtest.decisive_trades
            )

            historical_winrate = (
                backtest.winrate
            )

            if trades < 10:
                logger.info(
                    "%s | %s min | rejected: "
                    "only %s historical trades",
                    pair,
                    expiry,
                    trades,
                )
                return None

            if (
                historical_winrate
                < MIN_SIGNAL_WINRATE
            ):
                logger.info(
                    "%s | %s min | rejected: "
                    "historical winrate %.2f%% < %.2f%%",
                    pair,
                    expiry,
                    historical_winrate,
                    MIN_SIGNAL_WINRATE,
                )
                return None

            # ---------------------------------------------------------
            # Probability calibrator.
            #
            # Он используется как дополнительная статистика/metadata,
            # но не должен второй раз уничтожать уже подтверждённый
            # историческим backtest кандидат.
            # ---------------------------------------------------------

            calibrated_probability = None

            try:
                calibrated_probability = (
                    self.calibrator.calibrate(
                        historical_winrate
                    )
                )
            except TypeError:
                try:
                    calibrated_probability = (
                        self.calibrator.calibrate(
                            historical_winrate,
                            trades,
                        )
                    )
                except Exception:
                    calibrated_probability = None
            except Exception:
                calibrated_probability = None

            quality = self._quality_score(
                confidence=confidence,
                winrate=historical_winrate,
                confirmations=confirmations,
            )

            # Quality Score не должен отбрасывать сигнал,
            # если основные требования уже выполнены.
            #
            # Но если конфигурация явно установила порог,
            # оставляем мягкую проверку только ниже базового
            # минимального значения.
            if (
                MIN_SIGNAL_QUALITY > 0
                and quality < MIN_SIGNAL_QUALITY
            ):
                logger.info(
                    "%s | %s min | rejected: "
                    "quality %.2f < %.2f",
                    pair,
                    expiry,
                    quality,
                    MIN_SIGNAL_QUALITY,
                )
                return None

            entry_price = float(
                current_row["close"]
            )

            created_at = datetime.now(
                timezone.utc
            )

            expires_at = (
                created_at
                + timedelta(
                    minutes=expiry
                )
            )

            metadata: Dict[str, Any] = {
                "historical_total": (
                    backtest.total
                ),
                "historical_wins": (
                    backtest.wins
                ),
                "historical_losses": (
                    backtest.losses
                ),
                "historical_draws": (
                    backtest.draws
                ),
                "historical_decisive": (
                    trades
                ),
                "historical_winrate": (
                    historical_winrate
                ),
                "calibrated_probability": (
                    calibrated_probability
                ),
                "min_required_winrate": (
                    MIN_SIGNAL_WINRATE
                ),
                "min_required_trades": 10,
                "min_confirmations": (
                    MIN_SIGNAL_CONFIRMATIONS
                ),
                "source": source,
            }

            indicators: Dict[str, Any] = {}

            indicator_names = [
                "ema_fast",
                "ema_slow",
                "ema_trend",
                "rsi",
                "macd",
                "macd_signal",
                "macd_histogram",
                "bollinger_middle",
                "bollinger_upper",
                "bollinger_lower",
                "stochastic_k",
                "stochastic_d",
                "atr",
                "candle_body",
                "upper_wick",
                "lower_wick",
            ]

            for name in indicator_names:
                if name not in current_row:
                    continue

                value = current_row[name]

                try:
                    if pd.isna(value):
                        continue

                    indicators[name] = float(
                        value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    indicators[name] = value

            candidate = SignalCandidate(
                pair=pair,
                direction=direction,
                expiry_minutes=expiry,
                confidence=round(
                    float(confidence),
                    2,
                ),
                quality=quality,
                winrate=round(
                    float(historical_winrate),
                    2,
                ),
                entry_price=entry_price,
                created_at=created_at,
                expires_at=expires_at,
                source=source,
                market=market,
                reasons=reasons,
                confirmations=int(
                    confirmations
                ),
                indicators=indicators,
                chart_path=None,
                metadata=metadata,
                winrate_trades=trades,
                wins=backtest.wins,
                losses=backtest.losses,
                draws=backtest.draws,
            )

            logger.info(
                "%s | SIGNAL FOUND | %s | "
                "expiry=%sm | confidence=%.2f | "
                "quality=%.2f | historical=%.2f%% | "
                "trades=%s | confirmations=%s",
                pair,
                direction,
                expiry,
                confidence,
                quality,
                historical_winrate,
                trades,
                confirmations,
            )

            return candidate

        except Exception:
            logger.exception(
                "%s | SignalEngine analyze failed",
                pair,
            )
            return None

    def find_best(
        self,
        candidates,
    ) -> Optional[SignalCandidate]:

        valid = [
            candidate
            for candidate in candidates
            if candidate is not None
        ]

        if not valid:
            return None

        valid.sort(
            key=self._candidate_sort_key,
            reverse=True,
        )

        return valid[0]

    def analyze_many_expiries(
        self,
        pair: str,
        market: str,
        df: pd.DataFrame,
        source: str = "manual",
        min_expiry: int = 1,
        max_expiry: Optional[int] = None,
    ):
        """
        Синхронный helper для проверки нескольких экспираций.

        Scanner может запускать этот метод через asyncio.to_thread.
        """

        if max_expiry is None:
            max_expiry = MAX_EXPIRY_MINUTES

        min_expiry = max(
            1,
            int(min_expiry),
        )

        max_expiry = min(
            MAX_EXPIRY_MINUTES,
            int(max_expiry),
        )

        candidates = []

        for expiry in range(
            min_expiry,
            max_expiry + 1,
        ):
            candidate = self.analyze(
                pair=pair,
                market=market,
                df=df,
                expiry_minutes=expiry,
                source=source,
            )

            if candidate is not None:
                candidates.append(
                    candidate
                )

        return candidates
