from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd


@dataclass(slots=True)
class CandleFilterSettings:
    enabled: bool = False
    ignored_last_candles: int = 0
    expires_at: datetime | None = None


class CandleFilter:
    def __init__(self) -> None:
        self.settings = CandleFilterSettings()

    def configure(
        self,
        ignored_last_candles: int,
        duration_minutes: int,
    ) -> CandleFilterSettings:
        self.settings = CandleFilterSettings(
            enabled=ignored_last_candles > 0,
            ignored_last_candles=max(
                0,
                ignored_last_candles,
            ),
            expires_at=(
                datetime.utcnow()
                + timedelta(
                    minutes=max(
                        1,
                        duration_minutes,
                    )
                )
            ),
        )

        return self.settings

    def disable(self) -> None:
        self.settings = CandleFilterSettings()

    def active(
        self,
        now: datetime | None = None,
    ) -> bool:
        if not self.settings.enabled:
            return False

        if self.settings.expires_at is None:
            return True

        if now is None:
            now = datetime.utcnow()

        if now >= self.settings.expires_at:
            self.disable()
            return False

        return True

    def apply(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        if not self.active():
            return df.copy()

        amount = self.settings.ignored_last_candles

        if amount <= 0:
            return df.copy()

        if amount >= len(df):
            return df.iloc[0:0].copy()

        return df.iloc[:-amount].copy()


candle_filter = CandleFilter()
