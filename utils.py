from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from time_utils import (
    format_local_datetime,
    ensure_utc,
    utc_now,
)


def ensure_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default

        result = float(value)

        if result != result:
            return default

        return result
    except (
        TypeError,
        ValueError,
    ):
        return default


def ensure_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        if value is None:
            return default

        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


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


def format_pair(
    pair: str | None,
) -> str:
    if not pair:
        return "—"

    value = str(pair).strip().upper()

    if "/" in value:
        return value

    if len(value) == 6:
        return f"{value[:3]}/{value[3:]}"

    return value


def normalize_pair(
    pair: str,
) -> str:
    return (
        str(pair)
        .strip()
        .upper()
        .replace(
            "-",
            "/",
        )
        .replace(
            "_",
            "/",
        )
    )


def direction_text(
    direction: str | None,
) -> str:
    if not direction:
        return "—"

    normalized = (
        str(direction)
        .strip()
        .upper()
    )

    mapping = {
        "UP": "🟢 UP",
        "CALL": "🟢 UP",
        "BUY": "🟢 UP",
        "LONG": "🟢 UP",
        "DOWN": "🔴 DOWN",
        "PUT": "🔴 DOWN",
        "SELL": "🔴 DOWN",
        "SHORT": "🔴 DOWN",
    }

    return mapping.get(
        normalized,
        normalized,
    )


def normalize_direction(
    direction: str,
) -> str:
    normalized = (
        str(direction)
        .strip()
        .upper()
    )

    if normalized in {
        "UP",
        "CALL",
        "BUY",
        "LONG",
    }:
        return "UP"

    if normalized in {
        "DOWN",
        "PUT",
        "SELL",
        "SHORT",
    }:
        return "DOWN"

    return normalized


def format_confidence(
    value: float | int | None,
) -> str:
    number = ensure_float(
        value
    )

    return f"{number:.2f}%"


def format_price(
    value: float | int | None,
    decimals: int | None = None,
) -> str:
    if value is None:
        return "—"

    number = ensure_float(
        value
    )

    if decimals is None:
        if abs(number) >= 100:
            decimals = 2
        elif abs(number) >= 10:
            decimals = 3
        elif abs(number) >= 1:
            decimals = 4
        else:
            decimals = 5

    return f"{number:.{decimals}f}"


def format_datetime(
    value: datetime | None,
) -> str:
    return format_local_datetime(
        value
    )


def safe_username(
    username: str | None,
) -> str:
    if not username:
        return "нет username"

    username = str(
        username
    ).strip()

    username = username.lstrip("@")

    if not username:
        return "нет username"

    return "@" + escape(
        username
    )


def safe_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return escape(
        str(value)
    )


def percentage(
    numerator: int | float,
    denominator: int | float,
) -> float:
    denominator = ensure_float(
        denominator
    )

    if denominator <= 0:
        return 0.0

    return (
        ensure_float(numerator)
        / denominator
        * 100.0
    )


def utc_timestamp(
    value: datetime | None = None,
) -> float:
    if value is None:
        value = utc_now()

    return ensure_utc(
        value
    ).timestamp()


def age_seconds(
    value: datetime,
) -> float:
    return max(
        0.0,
        (
            utc_now()
            - ensure_utc(value)
        ).total_seconds(),
    )


def truncate(
    text: str,
    max_length: int,
) -> str:
    max_length = max(
        1,
        int(max_length),
    )

    if len(text) <= max_length:
        return text

    return (
        text[: max_length - 1]
        + "…"
    )


def bool_text(
    value: bool,
) -> str:
    return "ВКЛ" if value else "ВЫКЛ"
