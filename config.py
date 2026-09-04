from __future__ import annotations

import os
from typing import Final


# ============================================================
# HELPERS
# ============================================================

def _get_str(name: str, default: str = "") -> str:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip().lower()

    if value in {"1", "true", "yes", "y", "on", "да"}:
        return True

    if value in {"0", "false", "no", "n", "off", "нет"}:
        return False

    return default


def _get_list(
    name: str,
    default: list[str],
) -> list[str]:
    value = os.getenv(name)

    if value is None or not value.strip():
        return list(default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# ============================================================
# APPLICATION
# ============================================================

APP_NAME: Final[str] = _get_str(
    "APP_NAME",
    "Pocket Option Signal Bot",
)

APP_ENV: Final[str] = _get_str(
    "APP_ENV",
    "production",
)

DEBUG: Final[bool] = _get_bool(
    "DEBUG",
    False,
)


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN: Final[str] = _get_str(
    "BOT_TOKEN",
)

if not BOT_TOKEN:
    raise RuntimeError(
        "Environment variable BOT_TOKEN is required"
    )


# ============================================================
# ADMINS
# ============================================================

def _parse_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")

    if not raw.strip():
        return []

    result: list[int] = []

    for item in raw.split(","):
        item = item.strip()

        if not item:
            continue

        try:
            result.append(int(item))
        except ValueError:
            continue

    return result


ADMIN_IDS: Final[list[int]] = _parse_admin_ids()

# Compatibility with admin.py
OWNER_IDS: Final[list[int]] = list(ADMIN_IDS)


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL: Final[str] = _get_str(
    "DATABASE_URL",
)

if not DATABASE_URL:
    raise RuntimeError(
        "Environment variable DATABASE_URL is required"
    )


# SQLAlchemy connection pool settings.
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
        10,
    ),
)

