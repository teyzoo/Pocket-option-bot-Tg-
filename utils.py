from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_pair(pair: str) -> str:
    value = pair.strip().upper()

    if "/" in value:
        return value

    if len(value) == 6:
        return f"{value[:3]}/{value[3:]}"

    return value


def direction_text(direction: str) -> str:
    value = direction.upper()

    if value == "UP":
        return "🟢 ВВЕРХ ⬆️"

    if value == "DOWN":
        return "🔴 ВНИЗ ⬇️"

    return value


def format_confidence(value: float) -> str:
    return f"{value:.1f}%"


def format_price(
    value: float,
    decimals: int = 5,
) -> str:
    return f"{value:.{decimals}f}"


def format_datetime(
    value: datetime,
) -> str:
    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    ).strftime(
        "%H:%M:%S UTC"
    )
