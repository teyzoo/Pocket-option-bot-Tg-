from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# HELPERS
# ============================================================

def _get(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default

    value = value.strip()
    return value if value else default


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
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Environment variable {name} must be an integer"
        ) from exc


def _get_float(name: str, default: float) -> float:
    value = _get(name)

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
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


def _get_int_list(name: str) -> list[int]:
    value = _get(name, "")

    if not value:
        return []

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

    return result


# ============================================================
# APPLICATION
# ============================================================

BOT_TOKEN: Final[str] = _get_required("BOT_TOKEN")

DATABASE_URL: Final[str] = _get_required("DATABASE_URL")

TWELVE_DATA_API_KEY: Final[str] = _get_required(
    "TWELVE_DATA_API_KEY"
)

ADMIN_IDS: Final[list[int]] = _get_int_list("ADMIN_IDS")

OWNER_IDS: Final[list[int]] = _get_int_list("OWNER_IDS")

HOST: Final[str] = _get("HOST", "0.0.0.0") or "0.0.0.0"

PORT: Final[int] = max(
    1,
    _get_int("PORT", 8000),
)

HEALTH_PATH: Final[str] = (
    _get("HEALTH_PATH", "/health") or "/health"
)

TIMEZONE: Final[str] = (
    _get("TIMEZONE", "Europe/Moscow")
    or "Europe/Moscow"
)


# ============================================================
# SIGNAL THRESHOLDS
# ============================================================

MIN_SIGNAL_WINRATE: Final[float] = max(
    0.0,
    min(
        100.0,
        _get_float("MIN_SIGNAL_WINRATE", 75.0),
    ),
)

MIN_SIGNAL_CONFIDENCE: Final[float] = max(
    0.0,
    min(
        100.0,
        _get_float("MIN_SIGNAL_CONFIDENCE", 75.0),
    ),
)

MIN_SIGNAL_QUALITY: Final[float] = max(
    0.0,
    min(
        100.0,
        _get_float("MIN_SIGNAL_QUALITY", 75.0),
    ),
)

MIN_SIGNAL_CONFIRMATIONS: Final[int] = max(
    1,
    _get_int("MIN_SIGNAL_CONFIRMATIONS", 3),
)


# ============================================================
# INDICATOR SCORES
#
# Максимальная сумма = 85.
# SignalEngine использует её для расчёта confidence.
# ============================================================

EMA_SCORE: Final[float] = _get_float(
    "EMA_SCORE",
    15.0,
)

TREND_SCORE: Final[float] = _get_float(
    "TREND_SCORE",
    20.0,
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
    5.0,
)


# ============================================================
# EXPIRY / TIMEFRAME
# ============================================================

MIN_EXPIRY_MINUTES: Final[int] = max(
    1,
    _get_int("MIN_EXPIRY_MINUTES", 1),
)

MAX_EXPIRY_MINUTES: Final[int] = max(
    MIN_EXPIRY_MINUTES,
    min(
        20,
        _get_int("MAX_EXPIRY_MINUTES", 20),
    ),
)

DEFAULT_EXPIRY_MINUTES: Final[int] = max(
    MIN_EXPIRY_MINUTES,
    min(
        MAX_EXPIRY_MINUTES,
        _get_int("DEFAULT_EXPIRY_MINUTES", 5),
    ),
)


# ============================================================
# MARKET / TWELVE DATA
# ============================================================

MARKET_INTERVAL: Final[str] = (
    _get("MARKET_INTERVAL", "1min")
    or "1min"
)

TWELVE_DATA_BASE_URL: Final[str] = (
    _get(
        "TWELVE_DATA_BASE_URL",
        "https://api.twelvedata.com",
    )
    or "https://api.twelvedata.com"
)

TWELVE_DATA_TIMEOUT_SECONDS: Final[float] = max(
    1.0,
    _get_float(
        "TWELVE_DATA_TIMEOUT_SECONDS",
        20.0,
    ),
)

# Compatibility alias.
TWELVE_DATA_TIMEOUT: Final[float] = (
    TWELVE_DATA_TIMEOUT_SECONDS
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


# ============================================================
# SCANNER
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
# AUTOMATIC SIGNALS
# ============================================================

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
    0,
    _get_int(
        "SIGNAL_DEDUPLICATION_MINUTES",
        15,
    ),
)


# ============================================================
# RESULT CHECKING
# ============================================================