DB_POOL_TIMEOUT: Final[int] = max(
    1,
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


# Compatibility aliases for possible older database code.
DATABASE_POOL_SIZE: Final[int] = DB_POOL_SIZE
DATABASE_MAX_OVERFLOW: Final[int] = DB_MAX_OVERFLOW
DATABASE_POOL_TIMEOUT: Final[int] = DB_POOL_TIMEOUT
DATABASE_POOL_RECYCLE: Final[int] = DB_POOL_RECYCLE


# ============================================================
# TWELVE DATA
# ============================================================

TWELVE_DATA_API_KEY: Final[str] = _get_str(
    "TWELVE_DATA_API_KEY",
)

TWELVE_DATA_BASE_URL: Final[str] = _get_str(
    "TWELVE_DATA_BASE_URL",
    "https://api.twelvedata.com",
)

TWELVE_DATA_TIMEOUT_SECONDS: Final[float] = _get_float(
    "TWELVE_DATA_TIMEOUT_SECONDS",
    20.0,
)

# Compatibility alias.
TWELVE_DATA_TIMEOUT: Final[float] = (
    TWELVE_DATA_TIMEOUT_SECONDS
)

TWELVE_DATA_MAX_CANDLES: Final[int] = max(
    80,
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


# ============================================================
# CANDLES
# ============================================================

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


# ============================================================
# SIGNAL THRESHOLDS
# ============================================================

MIN_SIGNAL_WINRATE: Final[float] = max(
    0.0,
    min(
        100.0,
        _get_float(
            "MIN_SIGNAL_WINRATE",
            75.0,
        ),
    ),
)

MIN_SIGNAL_CONFIDENCE: Final[float] = max(
    0.0,
    min(
        100.0,
        _get_float(
            "MIN_SIGNAL_CONFIDENCE",
            75.0,
        ),
    ),
)

MIN_SIGNAL_QUALITY: Final[float] = max(
    0.0,
    min(
        100.0,
        _get_float(
            "MIN_SIGNAL_QUALITY",
            75.0,
        ),
    ),
)

MIN_SIGNAL_CONFIRMATIONS: Final[int] = max(
    1,
    _get_int(
        "MIN_SIGNAL_CONFIRMATIONS",
        4,
    ),
)


# ============================================================
# INDICATOR SCORES
# ============================================================

EMA_SCORE: Final[float] = _get_float(
    "EMA_SCORE",
    15.0,
)

TREND_SCORE: Final[float] = _get_float(
    "TREND_SCORE",
    15.0,
)

RSI_SCORE: Final[float] = _get_float(
    "RSI_SCORE",
    10.0,
)

MACD_SCORE: Final[float] = _get_float(
    "MACD_SCORE",
    15.0,
)

BOLLINGER_SCORE: Final[float] = _get_float(
    "BOLLINGER_SCORE",
    10.0,
)

STOCHASTIC_SCORE: Final[float] = _get_float(
    "STOCHASTIC_SCORE",
    10.0,
)

PRICE_ACTION_SCORE: Final[float] = _get_float(
    "PRICE_ACTION_SCORE",
    15.0,
)


# ============================================================
# INDICATOR PERIODS
# ============================================================

EMA_FAST_PERIOD: Final[int] = max(
    1,
    _get_int(
        "EMA_FAST_PERIOD",
        9,
    ),
)

EMA_SLOW_PERIOD: Final[int] = max(
    EMA_FAST_PERIOD + 1,
    _get_int(
        "EMA_SLOW_PERIOD",
        21,
    ),
)

EMA_TREND_PERIOD: Final[int] = max(
    EMA_SLOW_PERIOD + 1,
    _get_int(
        "EMA_TREND_PERIOD",
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

MACD_FAST_PERIOD: Final[int] = max(
    1,
    _get_int(
        "MACD_FAST_PERIOD",
        12,
    ),
)

MACD_SLOW_PERIOD: Final[int] = max(
    MACD_FAST_PERIOD + 1,
    _get_int(
        "MACD_SLOW_PERIOD",
        26,
    ),
)

MACD_SIGNAL_PERIOD: Final[int] = max(
    1,
    _get_int(
        "MACD_SIGNAL_PERIOD",
        9,
    ),
)

BB_PERIOD: Final[int] = max(
    2,
    _get_int(
        "BB_PERIOD",
        20,
    ),
)

BB_STDDEV: Final[float] = max(
    0.1,
    _get_float(
        "BB_STDDEV",
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

STOCHASTIC_SMOOTHING: Final[int] = max(
    1,
    _get_int(
        "STOCHASTIC_SMOOTHING",
        3,
    ),
)


# ============================================================
# INDICATOR COMPATIBILITY ALIASES
# ============================================================

EMA_FAST: Final[int] = EMA_FAST_PERIOD
EMA_SLOW: Final[int] = EMA_SLOW_PERIOD
EMA_TREND: Final[int] = EMA_TREND_PERIOD

RSI_LENGTH: Final[int] = RSI_PERIOD

MACD_FAST: Final[int] = MACD_FAST_PERIOD
MACD_SLOW: Final[int] = MACD_SLOW_PERIOD
MACD_SIGNAL: Final[int] = MACD_SIGNAL_PERIOD

BOLLINGER_PERIOD: Final[int] = BB_PERIOD
BOLLINGER_STDDEV: Final[float] = BB_STDDEV

STOCHASTIC_K_PERIOD: Final[int] = STOCHASTIC_PERIOD
STOCHASTIC_D_PERIOD: Final[int] = STOCHASTIC_SMOOTHING


# ============================================================
# AUTOMATIC SIGNALS
# ============================================================

AUTO_SIGNAL_ENABLED: Final[bool] = _get_bool(
    "AUTO_SIGNAL_ENABLED",
    True,
)

AUTO_SIGNAL_INTERVAL_MINUTES: Final[int] = max(
    1,
    min(
        20,
        _get_int(
            "AUTO_SIGNAL_INTERVAL_MINUTES",
            20,
        ),
    ),
)

AUTO_SIGNAL_MINUTES: Final[int] = (
    AUTO_SIGNAL_INTERVAL_MINUTES
)

MAX_AUTO_SCAN_PAIRS: Final[int] = max(
    1,
    _get_int(
        "MAX_AUTO_SCAN_PAIRS",
        8,
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
    0,
    _get_int(
        "SIGNAL_DEDUPLICATION_MINUTES",
        15,
    ),
)


# ============================================================
# EXPIRY
# ============================================================

MIN_EXPIRY_MINUTES: Final[int] = max(
    1,
    _get_int(
        "MIN_EXPIRY_MINUTES",
        1,
    ),
)

MAX_EXPIRY_MINUTES: Final[int] = max(
    MIN_EXPIRY_MINUTES,
    min(
        20,
        _get_int(
            "MAX_EXPIRY_MINUTES",
            20,
        ),
    ),
)


# ============================================================
# RESULT CHECKER
# ============================================================

RESULT_CHECK_INTERVAL_SECONDS: Final[int] = max(
    5,
    _get_int(
        "RESULT_CHECK_INTERVAL_SECONDS",
        30,
    ),
)

# SignalResultChecker imports this exact name.
RESULT_CHECKER_INTERVAL_SECONDS: Final[int] = (
    RESULT_CHECK_INTERVAL_SECONDS
)

RESULT_PRICE_TOLERANCE_SECONDS: Final[int] = max(
    0,
    _get_int(
        "RESULT_PRICE_TOLERANCE_SECONDS",
        120,
    ),
)


# ============================================================
# SIGNAL RESULT CONSTANTS
# ============================================================

RESULT_PENDING: Final[str] = "PENDING"
RESULT_WIN: Final[str] = "WIN"
RESULT_LOSS: Final[str] = "LOSS"
RESULT_DRAW: Final[str] = "DRAW"
RESULT_CANCELLED: Final[str] = "CANCELLED"

# Compatibility aliases.
SIGNAL_RESULT_PENDING: Final[str] = RESULT_PENDING
SIGNAL_RESULT_WIN: Final[str] = RESULT_WIN
SIGNAL_RESULT_LOSS: Final[str] = RESULT_LOSS
SIGNAL_RESULT_DRAW: Final[str] = RESULT_DRAW
SIGNAL_RESULT_CANCELLED: Final[str] = RESULT_CANCELLED


# ============================================================
# MARKET
# ============================================================

DEFAULT_MARKET: Final[str] = _get_str(
    "DEFAULT_MARKET",
    "regular",
)


# ============================================================
# PAIRS
# ============================================================

DEFAULT_PAIRS: Final[list[str]] = [
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
]

PAIRS: Final[list[str]] = _get_list(
    "PAIRS",
    DEFAULT_PAIRS,
)

MAX_PAIRS_PER_SCAN: Final[int] = max(
    1,
    _get_int(
        "MAX_PAIRS_PER_SCAN",
        8,
    ),
)


# ============================================================
# PROBABILITY / BACKTEST
# ============================================================

PROBABILITY_MINIMUM_TRADES: Final[int] = max(
    1,
    _get_int(
        "PROBABILITY_MINIMUM_TRADES",
        30,
    ),
)

PROBABILITY_MINIMUM_WINRATE: Final[float] = max(
    75.0,
    min(
        100.0,
        _get_float(
            "PROBABILITY_MINIMUM_WINRATE",
            75.0,
        ),
    ),
)


# Compatibility aliases.
MIN_PROBABILITY: Final[float] = PROBABILITY_MINIMUM_WINRATE
MINIMUM_PROBABILITY: Final[float] = PROBABILITY_MINIMUM_WINRATE
MINIMUM_TRADES: Final[int] = PROBABILITY_MINIMUM_TRADES


# ============================================================
# SIGNAL STORAGE
# ============================================================

SIGNAL_HISTORY_LIMIT: Final[int] = max(
    10,
    _get_int(
        "SIGNAL_HISTORY_LIMIT",
        500,
    ),
)


# ============================================================
# SERVER
# ============================================================

HOST: Final[str] = _get_str(
    "HOST",
    "0.0.0.0",
)

PORT: Final[int] = max(
    1,
    _get_int(
        "PORT",
        8000,
    ),
)

HEALTH_PATH: Final[str] = _get_str(
    "HEALTH_PATH",
    "/health",
)


# ============================================================
# TIMEZONE
# ============================================================

TIMEZONE: Final[str] = _get_str(
    "TIMEZONE",
    "Europe/Moscow",
)

MOSCOW_TIMEZONE: Final[str] = "Europe/Moscow"


# ============================================================
# ACCESS
# ============================================================

ACCESS_APPROVED: Final[str] = "APPROVED"
ACCESS_PENDING: Final[str] = "PENDING"
ACCESS_BLOCKED: Final[str] = "BLOCKED"


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL: Final[str] = _get_str(
    "LOG_LEVEL",
    "INFO",
).upper()


# ============================================================
# FEATURES
# ============================================================

ENABLE_RESULT_CHECKER: Final[bool] = _get_bool(
    "ENABLE_RESULT_CHECKER",
    True,
)

ENABLE_AUTO_SIGNALS: Final[bool] = _get_bool(
    "ENABLE_AUTO_SIGNALS",
    True,
)

ENABLE_MARKET_CACHE: Final[bool] = _get_bool(
    "ENABLE_MARKET_CACHE",
    True,
)


# ============================================================
# STARTUP
# ============================================================

STARTUP_TIMEOUT_SECONDS: Final[int] = max(
    5,
    _get_int(
        "STARTUP_TIMEOUT_SECONDS",
        30,
    ),
)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    # Application
    "APP_NAME",
    "APP_ENV",
    "DEBUG",

    # Telegram
    "BOT_TOKEN",

    # Admins
    "ADMIN_IDS",
    "OWNER_IDS",

    # Database
    "DATABASE_URL",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "DATABASE_POOL_SIZE",
    "DATABASE_MAX_OVERFLOW",
    "DATABASE_POOL_TIMEOUT",
    "DATABASE_POOL_RECYCLE",

    # Twelve Data
    "TWELVE_DATA_API_KEY",
    "TWELVE_DATA_BASE_URL",
    "TWELVE_DATA_TIMEOUT_SECONDS",
    "TWELVE_DATA_TIMEOUT",
    "TWELVE_DATA_MAX_CANDLES",
    "TWELVE_DATA_MIN_CANDLES",
    "TWELVE_DATA_MAX_REQUESTS_PER_SCAN",
    "TWELVE_DATA_CACHE_SECONDS",

    # Candles
    "MIN_CANDLES_REQUIRED",
    "MAX_CANDLES",

    # Signal thresholds
    "MIN_SIGNAL_WINRATE",
    "MIN_SIGNAL_CONFIDENCE",
    "MIN_SIGNAL_QUALITY",
    "MIN_SIGNAL_CONFIRMATIONS",

    # Scores
    "EMA_SCORE",
    "TREND_SCORE",
    "RSI_SCORE",
    "MACD_SCORE",
    "BOLLINGER_SCORE",
    "STOCHASTIC_SCORE",
    "PRICE_ACTION_SCORE",

    # Indicator periods
    "EMA_FAST_PERIOD",
    "EMA_SLOW_PERIOD",
    "EMA_TREND_PERIOD",
    "RSI_PERIOD",
    "MACD_FAST_PERIOD",
    "MACD_SLOW_PERIOD",
    "MACD_SIGNAL_PERIOD",
    "BB_PERIOD",
    "BB_STDDEV",
    "STOCHASTIC_PERIOD",
    "STOCHASTIC_SMOOTHING",

    # Indicator aliases
    "EMA_FAST",
    "EMA_SLOW",
    "EMA_TREND",
    "RSI_LENGTH",
    "MACD_FAST",
    "MACD_SLOW",
    "MACD_SIGNAL",
    "BOLLINGER_PERIOD",
    "BOLLINGER_STDDEV",
    "STOCHASTIC_K_PERIOD",
    "STOCHASTIC_D_PERIOD",

    # Automatic signals
    "AUTO_SIGNAL_ENABLED",
    "AUTO_SIGNAL_INTERVAL_MINUTES",
    "AUTO_SIGNAL_MINUTES",
    "MAX_AUTO_SCAN_PAIRS",
    "SIGNAL_COOLDOWN_MINUTES",
    "SIGNAL_DEDUPLICATION_MINUTES",

    # Expiry
    "MIN_EXPIRY_MINUTES",
    "MAX_EXPIRY_MINUTES",

    # Result checker
    "RESULT_CHECK_INTERVAL_SECONDS",
    "RESULT_CHECKER_INTERVAL_SECONDS",
    "RESULT_PRICE_TOLERANCE_SECONDS",

    # Results
    "RESULT_PENDING",
    "RESULT_WIN",
    "RESULT_LOSS",
    "RESULT_DRAW",
    "RESULT_CANCELLED",
    "SIGNAL_RESULT_PENDING",
    "SIGNAL_RESULT_WIN",
    "SIGNAL_RESULT_LOSS",
    "SIGNAL_RESULT_DRAW",
    "SIGNAL_RESULT_CANCELLED",

    # Market
    "DEFAULT_MARKET",

    # Pairs
    "DEFAULT_PAIRS",
    "PAIRS",
    "MAX_PAIRS_PER_SCAN",

    # Probability
    "PROBABILITY_MINIMUM_TRADES",
    "PROBABILITY_MINIMUM_WINRATE",
    "MIN_PROBABILITY",
    "MINIMUM_PROBABILITY",
    "MINIMUM_TRADES",

    # Storage
    "SIGNAL_HISTORY_LIMIT",

    # Server
    "HOST",
    "PORT",
    "HEALTH_PATH",

    # Time
    "TIMEZONE",
    "MOSCOW_TIMEZONE",

    # Access
    "ACCESS_APPROVED",
    "ACCESS_PENDING",
    "ACCESS_BLOCKED",

    # Logging
    "LOG_LEVEL",

    # Features
    "ENABLE_RESULT_CHECKER",
    "ENABLE_AUTO_SIGNALS",
    "ENABLE_MARKET_CACHE",

    # Startup
    "STARTUP_TIMEOUT_SECONDS",
]
