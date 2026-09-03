from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import (
    MAX_EXPIRY_MINUTES,
    MIN_EXPIRY_MINUTES,
    TIMEZONE,
)


UTC = timezone.utc
LOCAL_TZ = ZoneInfo(TIMEZONE)


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_now() -> datetime:
    return datetime.now(LOCAL_TZ)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def to_local(value: datetime) -> datetime:
    return ensure_utc(value).astimezone(
        LOCAL_TZ
    )


def calculate_expiry(
    created_at: datetime,
    expiry_minutes: int,
) -> datetime:
    expiry_minutes = normalize_expiry(
        expiry_minutes
    )

    return ensure_utc(
        created_at
    ) + timedelta(
        minutes=expiry_minutes
    )


def normalize_expiry(
    value: int,
) -> int:
    return max(
        MIN_EXPIRY_MINUTES,
        min(
            MAX_EXPIRY_MINUTES,
            int(value),
        ),
    )


def expiry_values() -> tuple[int, ...]:
    return tuple(
        range(
            MIN_EXPIRY_MINUTES,
            MAX_EXPIRY_MINUTES + 1,
        )
    )


def format_local_time(
    value: datetime,
) -> str:
    return to_local(value).strftime(
        "%H:%M"
    )


def format_local_datetime(
    value: datetime,
) -> str:
    return to_local(value).strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def is_expired(
    value: datetime,
    now: datetime | None = None,
) -> bool:
    current = (
        ensure_utc(now)
        if now is not None
        else utc_now()
    )

    return ensure_utc(value) <= current