RESULT_CHECK_INTERVAL_SECONDS: Final[int] = max(
    5,
    _get_int(
        "RESULT_CHECK_INTERVAL_SECONDS",
        30,
    ),
)

RESULT_PRICE_TOLERANCE_SECONDS: Final[int] = max(
    0,
    _get_int(
        "RESULT_PRICE_TOLERANCE_SECONDS",
        120,
    ),
)


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

EMA_FAST_PERIOD: Final[int] = max(
    1,
    _get_int("EMA_FAST_PERIOD", 9),
)

EMA_SLOW_PERIOD: Final[int] = max(
    EMA_FAST_PERIOD,
    _get_int("EMA_SLOW_PERIOD", 21),
)

EMA_TREND_PERIOD: Final[int] = max(
    EMA_SLOW_PERIOD,
    _get_int("EMA_TREND_PERIOD", 50),
)

RSI_PERIOD: Final[int] = max(
    2,
    _get_int("RSI_PERIOD", 14),
)

MACD_FAST_PERIOD: Final[int] = max(
    1,
    _get_int("MACD_FAST_PERIOD", 12),
)

MACD_SLOW_PERIOD: Final[int] = max(
    MACD_FAST_PERIOD,
    _get_int("MACD_SLOW_PERIOD", 26),
)

MACD_SIGNAL_PERIOD: Final[int] = max(
    1,
    _get_int("MACD_SIGNAL_PERIOD", 9),
)

BOLLINGER_PERIOD: Final[int] = max(
    2,
    _get_int("BOLLINGER_PERIOD", 20),
)

BOLLINGER_STD: Final[float] = max(
    0.1,
    _get_float("BOLLINGER_STD", 2.0),
)

STOCHASTIC_PERIOD: Final[int] = max(
    2,
    _get_int("STOCHASTIC_PERIOD", 14),
)

STOCHASTIC_SMOOTH: Final[int] = max(
    1,
    _get_int("STOCHASTIC_SMOOTH", 3),
)

ATR_PERIOD: Final[int] = max(
    2,
    _get_int("ATR_PERIOD", 14),
)


# ============================================================
# CHARTS
# ============================================================

CHARTS_ENABLED: Final[bool] = _get_bool(
    "CHARTS_ENABLED",
    True,
)

CHART_WIDTH: Final[float] = max(
    1.0,
    _get_float("CHART_WIDTH", 12.0),
)

CHART_HEIGHT: Final[float] = max(
    1.0,
    _get_float("CHART_HEIGHT", 8.0),
)

CHART_DPI: Final[int] = max(
    50,
    _get_int("CHART_DPI", 120),
)


# ============================================================
# CANDLE FILTER
# ============================================================

CANDLE_FILTER_ENABLED: Final[bool] = _get_bool(
    "CANDLE_FILTER_ENABLED",
    False,
)

CANDLE_FILTER_IGNORED: Final[int] = max(
    0,
    _get_int(
        "CANDLE_FILTER_IGNORED",
        0,
    ),
)

CANDLE_FILTER_DURATION_SECONDS: Final[int] = max(
    0,
    _get_int(
        "CANDLE_FILTER_DURATION_SECONDS",
        60,
    ),
)


# ============================================================
# DATABASE
# ============================================================

DB_POOL_SIZE: Final[int] = max(
    1,
    _get_int("DB_POOL_SIZE", 5),
)

DB_MAX_OVERFLOW: Final[int] = max(
    0,
    _get_int("DB_MAX_OVERFLOW", 5),
)

DB_POOL_TIMEOUT: Final[int] = max(
    1,
    _get_int("DB_POOL_TIMEOUT", 30),
)

DB_POOL_RECYCLE: Final[int] = max(
    60,
    _get_int("DB_POOL_RECYCLE", 1800),
)


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL: Final[str] = (
    _get("LOG_LEVEL", "INFO") or "INFO"
).upper()


# ============================================================
# PAIRS
# ============================================================

