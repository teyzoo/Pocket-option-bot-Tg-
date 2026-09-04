from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from backtest import evaluate_row, run_backtest
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
    Основной движок поиска сигналов.

    Логика:

        свежие 1m свечи
                ↓
        технические индикаторы
                ↓
        текущее направление
                ↓
        исторический backtest
                ↓
        WINRATE >= заданного порога
                ↓
        QUALITY / CONFIDENCE
                ↓
        SignalCandidate

    Важный принцип:
        мы НЕ создаём искусственный сигнал.

        Если текущая ситуация не подтверждена исторически,
        возвращается None.

    При этом текущий сигнал и backtest используют
    одну и ту же систему оценки из backtest.py.
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
        self.min_confirmations = int(
            min_confirmations
        )

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze(
        self,
        pair: str,
        market: Any,
        df: pd.DataFrame,
        expiry_minutes: int,
        source: str = "manual",
    ) -> SignalCandidate | None:
        """
        Анализирует одну пару для конкретного времени экспирации.

        Возвращает SignalCandidate только при выполнении
        всех обязательных условий.
        """

        # --------------------------------------------------------
        # Проверяем expiry
        # --------------------------------------------------------

        try:
            expiry = int(expiry_minutes)
        except (
            TypeError,
            ValueError,
        ):
            return None

        if expiry < 1 or expiry > 20:
            return None

        # --------------------------------------------------------
        # Проверяем данные
        # --------------------------------------------------------

        if df is None or df.empty:
            return None

        prepared = self._prepare_dataframe(
            df
        )

        if prepared is None:
            return None

        # Для EMA 50 + backtest нужна нормальная история.
        if len(prepared) < 80:
            return None

        # --------------------------------------------------------
        # ТЕКУЩАЯ СИТУАЦИЯ
        # --------------------------------------------------------

        try:
            current = latest_indicators(
                prepared
            )
        except Exception:
            return None

        if not current:
            return None

        # --------------------------------------------------------
        # Используем ТОЧНО ту же систему,
        # что и backtest.py.
        # --------------------------------------------------------

        try:
            current_row = prepared.iloc[-1]

            (
                direction,
                confirmations,
                current_confidence,
                current_reasons,
            ) = evaluate_row(
                current_row
            )

        except Exception:
            return None

        if direction not in {
            "UP",
            "DOWN",
        }:
            return None

        if confirmations < self.min_confirmations:
            return None

        # --------------------------------------------------------
        # Исторический backtest
        # --------------------------------------------------------

        try:
            backtest_result = run_backtest(
                prepared,
                expiry,
                direction=direction,
            )
        except Exception:
            return None

        if backtest_result is None:
            return None

        trades = int(
            getattr(
                backtest_result,
                "decisive_trades",
                0,
            )
        )

        wins = int(
            getattr(
                backtest_result,
                "wins",
                0,
            )
        )

        losses = int(
            getattr(
                backtest_result,
                "losses",
                0,
            )
        )

        draws = int(
            getattr(
                backtest_result,
                "draws",
                0,
            )
        )

        # Нельзя считать WINRATE по нулевой выборке.
        if trades < 10:
            return None

        historical_winrate = float(
            getattr(
                backtest_result,
                "winrate",
                0.0,
            )
            or 0.0
        )

        # --------------------------------------------------------
        # ГЛАВНЫЙ ФИЛЬТР
        #
        # Именно здесь сохраняем требование пользователя:
        # исторический WINRATE >= 75%.
        # --------------------------------------------------------

        if (
            historical_winrate
            < self.min_winrate
        ):
            return None

        # --------------------------------------------------------
        # Probability calibrator
        #
        # Он использует тот же backtest,
        # поэтому не подменяем реальную статистику.
        # --------------------------------------------------------

        calibrated_winrate = historical_winrate

        try:
            estimate = (
                probability_calibrator.estimate(
                    prepared,
                    expiry,
                    direction=direction,
                )
            )

            if estimate is not None:
                estimate_winrate = float(
                    getattr(
                        estimate,
                        "winrate",
                        0.0,
                    )
                    or 0.0
                )

                if estimate_winrate > 0:
                    calibrated_winrate = (
                        estimate_winrate
                    )

        except Exception:
            # Если calibrator не сработал,
            # исторический backtest всё равно остаётся
            # действительным источником статистики.
            calibrated_winrate = (
                historical_winrate
            )

        # --------------------------------------------------------
        # Итоговый WINRATE.
        #
        # Берём более консервативное значение.
        # --------------------------------------------------------

        effective_winrate = min(
            historical_winrate,
            calibrated_winrate,
        )

        if effective_winrate < self.min_winrate:
            return None

        # --------------------------------------------------------
        # CONFIDENCE
        # --------------------------------------------------------

        confidence = self._calculate_confidence(
            current_confidence=current_confidence,
            historical_winrate=historical_winrate,
            confirmations=confirmations,
        )

        if confidence < self.min_confidence:
            return None

        # --------------------------------------------------------
        # QUALITY
        # --------------------------------------------------------

        quality = self._calculate_quality(
            current_confidence=current_confidence,
            historical_winrate=historical_winrate,
            effective_winrate=effective_winrate,
            confirmations=confirmations,
            trades=trades,
        )

        if quality < self.min_quality:
            return None

        # --------------------------------------------------------
        # ENTRY PRICE
        # --------------------------------------------------------

        price = self._safe_float(
            current.get("price")
        )

        if price is None:
            price = self._safe_float(
                prepared.iloc[-1].get(
                    "close"
                )
            )

        if price is None:
            return None

        # --------------------------------------------------------
        # ВРЕМЯ СОЗДАНИЯ / ЭКСПИРАЦИИ
        # --------------------------------------------------------

        created_at = datetime.now(
            timezone.utc
        )

        expires_at = (
            created_at
            + timedelta(
                minutes=expiry
            )
        )

        # --------------------------------------------------------
        # REASONS
        # --------------------------------------------------------

        reasons = list(
            current_reasons
            or []
        )

        reasons = self._build_reasons(
            reasons=reasons,
            direction=direction,
            historical_winrate=historical_winrate,
            confirmations=confirmations,
            trades=trades,
        )

        # --------------------------------------------------------
        # INDICATORS
        # --------------------------------------------------------

        indicators = self._clean_indicators(
            current
        )

        # --------------------------------------------------------
        # METADATA
        # --------------------------------------------------------

        metadata = {
            "current_confidence": round(
                float(current_confidence),
                2,
            ),
            "historical_winrate": round(
                historical_winrate,
                2,
            ),
            "calibrated_winrate": round(
                calibrated_winrate,
                2,
            ),
            "effective_winrate": round(
                effective_winrate,
                2,
            ),
            "backtest_trades": trades,
            "backtest_wins": wins,
            "backtest_losses": losses,
            "backtest_draws": draws,
            "signal_candle_time": self._get_last_candle_time(
                prepared
            ),
            "timeframe": "1min",
            "analysis": "current_plus_historical",
        }

        # --------------------------------------------------------
        # ГОТОВЫЙ КАНДИДАТ
        # --------------------------------------------------------

        return SignalCandidate(
            pair=pair,
            direction=direction,
            expiry_minutes=expiry,
            confidence=round(
                confidence,
                2,
            ),
            quality=round(
                quality,
                2,
            ),
            winrate=round(
                effective_winrate,
                2,
            ),
            entry_price=price,
            created_at=created_at,
            expires_at=expires_at,
            source=source,
            market=self._market_name(
                market
            ),
            reasons=reasons,
            confirmations=confirmations,
            indicators=indicators,
            chart_path=None,
            metadata=metadata,
            winrate_trades=trades,
            winrate_wins=wins,
            winrate_losses=losses,
            winrate_draws=draws,
        )

    # ============================================================
    # DATA PREPARATION
    # ============================================================

    @staticmethod
    def _prepare_dataframe(
        df: pd.DataFrame,
    ) -> pd.DataFrame | None:
        try:
            result = df.copy()

            required = (
                "datetime",
                "open",
                "high",
                "low",
                "close",
                "volume",
            )

            for column in required:
                if column not in result.columns:
                    return None

            result["datetime"] = pd.to_datetime(
                result["datetime"],
                utc=True,
                errors="coerce",
            )

            for column in (
                "open",
                "high",
                "low",
                "close",
                "volume",
            ):
                result[column] = pd.to_numeric(
                    result[column],
                    errors="coerce",
                )

            result = result.dropna(
                subset=[
                    "datetime",
                    "open",
                    "high",
                    "low",
                    "close",
                ]
            )

            result = (
                result
                .sort_values(
                    "datetime"
                )
                .drop_duplicates(
                    subset=[
                        "datetime"
                    ],
                    keep="last",
                )
                .reset_index(
                    drop=True
                )
            )

            if len(result) < 80:
                return None

            result = calculate_indicators(
                result
            )

            return result

        except Exception:
            return None

    # ============================================================
    # CONFIDENCE
    # ============================================================

    @staticmethod
    def _calculate_confidence(
        current_confidence: float,
        historical_winrate: float,
        confirmations: int,
    ) -> float:
        """
        Confidence текущей ситуации.

        Не делаем искусственный разгон значения.
        Историческая статистика и текущие подтверждения
        влияют на итог.
        """

        current = max(
            0.0,
            min(
                100.0,
                float(
                    current_confidence
                    or 0.0
                ),
            ),
        )

        historical = max(
            0.0,
            min(
                100.0,
                float(
                    historical_winrate
                    or 0.0
                ),
            ),
        )

        # Текущая техническая оценка — основной компонент.
        # Историческая статистика — второй.
        confidence = (
            current * 0.60
            + historical * 0.40
        )

        # Небольшое преимущество за дополнительные
        # подтверждения сверх минимальных.
        extra_confirmations = max(
            0,
            confirmations - 4,
        )

        confidence += min(
            5.0,
            extra_confirmations * 1.5,
        )

        return max(
            0.0,
            min(
                100.0,
                confidence,
            ),
        )

    # ============================================================
    # QUALITY
    # ============================================================

    @staticmethod
    def _calculate_quality(
        current_confidence: float,
        historical_winrate: float,
        effective_winrate: float,
        confirmations: int,
        trades: int,
    ) -> float:
        """
        Итоговое качество.

        Чем сильнее текущая ситуация и чем лучше
        историческая статистика, тем выше score.

        Дополнительные сделки повышают качество,
        но не могут искусственно превратить плохой
        исторический результат в хороший.
        """

        current_component = max(
            0.0,
            min(
                100.0,
                float(
                    current_confidence
                    or 0.0
                ),
            ),
        )

        historical_component = max(
            0.0,
            min(
                100.0,
                float(
                    historical_winrate
                    or 0.0
                ),
            ),
        )

        effective_component = max(
            0.0,
            min(
                100.0,
                float(
                    effective_winrate
                    or 0.0
                ),
            ),
        )

        confirmation_component = (
            min(
                confirmations,
                7,
            )
            / 7.0
            * 100.0
        )

        # Небольшой бонус за размер выборки.
        if trades >= 30:
            sample_bonus = 5.0
        elif trades >= 20:
            sample_bonus = 3.0
        elif trades >= 10:
            sample_bonus = 1.0
        else:
            sample_bonus = 0.0

        quality = (
            current_component * 0.30
            + historical_component * 0.25
            + effective_component * 0.25
            + confirmation_component * 0.20
            + sample_bonus
        )

        return max(
            0.0,
            min(
                100.0,
                quality,
            ),
        )

    # ============================================================
    # REASONS
    # ============================================================

    @staticmethod
    def _build_reasons(
        reasons: list[str],
        direction: str,
        historical_winrate: float,
        confirmations: int,
        trades: int,
    ) -> list[str]:
        result = list(
            reasons
        )

        direction_text = (
            "ВВЕРХ"
            if direction == "UP"
            else "ВНИЗ"
        )

        result.insert(
            0,
            f"Направление: {direction_text}",
        )

        result.append(
            f"Исторический WINRATE: "
            f"{historical_winrate:.1f}%"
        )

        result.append(
            f"Подтверждения: "
            f"{confirmations}/7"
        )

        result.append(
            f"Историческая выборка: "
            f"{trades} сделок"
        )

        return result

    # ============================================================
    # INDICATORS
    # ============================================================

    @staticmethod
    def _clean_indicators(
        values: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for key, value in values.items():

            if value is None:
                continue

            if isinstance(
                value,
                bool,
            ):
                result[key] = value
                continue

            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass

            try:
                result[key] = round(
                    float(value),
                    8,
                )
            except (
                TypeError,
                ValueError,
            ):
                try:
                    result[key] = value.item()
                except Exception:
                    result[key] = str(
                        value
                    )

        return result

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            result = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if pd.isna(result):
            return None

        return result

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

        for attribute in (
            "name",
            "market",
            "market_type",
        ):
            value = getattr(
                market,
                attribute,
                None,
            )

            if value:
                return str(
                    value
                )

        return "regular"

    @staticmethod
    def _get_last_candle_time(
        df: pd.DataFrame,
    ) -> str | None:
        if (
            df is None
            or df.empty
            or "datetime" not in df.columns
        ):
            return None

        try:
            value = pd.to_datetime(
                df.iloc[-1]["datetime"],
                utc=True,
            )

            return value.isoformat()

        except Exception:
            return None
