from __future__ import annotations

import os
from typing import Final


# ============================================================
# HELPERS
# ============================================================

def _get_str(
    name: str,
    default: str = "",
) -> str:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip()


def _get_int(
    name: str,
    default: int,
) -> int:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _get_float(
    name: str,
    default: float,
) -> float:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return default


def _get_bool(
    name: str,
    default: bool,
) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip().lower()

    if value in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "да",
        "enabled",
    }:
        return True

    if value in {
        "0",
        "false",
        "no",
        "n",
        "off",
        "нет",
        "disabled",
    }:
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
        for item in value.replace(";", ",").split(",")
        if item.strip()
    ]


def _parse_ids_from_env(
    *names: str,
) -> list[int]:
    """
    Читает Telegram ID из нескольких ENV.

    Поддерживается:

        ADMIN_IDS=123,456
        OWNER_IDS=123,456
        OWNER_ID=123

    Можно использовать:
        ,
        ;
        пробелы

    Все значения объединяются без дублей.
    """

    result: list[int] = []

    for name in names:
        raw = os.getenv(name, "")

        if not raw:
            continue

        raw = raw.replace(";", ",")

        for item in raw.split(","):
            item = item.strip()

            if not item:
                continue

            try:
                value = int(item)

            except (TypeError, ValueError):
                continue

            if value not in result:
                result.append(value)

    return result


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
# ADMINS / OWNERS
# ============================================================

# Администраторы.
ADMIN_IDS: Final[list[int]] = _parse_ids_from_env(
    "ADMIN_IDS",
)

# Владелец.
#
# Раньше здесь OWNER_IDS фактически копировался
# только из ADMIN_IDS.
#
# Теперь используются реальные ENV:
#
# OWNER_IDS=123456789
#
# или:
#
# OWNER_ID=123456789
#
OWNER_IDS: Final[list[int]] = _parse_ids_from_env(
    "OWNER_IDS",
    "OWNER_ID",
)

# Все привилегированные пользователи.
#
# Владелец также является администратором.
ALL_PRIVILEGED_IDS: Final[list[int]] = list(
    dict.fromkeys(
        ADMIN_IDS + OWNER_IDS
    )
)

# Совместимость:
# старый код может проверять ADMIN_IDS.
ADMIN_IDS = list(
    ALL_PRIVILEGED_IDS
)

# Совместимость:
# старый код может проверять OWNER_IDS.
#
# Администраторы также считаются владельцами
# для старой логики доступа.
OWNER_IDS = list(
    ALL_PRIVILEGED_IDS
)


# ============================================================
# ACCESS STATUSES
# ============================================================

ACCESS_APPROVED: Final[str] = "approved"

ACCESS_PENDING: Final[str] = "pending"

ACCESS_REJECTED: Final[str] = "rejected"

ACCESS_BLACKLISTED: Final[str] = "blacklisted"


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


# Старые названия для совместимости.

DATABASE_POOL_SIZE: Final[int] = (
    DB_POOL_SIZE
)

DATABASE_MAX_OVERFLOW: Final[int] = (
    DB_MAX_OVERFLOW
)

DATABASE_POOL_TIMEOUT: Final[int] = (
    DB_POOL_TIMEOUT
)

DATABASE_POOL_RECYCLE: Final[int] = (
    DB_POOL_RECYCLE
)


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

TWELVE_DATA_TIMEOUT_SECONDS: Final[float] = max(
    1.0,
    _get_float(
        "TWELVE_DATA_TIMEOUT_SECONDS",
        20.0,
    ),
)

# Совместимость.
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
        80,
    ),
)

MAX_CANDLES: Final[int] = max(
    MIN_CANDLES_REQUIRED,
    _get_int(
        "MAX_CANDLES",
        300,
    ),
)


# ============================================================
# SIGNAL THRESHOLDS
# ============================================================

# Минимальный исторический WINRATE.
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

