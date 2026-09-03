from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo


UTC = timezone.utc
LOCAL_TZ = ZoneInfo("Europe/Moscow")


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_now() -> datetime:
    return utc_now().astimezone(
        LOCAL_TZ
    )


def ensure_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(
            tzinfo=UTC
        )

    return value.astimezone(UTC)


def to_local(
    value: datetime,
) -> datetime:
    return ensure_utc(value).astimezone(
        LOCAL_TZ
    )


def calculate_expiry(
    created_at: datetime,
    expiry_minutes: int,
) -> datetime:
    created = ensure_utc(
        created_at
    )

    minutes = max(
        1,
        int(expiry_minutes),
    )

    return created + timedelta(
        minutes=minutes
    )


def normalize_expiry(
    expiry_minutes: int,
) -> int:
    return max(
        1,
        min(
            20,
            int(expiry_minutes),
        ),
    )


def expiry_values() -> tuple[int, ...]:
    return tuple(
        range(1, 21)
    )


def format_local_time(
    value: datetime | None,
) -> str:
    if value is None:
        return "—"

    return to_local(value).strftime(
        "%H:%M:%S"
    )


def format_local_datetime(
    value: datetime | None,
) -> str:
    if value is None:
        return "—"

    return to_local(value).strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def is_expired(
    value: datetime | None,
) -> bool:
    if value is None:
        return False

    return ensure_utc(value) <= utc_now()


def seconds_until(
    value: datetime,
) -> float:
    delta = (
        ensure_utc(value)
        - utc_now()
    )

    return max(
        0.0,
        delta.total_seconds(),
    )


def floor_to_minute(
    value: datetime,
) -> datetime:
    value = ensure_utc(value)

    return value.replace(
        second=0,
        microsecond=0,
    )


def ceil_to_minute(
    value: datetime,
) -> datetime:
    value = ensure_utc(value)

    floored = floor_to_minute(
        value
    )

    if value == floored:
        return floored

    return floored + timedelta(
        minutes=1
    )


def next_minute(
    value: datetime | None = None,
) -> datetime:
    if value is None:
        value = utc_now()

    return ceil_to_minute(value)


def next_n_minute_mark(
    minutes: int,
    value: datetime | None = None,
) -> datetime:
    """
    Возвращает ближайшую отметку времени,
    кратную заданному количеству минут.

    Например, для 5 минут:
    12:01 -> 12:05
    12:05 -> 12:10
    """
    minutes = max(
        1,
        int(minutes),
    )

    if value is None:
        value = utc_now()

    value = ensure_utc(value)

    base = value.replace(
        second=0,
        microsecond=0,
    )

    remainder = base.minute % minutes

    if remainder == 0 and value == base:
        return base

    add_minutes = (
        minutes - remainder
    )

    if remainder == 0:
        add_minutes = minutes

    return base + timedelta(
        minutes=add_minutes
    )


def next_20_minute_mark(
    value: datetime | None = None,
) -> datetime:
    return next_n_minute_mark(
        20,
        value,
    )
