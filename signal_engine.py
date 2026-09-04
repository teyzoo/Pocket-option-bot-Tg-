from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pandas as pd

from backtest import run_backtest
from config import (
    MAX_EXPIRY_MINUTES,
    MIN_CANDLES,
    MIN_SIGNAL_CONFIDENCE,
    MIN_SIGNAL_CONFIRMATIONS,
    MIN_SIGNAL_QUALITY,
    MIN_SIGNAL_WINRATE,
)
from indicators import calculate_indicators
from models import SignalCandidate
from strategy_engine import StrategyAnalysis, StrategyEngine


logger = logging.getLogger("signal_engine")


class SignalEngine:

    def __init__(self) -> None:
        self.strategy_engine = StrategyEngine()

    @staticmethod
    def _prepare(
        df: pd.DataFrame,
    ) -> Optional[pd.DataFrame]:

        if df is None or df.empty:
            return None

        data = df.copy()

        required = {
            "open",
            "high",
            "low",
            "close",
        }

        if not required.issubset(data.columns):
            return None

        if "datetime" in data.columns:
            data["datetime"] = pd.to_datetime(
                data["datetime"],
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

        if "datetime" in data.columns:
            data = data.sort_values(
                "datetime"
            )

        data = data.reset_index(
            drop=True
        )

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
            data.columns
        ):
            data = calculate_indicators(
                data
            )

        if len(data) < MIN_CANDLES:
            return None

        return data

    @staticmethod
    def _quality(
        strategy: StrategyAnalysis,
        winrate: float,
    ) -> float:

        confirmation_component = min(
            100.0,
            strategy.confirmations
            / 7.0
            * 100.0,
        )

        value = (
            strategy.confidence * 0.35
            + min(
                100.0,
                max(0.0, winrate),
            ) * 0.50
            + confirmation_component * 0.15
        )

        return round(
            min(100.0, value),
            2,
        )

    @staticmethod
    def _build_candidate(
        pair: str,
        market: str,
        data: pd.DataFrame,
        strategy: StrategyAnalysis,
        expiry: int,
        result: Any,
        source: str,
        quality: float,
    ) -> SignalCandidate:

        row = data.iloc[-1]

        entry_price = float(
            row["close"]
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
        ]

        for name in indicator_names:

            if name not in row:
                continue

            try:
                value = row[name]

                if not pd.isna(value):
                    indicators[name] = float(
                        value
                    )
            except Exception:
                continue

        strategy_details = []

        for item in strategy.strategies:

            strategy_details.append(
                {
                    "name": item.name,
                    "direction": item.direction,
                    "score": item.score,
                    "confidence": item.confidence,
                    "reason": item.reason,
                }
            )

        metadata = {
            "strategy_engine": True,
            "strategy_score_up": strategy.score_up,
            "strategy_score_down": strategy.score_down,
            "strategy_confidence": strategy.confidence,
            "strategy_confirmations": strategy.confirmations,
            "strategies": strategy_details,
            "historical_total": result.total,
            "historical_wins": result.wins,
            "historical_losses": result.losses,
            "historical_draws": result.draws,
            "historical_winrate": result.winrate,
            "minimum_winrate": MIN_SIGNAL_WINRATE,
            "minimum_trades": 10,
        }

        return SignalCandidate(
            pair=pair,
            direction=strategy.direction,
            expiry_minutes=expiry,
            confidence=round(
                strategy.confidence,
                2,
            ),
            quality=quality,
            winrate=round(
                result.winrate,
                2,
            ),
            entry_price=entry_price,
            created_at=created_at,
            expires_at=expires_at,
            source=source,
            market=market,
            reasons=strategy.reasons,
            confirmations=strategy.confirmations,
            indicators=indicators,
            chart_path=None,
            metadata=metadata,
            winrate_trades=result.decisive_trades,
            wins=result.wins,
            losses=result.losses,
            draws=result.draws,
        )

    def _validate_strategy(
        self,
        strategy: StrategyAnalysis,
    ) -> bool:

        if strategy.direction is None:
            return False

        if (
            strategy.confirmations
            < MIN_SIGNAL_CONFIRMATIONS
        ):
            return False

        if (
            strategy.confidence
            < MIN_SIGNAL_CONFIDENCE
        ):
            return False

        return True

    def _run_expiry_backtests(
        self,
        data: pd.DataFrame,
        direction: str,
    ) -> Dict[int, Any]:

        results: Dict[int, Any] = {}

        for expiry in range(
            1,
            MAX_EXPIRY_MINUTES + 1,
        ):

            try:
                result = run_backtest(
                    data,
                    expiry_minutes=expiry,
                    direction=direction,
                )
            except Exception:
                logger.exception(
                    "Backtest failed: expiry=%s",
                    expiry,
                )
                continue

            if result.decisive_trades < 10:
                continue

            if result.winrate < MIN_SIGNAL_WINRATE:
                continue

            results[expiry] = result

        return results

    def analyze(
        self,
        pair: str,
        market: str,
        df: pd.DataFrame,
        expiry_minutes: int,
        source: str = "manual",
    ) -> Optional[SignalCandidate]:

        try:
            expiry = int(
                expiry_minutes
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if not (
            1
            <= expiry
            <= MAX_EXPIRY_MINUTES
        ):
            return None

        data = self._prepare(df)

        if data is None:
            return None

        strategy = (
            self.strategy_engine.analyze(
                data
            )
        )

        if not self._validate_strategy(
            strategy
        ):
            return None

        try:
            result = run_backtest(
                data,
                expiry_minutes=expiry,
                direction=strategy.direction,
            )
        except Exception:
            logger.exception(
                "Backtest failed: pair=%s expiry=%s",
                pair,
                expiry,
            )
            return None

        if result.decisive_trades < 10:
            return None

        if result.winrate < MIN_SIGNAL_WINRATE:
            return None

        quality = self._quality(
            strategy,
            result.winrate,
        )

        if quality < MIN_SIGNAL_QUALITY:
            return None

        candidate = self._build_candidate(
            pair=pair,
            market=market,
            data=data,
            strategy=strategy,
            expiry=expiry,
            result=result,
            source=source,
            quality=quality,
        )

        logger.info(
            "%s | SIGNAL | %s | %sm | "
            "strategy=%.2f | quality=%.2f | "
            "winrate=%.2f | trades=%s",
            pair,
            strategy.direction,
            expiry,
            strategy.confidence,
            quality,
            result.winrate,
            result.decisive_trades,
        )

        return candidate

    def find_best(
        self,
        candidates,
    ) -> Optional[SignalCandidate]:

        valid = [
            item
            for item in candidates
            if item is not None
        ]

        if not valid:
            return None

        valid.sort(
            key=lambda item: (
                float(item.quality),
                float(item.winrate),
                float(item.confidence),
                int(item.confirmations),
                int(item.winrate_trades),
            ),
            reverse=True,
        )

        return valid[0]

    def analyze_any_time(
        self,
        pair: str,
        market: str,
        df: pd.DataFrame,
        source: str = "manual",
    ) -> Optional[SignalCandidate]:

        data = self._prepare(df)

        if data is None:
            return None

        strategy = (
            self.strategy_engine.analyze(
                data
            )
        )

        if not self._validate_strategy(
            strategy
        ):
            return None

        results = self._run_expiry_backtests(
            data,
            strategy.direction,
        )

        candidates = []

        for expiry, result in results.items():

            quality = self._quality(
                strategy,
                result.winrate,
            )

            if quality < MIN_SIGNAL_QUALITY:
                continue

            candidate = self._build_candidate(
                pair=pair,
                market=market,
                data=data,
                strategy=strategy,
                expiry=expiry,
                result=result,
                source=source,
                quality=quality,
            )

            candidates.append(
                candidate
            )

        best = self.find_best(
            candidates
        )

        if best is None:
            logger.info(
                "%s | ANY TIME | no valid candidate",
                pair,
            )

        return best

    def analyze_all_expiries(
        self,
        pair: str,
        market: str,
        df: pd.DataFrame,
        source: str = "manual",
    ):

        data = self._prepare(df)

        if data is None:
            return []

        strategy = (
            self.strategy_engine.analyze(
                data
            )
        )

        if not self._validate_strategy(
            strategy
        ):
            return []

        results = self._run_expiry_backtests(
            data,
            strategy.direction,
        )

        candidates = []

        for expiry, result in results.items():

            quality = self._quality(
                strategy,
                result.winrate,
            )

            if quality < MIN_SIGNAL_QUALITY:
                continue

            candidates.append(
                self._build_candidate(
                    pair=pair,
                    market=market,
                    data=data,
                    strategy=strategy,
                    expiry=expiry,
                    result=result,
                    source=source,
                    quality=quality,
                )
            )

        return candidates
