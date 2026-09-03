from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd


@dataclass(slots=True)
class CandleFilterSettings:
    enabled: bool = False
    ignored_last_candles: int = 0
    expires_at: datetime | None = None

    def is_active(self, now: datetime) -> bool:
        if not self.enabled:
            return False

        if self.expires_at is None:
            return True

        return now < self.expires_at


class CandleFilter:
    """
    Временное исключение последних свечей из анализа.

    Важно:
    реальные рыночные данные не удаляются.
    Мы только создаём копию DataFrame без указанного
    количества последних свечей для аналитики.
    """

    def __init__(self) -> None:
        self.settings = CandleFilterSettings()

    def configure(
        self,
        enabled: bool,
        ignored_last_candles: int,
        duration_minutes: int | None = None,
    ) -> CandleFilterSettings:
        ignored_last_candles = max(
            0,
            int(ignored_last_candles),
        )

        expires_at = None

        if duration_minutes is not None:
            duration_minutes = max(
                1,
                int(duration_minutes),
            )

            expires_at = datetime.utcnow() + timedelta(
                minutes=duration_minutes
            )

        self.settings = CandleFilterSettings(
            enabled=bool(enabled),
            ignored_last_candles=ignored_last_candles,
            expires_at=expires_at,
        )

        return self.settings

    def disable(self) -> CandleFilterSettings:
        self.settings = CandleFilterSettings(
            enabled=False,
            ignored_last_candles=0,
            expires_at=None,
        )

        return self.settings

    def apply(
        self,
        df: pd.DataFrame,
        now: datetime | None = None,
    ) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        if now is None:
            now = datetime.utcnow()

        if not self.settings.is_active(now):
            return df.copy()

        amount = self.settings.ignored_last_candles

        if amount <= 0:
            return df.copy()

        if amount >= len(df):
            return df.iloc[0:0].copy()

        return df.iloc[:-amount].copy()

    def get_settings(self) -> CandleFilterSettings:
        return self.settings


candle_filter = CandleFilter()