DEFAULT_PAIRS: Final[tuple[str, ...]] = (
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

NORMAL_PAIRS: Final[tuple[str, ...]] = DEFAULT_PAIRS

OTC_PAIRS: Final[tuple[str, ...]] = tuple(
    item.strip()
    for item in (
        _get("OTC_PAIRS", "") or ""
    ).split(",")
    if item.strip()
)


# ============================================================
# RESULT CONSTANTS
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
# USER ACCESS
# ============================================================

USER_PENDING: Final[str] = "PENDING"
USER_APPROVED: Final[str] = "APPROVED"
USER_REJECTED: Final[str] = "REJECTED"
USER_BLACKLISTED: Final[str] = "BLACKLISTED"

# Compatibility aliases.
ACCESS_PENDING: Final[str] = USER_PENDING
ACCESS_APPROVED: Final[str] = USER_APPROVED
ACCESS_REJECTED: Final[str] = USER_REJECTED
ACCESS_BLACKLISTED: Final[str] = USER_BLACKLISTED


# ============================================================
# MARKET TYPES
# ============================================================

MARKET_REGULAR: Final[str] = "REGULAR"
MARKET_OTC: Final[str] = "OTC"


# ============================================================
# SIGNAL SOURCES
# ============================================================

SIGNAL_SOURCE_AUTO: Final[str] = "auto"
SIGNAL_SOURCE_MANUAL: Final[str] = "manual"
SIGNAL_SOURCE_ANALYSIS: Final[str] = "analysis"


# ============================================================
# DIRECTIONS
# ============================================================

DIRECTION_UP: Final[str] = "UP"
DIRECTION_DOWN: Final[str] = "DOWN"


# ============================================================
# SNAPSHOT
# ============================================================

@dataclass(frozen=True)
class ConfigSnapshot:
    bot_token: str
    database_url: str
    twelve_data_api_key: str

    timezone: str

    min_signal_winrate: float
    min_signal_confidence: float
    min_signal_quality: float
    min_signal_confirmations: int

    min_expiry_minutes: int
    max_expiry_minutes: int
    default_expiry_minutes: int

    auto_signal_enabled: bool
    auto_signal_interval_minutes: int

    min_candles_required: int
    max_candles: int


# ============================================================
# VALIDATION
# ============================================================

def validate_config() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is required"
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required"
        )

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is required"
        )

    if MIN_CANDLES_REQUIRED < 50:
        raise RuntimeError(
            "MIN_CANDLES_REQUIRED must be >= 50"
        )

    if MAX_CANDLES < MIN_CANDLES_REQUIRED:
        raise RuntimeError(
            "MAX_CANDLES must be >= MIN_CANDLES_REQUIRED"
        )

    if TWELVE_DATA_TIMEOUT_SECONDS <= 0:
        raise RuntimeError(
            "TWELVE_DATA_TIMEOUT_SECONDS must be > 0"
        )

    if MIN_EXPIRY_MINUTES < 1:
        raise RuntimeError(
            "MIN_EXPIRY_MINUTES must be >= 1"
        )

    if MAX_EXPIRY_MINUTES > 20:
        raise RuntimeError(
            "MAX_EXPIRY_MINUTES must be <= 20"
        )

    if DEFAULT_EXPIRY_MINUTES < MIN_EXPIRY_MINUTES:
        raise RuntimeError(
            "DEFAULT_EXPIRY_MINUTES is below MIN_EXPIRY_MINUTES"
        )

    if DEFAULT_EXPIRY_MINUTES > MAX_EXPIRY_MINUTES:
        raise RuntimeError(
            "DEFAULT_EXPIRY_MINUTES is above MAX_EXPIRY_MINUTES"
        )

    if MIN_SIGNAL_CONFIRMATIONS < 1:
        raise RuntimeError(
            "MIN_SIGNAL_CONFIRMATIONS must be >= 1"
        )


# ============================================================
# GLOBAL CONFIG OBJECT
# ============================================================

CONFIG: Final[ConfigSnapshot] = ConfigSnapshot(
    bot_token=BOT_TOKEN,
    database_url=DATABASE_URL,
    twelve_data_api_key=TWELVE_DATA_API_KEY,
    timezone=TIMEZONE,
    min_signal_winrate=MIN_SIGNAL_WINRATE,
    min_signal_confidence=MIN_SIGNAL_CONFIDENCE,
    min_signal_quality=MIN_SIGNAL_QUALITY,
    min_signal_confirmations=MIN_SIGNAL_CONFIRMATIONS,
    min_expiry_minutes=MIN_EXPIRY_MINUTES,
    max_expiry_minutes=MAX_EXPIRY_MINUTES,
    default_expiry_minutes=DEFAULT_EXPIRY_MINUTES,
    auto_signal_enabled=AUTO_SIGNAL_ENABLED,
    auto_signal_interval_minutes=AUTO_SIGNAL_INTERVAL_MINUTES,
    min_candles_required=MIN_CANDLES_REQUIRED,
    max_candles=MAX_CANDLES,
)


validate_config()
