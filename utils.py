from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation


def utc_now() -> datetime:
    return datetime.utcnow()


def ensure_float(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean cannot be converted to price")

    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(
            f"Cannot convert value to float: {value!r}"
        ) from exc


def format_pair(pair: str) -> str:
    return pair.replace("_", "/").upper().strip()


def direction_text(direction: str) -> str:
    direction = direction.upper()

    if direction == "UP":
        return "🟢 ВВЕРХ / CALL"

    if direction == "DOWN":
        return "🔴 ВНИЗ / PUT"

    return direction


def format_confidence(value: float) -> str:
    return f"{value:.1f}%"


def format_price(value: float) -> str:
    if value >= 100:
        return f"{value:.3f}"

    if value >= 10:
        return f"{value:.4f}"

    return f"{value:.5f}"


def format_datetime(value: datetime) -> str:
    return value.strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def safe_username(
    username: str | None,
) -> str:
    if not username:
        return "нет username"

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

    if value not in {"UP", "DOWN"}:
        raise ValueError(
            f"Unsupported direction: {direction}"
        )

    return value
