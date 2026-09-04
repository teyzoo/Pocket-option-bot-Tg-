from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv


load_dotenv()


def _get(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip()

    if not value:
        return default

    return value


def _get_required(name: str) -> str:
    value = _get(name)

    if not value:
        raise RuntimeError(
            f"Environment variable {name} is required"
        )

    return value


def _get_int(name: str, default: int) -> int:
    value = _get(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be an integer"
        ) from exc


def _get_float(name: str, default: float) -> float:
    value = _get(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be a number"
        ) from exc


def _get_bool(name: str, default: bool) -> bool:
    value = _get(name)

    if value is None:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def _get_int_list(name: str) -> tuple[int, ...]:
    value = _get(name, "")

    if not value:
        return ()

    result: list[int] = []

    for item in value.split(","):
        item = item.strip()

        if not item:
            continue

        try:
            result.append(int(item))
        except ValueError as exc:
            raise RuntimeError(
                f"Environment variable {name} contains invalid integer: {item}"
            ) from exc

    return tuple(dict.fromkeys(result))


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

BOT_TOKEN: Final[str] = _get_required("BOT_TOKEN")

DATABASE_URL: Final[str] = _get_required("DATABASE_URL")

TWELVE_DATA_API_KEY: Final[str] = _get_required(
    "TWELVE_DATA_API_KEY"
)

ADMIN_IDS: Final[tuple[int, ...]] = _get_int_list(
    "ADMIN_IDS"
)

OWNER_IDS: Final[tuple[int, ...]] = (
    _get_int_list("OWNER_IDS") or ADMIN_IDS
)

HOST: Final[str] = (
    _get("HOST", "0.0.0.0")
    or "0.0.0.0"
)

PORT: Final[int] = _get_int(
    "PORT",
    10000,
)

HEALTH_PATH: Final[str] = (
    _get("HEALTH_PATH", "/health")
    or "/health"
)

TIMEZONE: Final[str] = (
    _get("TIMEZONE", "Europe/Moscow")
    or "Europe/Moscow"
)


# ---------------------------------------------------------------------------
# Signal requirements
# ---------------------------------------------------------------------------

MIN_SIGNAL_WINRATE: Final[float] = max(
    75.0,
    _get_float(
        "MIN_SIGNAL_WINRATE",
        75.0,
    ),
)

MIN_SIGNAL_CONFIDENCE: Final[float] = max(
    75.0,
    _get_float(
        "MIN_SIGNAL_CONFIDENCE",
        75.0,
    ),
)

MIN_SIGNAL_QUALITY: Final[float] = max(
    75.0,
    _get_float(
        "MIN_SIGNAL_QUALITY",
        75.0,
    ),
)

MIN_SIGNAL_CONFIRMATIONS: Final[int] = max(
    3,
    _get_int(
        "MIN_SIGNAL_CONFIRMATIONS",
        3,
    ),
)


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------

MIN_EXPIRY_MINUTES: Final[int] = max(
    1,
    _get_int(
        "MIN_EXPIRY_MINUTES",
        1,
    ),
)

MAX_EXPIRY_MINUTES: Final[int] = min(
    20,
    max(
        MIN_EXPIRY_MINUTES,
        _get_int(
            "MAX_EXPIRY_MINUTES",
            20,
        ),
    ),
)

DEFAULT_EXPIRY_MINUTES: Final[int] = min(
    MAX_EXPIRY_MINUTES,
    max(
        MIN_EXPIRY_MINUTES,
        _get_int(
            "DEFAULT_EXPIRY_MINUTES",
            5,
        ),
    ),
)


# ---------------------------------------------------------------------------
# Market / Twelve Data
# ---------------------------------------------------------------------------

MARKET_INTERVAL: Final[str] = (
    _get(
        "MARKET_INTERVAL",
        "1min",
    )
    or "1min"
)

TWELVE_DATA_BASE_URL: Final[str] = (
    _get(
        "TWELVE_DATA_BASE_URL",
        "https://api.twelvedata.com",
    )
    or "https://api.twelvedata.com"
)

TWELVE_DATA_TIMEOUT_SECONDS: Final[float] = _get_float(
    "TWELVE_DATA_TIMEOUT_SECONDS",
    20.0,
)

TWELVE_DATA_MAX_CANDLES: Final[int] = max(
    100,
    _get_int(
        "TWELVE_DATA_MAX_CANDLES",
        300,
    ),
)

TWELVE_DATA_MIN_CANDLES: Final[int] = max(
    50,
    _get_int(
        "TWELVE_DATA_MIN_CANDLES",
        80,
    ),
)

TWELVE_DATA_MAX_REQUESTS_PER_SCAN: Final[int] = max(
    1,
    _get_int(
        "TWELVE_DATA_MAX_REQUESTS_PER_SCAN",
        8,
    ),
)

TWELVE_DATA_CACHE_SECONDS: Final[int] = max(
    0,
    _get_int(
        "TWELVE_DATA_CACHE_SECONDS",
        45,
    ),
)


# ---------------------------------------------------------------------------
# Scanner candle limits
# ---------------------------------------------------------------------------

MIN_CANDLES_REQUIRED: Final[int] = max(
    50,
    _get_int(
        "MIN_CANDLES_REQUIRED",
        50,
    ),
)

MAX_CANDLES: Final[int] = max(
    MIN_CANDLES_REQUIRED,
    _get_int(
        "MAX_CANDLES",
        200,
    ),
)


# ---------------------------------------------------------------------------
# Automatic signals
# ---------------------------------------------------------------------------

AUTO_SIGNAL_ENABLED: Final[bool] = _get_bool(
    "AUTO_SIGNAL_ENABLED",
    True,
)

AUTO_SIGNAL_INTERVAL_MINUTES: Final[int] = max(
    1,
    _get_int(
        "AUTO_SIGNAL_INTERVAL_MINUTES",
        5,
    ),
)

SIGNAL_COOLDOWN_MINUTES: Final[int] = max(
    0,
    _get_int(
        "SIGNAL_COOLDOWN_MINUTES",
        5,
    ),
)

SIGNAL_DEDUPLICATION_MINUTES: Final[int] = max(
    1,
    _get_int(
        "SIGNAL_DEDUPLICATION_MINUTES",
        15,
    ),
)


# ---------------------------------------------------------------------------
# Result checking
# ---------------------------------------------------------------------------

RESULT_CHECK_INTERVAL_SECONDS: Final[int] = max(
    5,
    _get_int(
        "RESULT_CHECK_INTERVAL_SECONDS",
        30,
    ),
)

RESULT_PRICE_TOLERANCE_SECONDS: Final[int] = max(
    30,
    _get_int(
        "RESULT_PRICE_TOLERANCE_SECONDS",
        120,
    ),
)


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

EMA_FAST: Final[int] = max(
    2,
    _get_int(
        "EMA_FAST",
        9,
    ),
)

EMA_SLOW: Final[int] = max(
    EMA_FAST + 1,
    _get_int(
        "EMA_SLOW",
        21,
    ),
)

EMA_TREND: Final[int] = max(
    EMA_SLOW + 1,
    _get_int(
        "EMA_TREND",
        50,
    ),
)


RSI_PERIOD: Final[int] = max(
    2,
    _get_int(
        "RSI_PERIOD",
        14,
    ),
)


MACD_FAST: Final[int] = max(
    2,
    _get_int(
        "MACD_FAST",
        12,
    ),
)

MACD_SLOW: Final[int] = max(
    MACD_FAST + 1,
    _get_int(
        "MACD_SLOW",
        26,
    ),
)

MACD_SIGNAL: Final[int] = max(
    2,
    _get_int(
        "MACD_SIGNAL",
        9,
    ),
)


BOLLINGER_PERIOD: Final[int] = max(
    2,
    _get_int(
        "BOLLINGER_PERIOD",
        20,
    ),
)

BOLLINGER_STD: Final[float] = max(
    0.1,
    _get_float(
        "BOLLINGER_STD",
        2.0,
    ),
)


STOCHASTIC_PERIOD: Final[int] = max(
    2,
    _get_int(
        "STOCHASTIC_PERIOD",
        14,
    ),
)

STOCHASTIC_SMOOTH: Final[int] = max(
    1,
    _get_int(
        "STOCHASTIC_SMOOTH",
        3,
    ),
)


ATR_PERIOD: Final[int] = max(
    2,
    _get_int(
        "ATR_PERIOD",
        14,
    ),
)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

CHART_ENABLED: Final[bool] = _get_bool(
    "CHART_ENABLED",
    True,
)

CHART_WIDTH: Final[float] = max(
    6.0,
    _get_float(
        "CHART_WIDTH",
        12.0,
    ),
)

CHART_HEIGHT: Final[float] = max(
    4.0,
    _get_float(
        "CHART_HEIGHT",
        8.0,
    ),
)

CHART_DPI: Final[int] = max(
    72,
    _get_int(
        "CHART_DPI",
        120,
    ),
)


# ---------------------------------------------------------------------------
# Candle filter
# ---------------------------------------------------------------------------

CANDLE_FILTER_ENABLED: Final[bool] = _get_bool(
    "CANDLE_FILTER_ENABLED",
    False,
)

CANDLE_FILTER_IGNORED_LAST: Final[int] = max(
    0,
    _get_int(
        "CANDLE_FILTER_IGNORED_LAST",
        0,
    ),
)

CANDLE_FILTER_DURATION_MINUTES: Final[int] = max(
    1,
    _get_int(
        "CANDLE_FILTER_DURATION_MINUTES",
        60,
    ),
)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_POOL_SIZE: Final[int] = max(
    1,
    _get_int(
        "DB_POOL_SIZE",
        5,
    ),
)

DB_MAX_OVERFLOW: Final[int] = max(
    0,
    _get_int(
        "DB_MAX_OVERFLOW",
        5,
    ),
)

DB_POOL_TIMEOUT: Final[int] = max(
    5,
    _get_int(
        "DB_POOL_TIMEOUT",
        30,
    ),
)

DB_POOL_RECYCLE: Final[int] = max(
    60,
    _get_int(
        "DB_POOL_RECYCLE",
        1800,
    ),
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL: Final[str] = (
    _get(
        "LOG_LEVEL",
        "INFO",
    )
    or "INFO"
).upper()


# ---------------------------------------------------------------------------
# Currency pairs
# ---------------------------------------------------------------------------

NORMAL_PAIRS: Final[tuple[str, ...]] = (
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
    "EUR/GBP",
    "EUR/JPY",
    "GBP/JPY",
)


# OTC intentionally remains empty.
# No fake OTC prices or candles are generated.
OTC_PAIRS: Final[tuple[str, ...]] = ()


# ---------------------------------------------------------------------------
# Signal results
# ---------------------------------------------------------------------------

RESULT_PENDING: Final[str] = "pending"
RESULT_WIN: Final[str] = "win"
RESULT_LOSS: Final[str] = "loss"
RESULT_DRAW: Final[str] = "draw"
RESULT_CANCELLED: Final[str] = "cancelled"


# Backward-compatible signal-result aliases.
SIGNAL_RESULT_PENDING: Final[str] = RESULT_PENDING
SIGNAL_RESULT_WIN: Final[str] = RESULT_WIN
SIGNAL_RESULT_LOSS: Final[str] = RESULT_LOSS
SIGNAL_RESULT_DRAW: Final[str] = RESULT_DRAW
SIGNAL_RESULT_CANCELLED: Final[str] = RESULT_CANCELLED


# ---------------------------------------------------------------------------
# User access statuses
# ---------------------------------------------------------------------------

USER_PENDING: Final[str] = "pending"
USER_APPROVED: Final[str] = "approved"
USER_REJECTED: Final[str] = "rejected"
USER_BLACKLISTED: Final[str] = "blacklisted"


# Backward-compatible access aliases.
ACCESS_PENDING: Final[str] = USER_PENDING
ACCESS_APPROVED: Final[str] = USER_APPROVED
ACCESS_REJECTED: Final[str] = USER_REJECTED
ACCESS_BLACKLISTED: Final[str] = USER_BLACKLISTED


# ---------------------------------------------------------------------------
# Market types
# ---------------------------------------------------------------------------

MARKET_REGULAR: Final[str] = "regular"
MARKET_OTC: Final[str] = "otc"


# ---------------------------------------------------------------------------
# Signal sources
# ---------------------------------------------------------------------------

SIGNAL_SOURCE_AUTO: Final[str] = "auto"
SIGNAL_SOURCE_MANUAL: Final[str] = "manual"
SIGNAL_SOURCE_ANALYSIS: Final[str] = "analysis"


# ---------------------------------------------------------------------------
# Signal directions
# ---------------------------------------------------------------------------

DIRECTION_UP: Final[str] = "UP"
DIRECTION_DOWN: Final[str] = "DOWN"


# ---------------------------------------------------------------------------
# Config snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfigSnapshot:
    bot_token: str
    database_url: str
    twelve_data_api_key: str
    admin_ids: tuple[int, ...]
    owner_ids: tuple[int, ...]
    timezone: str
    min_signal_winrate: float
    min_signal_confidence: float
    min_signal_quality: float
    min_signal_confirmations: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is empty"
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is empty"
        )

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is empty"
        )

    if not ADMIN_IDS:
        raise RuntimeError(
            "ADMIN_IDS is empty. Add at least one Telegram administrator ID."
        )

    if not OWNER_IDS:
        raise RuntimeError(
            "OWNER_IDS is empty. Add at least one Telegram owner ID."
        )

    if MIN_EXPIRY_MINUTES > MAX_EXPIRY_MINUTES:
        raise RuntimeError(
            "MIN_EXPIRY_MINUTES cannot exceed MAX_EXPIRY_MINUTES"
        )

    if DEFAULT_EXPIRY_MINUTES < MIN_EXPIRY_MINUTES:
        raise RuntimeError(
            "DEFAULT_EXPIRY_MINUTES is below MIN_EXPIRY_MINUTES"
        )

    if DEFAULT_EXPIRY_MINUTES > MAX_EXPIRY_MINUTES:
        raise RuntimeError(
            "DEFAULT_EXPIRY_MINUTES exceeds MAX_EXPIRY_MINUTES"
        )

    if TWELVE_DATA_MIN_CANDLES > TWELVE_DATA_MAX_CANDLES:
        raise RuntimeError(
            "TWELVE_DATA_MIN_CANDLES cannot exceed TWELVE_DATA_MAX_CANDLES"
        )

    if MIN_CANDLES_REQUIRED < 50:
        raise RuntimeError(
            "MIN_CANDLES_REQUIRED cannot be below 50"
        )

    if MAX_CANDLES < MIN_CANDLES_REQUIRED:
        raise RuntimeError(
            "MAX_CANDLES cannot be below MIN_CANDLES_REQUIRED"
        )


validate_config()


# ---------------------------------------------------------------------------
# Global config snapshot
# ---------------------------------------------------------------------------

CONFIG = ConfigSnapshot(
    bot_token=BOT_TOKEN,
    database_url=DATABASE_URL,
    twelve_data_api_key=TWELVE_DATA_API_KEY,
    admin_ids=ADMIN_IDS,
    owner_ids=OWNER_IDS,
    timezone=TIMEZONE,
    min_signal_winrate=MIN_SIGNAL_WINRATE,
    min_signal_confidence=MIN_SIGNAL_CONFIDENCE,
    min_signal_quality=MIN_SIGNAL_QUALITY,
    min_signal_confirmations=MIN_SIGNAL_CONFIRMATIONS,
)
