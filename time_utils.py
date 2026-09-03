from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import (
    DEFAULT_EXPIRY_MINUTES,
    MAX_EXPIRY_MINUTES,
    MIN_EXPIRY_MINUTES,
    TIMEZONE,
)


UTC = ZoneInfo("UTC")
LOCAL_TZ = ZoneInfo(TIMEZONE)


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_now() -> datetime:
    return datetime.now(LOCAL_TZ)


def ensure_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def to_local(
    value: datetime,
) -> datetime:
    return ensure_utc(value).astimezone(
        LOCAL_TZ
    )


def calculate_expiry(
    expiry_minutes: int,
    from_time: datetime | None = None,
) -> datetime:
    expiry_minutes = normalize_expiry(
        expiry_minutes
    )

    if from_time is None:
        from_time = utc_now()

    return ensure_utc(from_time) + timedelta(
        minutes=expiry_minutes
    )


def normalize_expiry(
    value: str | int,
) -> int:
    if isinstance(value, str):
        if value.lower().strip() == "any":
            return DEFAULT_EXPIRY_MINUTES

        value = int(value)

    return max(
        MIN_EXPIRY_MINUTES,
        min(
            MAX_EXPIRY_MINUTES,
            int(value),
        ),
    )


def format_local_time(
    value: datetime,
) -> str:
    return to_local(value).strftime(
        "%H:%M:%S"
    )


def format_local_datetime(
    value: datetime,
) -> str:
    return to_local(value).strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def expiry_values() -> list[int]:
    return list(
        range(
            MIN_EXPIRY_MINUTES,
            MAX_EXPIRY_MINUTES + 1,
        )
    )
