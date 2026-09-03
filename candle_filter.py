from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd


@dataclass(slots=True)
class CandleFilterSettings:
    enabled: bool = False
    ignored_last_candles: int = 0
    expires_at: datetime | None = None


class CandleFilter:
    def __init__(self) -> None:
        self._settings = CandleFilterSettings()

    def configure(
        self,
        ignored_last_candles: int,
        duration_minutes: int,
    ) -> CandleFilterSettings:
        ignored_last_candles = max(
            0,
            int(ignored_last_candles),
        )

        duration_minutes = max(
            1,
            int(duration_minutes),
        )

        if ignored_last_candles <= 0:
            self.disable()
            return self.get_settings()

        expires_at = datetime.now(
            timezone.utc
        ) + timedelta(
            minutes=duration_minutes
        )

        self._settings = CandleFilterSettings(
            enabled=True,
            ignored_last_candles=ignored_last_candles,
            expires_at=expires_at,
        )

        return self.get_settings()

    def disable(self) -> None:
        self._settings = CandleFilterSettings()

    def get_settings(self) -> CandleFilterSettings:
        settings = CandleFilterSettings(
            enabled=self._settings.enabled,
            ignored_last_candles=self._settings.ignored_last_candles,
            expires_at=self._settings.expires_at,
        )

        if (
            settings.enabled
            and settings.expires_at is not None
            and settings.expires_at
            <= datetime.now(timezone.utc)
        ):
            self.disable()
            return CandleFilterSettings()

        return settings

    def apply(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        settings = self.get_settings()

        if not settings.enabled:
            return df.copy()

        count = settings.ignored_last_candles

        if count <= 0:
            return df.copy()

        if len(df) <= count:
            return df.iloc[0:0].copy()

        return df.iloc[:-count].copy()
