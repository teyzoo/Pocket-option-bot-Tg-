from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from settings_service import (
    delete_setting,
    get_json_setting,
    set_json_setting,
)
from time_utils import (
    ensure_utc,
    utc_now,
)


CANDLE_FILTER_SETTING_KEY = "candle_filter"


@dataclass(slots=True)
class CandleFilterSettings:
    enabled: bool = False
    ignored_last_candles: int = 0
    expires_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        if not self.enabled:
            return False

        if self.ignored_last_candles <= 0:
            return False

        if self.expires_at is None:
            return True

        return ensure_utc(self.expires_at) > utc_now()


class CandleFilter:
    """
    Временное исключение последних свечей из анализа.

    ВАЖНО:
    - рыночные данные не удаляются;
    - база данных рынка не изменяется;
    - исключаются только свечи, передаваемые в анализ;
    - после окончания срока фильтр автоматически перестаёт действовать.
    """

    async def get_settings(self) -> CandleFilterSettings:
        raw = await get_json_setting(
            CANDLE_FILTER_SETTING_KEY,
            default=None,
        )

        if not isinstance(raw, dict):
            return CandleFilterSettings()

        enabled = bool(raw.get("enabled", False))

        try:
            count = int(
                raw.get(
                    "ignored_last_candles",
                    0,
                )
            )
        except (TypeError, ValueError):
            count = 0

        expires_raw = raw.get("expires_at")

        expires_at: datetime | None = None

        if expires_raw:
            try:
                if isinstance(expires_raw, datetime):
                    expires_at = ensure_utc(expires_raw)
                else:
                    expires_at = ensure_utc(
                        datetime.fromisoformat(
                            str(expires_raw)
                        )
                    )
            except Exception:
                expires_at = None

        settings = CandleFilterSettings(
            enabled=enabled,
            ignored_last_candles=max(0, count),
            expires_at=expires_at,
        )

        if (
            settings.enabled
            and settings.expires_at is not None
            and settings.expires_at <= utc_now()
        ):
            await self.disable(updated_by=None)
            return CandleFilterSettings()

        return settings

    async def configure(
        self,
        ignored_last_candles: int,
        duration_minutes: int,
        updated_by: int | None = None,
    ) -> CandleFilterSettings:
        count = max(
            0,
            int(ignored_last_candles),
        )

        duration = max(
            1,
            int(duration_minutes),
        )

        if count <= 0:
            return await self.disable(
                updated_by=updated_by
            )

        expires_at = (
            utc_now()
            + timedelta(minutes=duration)
        )

        value = {
            "enabled": True,
            "ignored_last_candles": count,
            "expires_at": expires_at.isoformat(),
        }

        await set_json_setting(
            key=CANDLE_FILTER_SETTING_KEY,
            value=value,
            updated_by=updated_by,
            expires_at=expires_at,
        )

        return CandleFilterSettings(
            enabled=True,
            ignored_last_candles=count,
            expires_at=expires_at,
        )

    async def disable(
        self,
        updated_by: int | None = None,
    ) -> CandleFilterSettings:
        await delete_setting(
            CANDLE_FILTER_SETTING_KEY
        )

        return CandleFilterSettings()

    async def apply(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        if df is None:
            return df

        if df.empty:
            return df.copy()

        settings = await self.get_settings()

        if not settings.is_active:
            return df.copy()

        count = settings.ignored_last_candles

        if count <= 0:
            return df.copy()

        if len(df) <= count:
            return df.iloc[0:0].copy()

        return df.iloc[:-count].copy()

    async def status_text(self) -> str:
        settings = await self.get_settings()

        if not settings.is_active:
            return "ВЫКЛ"

        expires = (
            settings.expires_at.isoformat()
            if settings.expires_at
            else "без срока"
        )

        return (
            f"ВКЛ • исключено: "
            f"{settings.ignored_last_candles} • "
            f"до: {expires}"
        )


# ---------------------------------------------------------------------------
# Обратная совместимость
# ---------------------------------------------------------------------------
#
# signal_scanner.py импортирует:
#
#     from candle_filter import candle_filter
#
# Поэтому оставляем совместимую функцию.
#
# Функция использует тот же CandleFilter и не меняет существующую логику.
#

_candle_filter_instance = CandleFilter()


async def candle_filter(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Применяет текущий временный фильтр свечей.

    Совместимый функциональный интерфейс для старого кода.
    """
    return await _candle_filter_instance.apply(df)


# Удобный доступ к экземпляру фильтра для нового кода.
candle_filter_service = _candle_filter_instance
