from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if result != result:
        return None

    return result


def format_pair(pair: str) -> str:
    return pair.replace("_", "/").strip().upper()


def direction_text(direction: str) -> str:
    normalized = direction.upper()

    if normalized == "UP":
        return "🟢 ВВЕРХ"

    if normalized == "DOWN":
        return "🔴 ВНИЗ"

    return normalized


def format_confidence(value: float) -> str:
    return f"{value:.1f}%"


def format_price(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:.3f}"

    if abs(value) >= 10:
        return f"{value:.4f}"

    return f"{value:.5f}"


def format_datetime(
    value: datetime,
) -> str:
    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def safe_username(
    username: str | None,
) -> str:
    if not username:
        return "без username"

    return f"@{username.lstrip('@')}"


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def normalize_direction(
    direction: str,
) -> str:
    value = direction.strip().upper()

    aliases = {
        "CALL": "UP",
        "PUT": "DOWN",
        "BUY": "UP",
        "SELL": "DOWN",
        "ВВЕРХ": "UP",
        "ВНИЗ": "DOWN",
    }

    return aliases.get(
        value,
        value,
    )