# Минимальная уверенность.
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

# Минимальное качество сигнала.
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

# Минимальное количество подтверждений.
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


ATR_PERIOD: Final[int] = max(
    2,
    _get_int(
        "ATR_PERIOD",
        14,
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

BOLLINGER_STDDEV: Final[float] = (
    BB_STDDEV
)

BOLLINGER_STD: Final[float] = (
    BB_STDDEV
)


STOCHASTIC_K_PERIOD: Final[int] = (
    STOCHASTIC_PERIOD
)

STOCHASTIC_D_PERIOD: Final[int] = (
    STOCHASTIC_SMOOTHING
)

STOCHASTIC_SMOOTH: Final[int] = (
    STOCHASTIC_SMOOTHING
)


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

# Совместимость.
AUTO_SIGNAL_MINUTES: Final[int] = (
    AUTO_SIGNAL_INTERVAL_MINUTES
)


MAX_AUTO_SCAN_PAIRS: Final[int] = max(
    1,
    min(
        10,
        _get_int(
            "MAX_AUTO_SCAN_PAIRS",
            10,
        ),
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
# EXPIRY / TIME
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


# Все разрешённые тайминги:
#
# 1, 2, 3 ... 20 минут.
#
EXPIRY_MINUTES: Final[list[int]] = list(
    range(
        MIN_EXPIRY_MINUTES,
        MAX_EXPIRY_MINUTES + 1,
    )
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

# Старое название.
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
# RESULT CONSTANTS
# ============================================================

RESULT_PENDING: Final[str] = "PENDING"

RESULT_WIN: Final[str] = "WIN"

RESULT_LOSS: Final[str] = "LOSS"

RESULT_DRAW: Final[str] = "DRAW"

RESULT_CANCELLED: Final[str] = "CANCELLED"


# Старые названия.

SIGNAL_RESULT_PENDING: Final[str] = (
    RESULT_PENDING
)

SIGNAL_RESULT_WIN: Final[str] = (
    RESULT_WIN
)

SIGNAL_RESULT_LOSS: Final[str] = (
    RESULT_LOSS
)

SIGNAL_RESULT_DRAW: Final[str] = (
    RESULT_DRAW
)

SIGNAL_RESULT_CANCELLED: Final[str] = (
    RESULT_CANCELLED
)


# ============================================================
# MARKET
# ============================================================

MARKET_REGULAR: Final[str] = "regular"

MARKET_OTC: Final[str] = "otc"

DEFAULT_MARKET: Final[str] = _get_str(
    "DEFAULT_MARKET",
    MARKET_REGULAR,
)


# ============================================================
# NORMAL PAIRS
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


# ============================================================
# OTC PAIRS
# ============================================================

DEFAULT_OTC_PAIRS: Final[list[str]] = [
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


# ============================================================
# PAIR ALIASES
# ============================================================

NORMAL_PAIRS: Final[list[str]] = list(
    _get_list(
        "NORMAL_PAIRS",
        DEFAULT_PAIRS,
    )
)


OTC_PAIRS: Final[list[str]] = list(
    _get_list(
        "OTC_PAIRS",
        DEFAULT_OTC_PAIRS,
    )
)


# ============================================================
# PAIR LIMITS
# ============================================================

MAX_NORMAL_PAIRS: Final[int] = max(
    1,
    min(
        len(NORMAL_PAIRS),
        _get_int(
            "MAX_NORMAL_PAIRS",
            len(NORMAL_PAIRS),
        ),
    ),
)

MAX_OTC_PAIRS: Final[int] = max(
    1,
    min(
        len(OTC_PAIRS),
        _get_int(
            "MAX_OTC_PAIRS",
            len(OTC_PAIRS),
        ),
    ),
)


# ============================================================
# SEARCH
# ============================================================

SEARCH_LIMIT_FREE: Final[int] = max(
    1,
    _get_int(
        "SEARCH_LIMIT_FREE",
        5,
    ),
)

SEARCH_BATCH_LIMIT_PREMIUM: Final[int] = max(
    1,
    _get_int(
        "SEARCH_BATCH_LIMIT_PREMIUM",
        10,
    ),
)


# ============================================================
# PROBABILITY / BACKTEST
# ============================================================

PROBABILITY_MIN_TRADES: Final[int] = max(
    1,
    _get_int(
        "PROBABILITY_MIN_TRADES",
        10,
    ),
)

BACKTEST_MIN_TRADES: Final[int] = max(
    1,
    _get_int(
        "BACKTEST_MIN_TRADES",
        10,
    ),
)

BACKTEST_MAX_CANDLES: Final[int] = max(
    100,
    _get_int(
        "BACKTEST_MAX_CANDLES",
        300,
    ),
)


# ============================================================
# SCANNER
# ============================================================

SCANNER_MAX_PAIRS: Final[int] = max(
    1,
    min(
        10,
        _get_int(
            "SCANNER_MAX_PAIRS",
            10,
        ),
    ),
)

SCANNER_MIN_CANDLES: Final[int] = max(
    50,
    _get_int(
        "SCANNER_MIN_CANDLES",
        MIN_CANDLES_REQUIRED,
    ),
)


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL: Final[str] = _get_str(
    "LOG_LEVEL",
    "INFO",
).upper()


# ============================================================
# TIMEZONE
# ============================================================

TIMEZONE: Final[str] = _get_str(
    "TIMEZONE",
    "Europe/Moscow",
)

MOSCOW_TIMEZONE: Final[str] = (
    "Europe/Moscow"
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
        10000,
    ),
)


# ============================================================
# COMPATIBILITY
# ============================================================

# Старые/альтернативные названия, которые могли
# использоваться в предыдущих версиях проекта.

MIN_SIGNAL_SCORE: Final[float] = (
    MIN_SIGNAL_QUALITY
)

MIN_QUALITY_SCORE: Final[float] = (
    MIN_SIGNAL_QUALITY
)

MIN_WINRATE: Final[float] = (
    MIN_SIGNAL_WINRATE
)

MIN_CONFIDENCE: Final[float] = (
    MIN_SIGNAL_CONFIDENCE
)

MIN_CONFIRMATIONS: Final[int] = (
    MIN_SIGNAL_CONFIRMATIONS
)


# ============================================================
# STARTUP SUMMARY
# ============================================================

def get_config_summary() -> dict:
    """
    Возвращает безопасную информацию о конфигурации
    без вывода BOT_TOKEN и DATABASE_URL.
    """

    return {
        "app_name": APP_NAME,
        "app_env": APP_ENV,
        "debug": DEBUG,
        "admins_count": len(ADMIN_IDS),
        "owners_count": len(OWNER_IDS),
        "privileged_count": len(
            ALL_PRIVILEGED_IDS
        ),
        "database_configured": bool(
            DATABASE_URL
        ),
        "twelve_data_configured": bool(
            TWELVE_DATA_API_KEY
        ),
        "min_winrate": MIN_SIGNAL_WINRATE,
        "min_confidence": MIN_SIGNAL_CONFIDENCE,
        "min_quality": MIN_SIGNAL_QUALITY,
        "min_confirmations": MIN_SIGNAL_CONFIRMATIONS,
        "auto_enabled": AUTO_SIGNAL_ENABLED,
        "auto_interval_minutes": (
            AUTO_SIGNAL_INTERVAL_MINUTES
        ),
        "max_auto_pairs": MAX_AUTO_SCAN_PAIRS,
        "min_expiry_minutes": MIN_EXPIRY_MINUTES,
        "max_expiry_minutes": MAX_EXPIRY_MINUTES,
        "normal_pairs_count": len(
            NORMAL_PAIRS
        ),
        "otc_pairs_count": len(
            OTC_PAIRS
        ),
    }
