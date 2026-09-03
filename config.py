from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip()

    return value if value else default


def required_env(name: str) -> str:
    value = env(name)

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def env_int(
    name: str,
    default: int,
) -> int:
    value = env(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be an integer"
        ) from exc


def env_float(
    name: str,
    default: float,
) -> float:
    value = env(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be a number"
        ) from exc


def env_bool(
    name: str,
    default: bool,
) -> bool:
    value = env(name)

    if value is None:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "on",
        "y",
    }


def parse_int_list(value: str) -> tuple[int, ...]:
    result: list[int] = []

    for item in value.split(","):
        item = item.strip()

        if not item:
            continue

        try:
            result.append(int(item))
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid integer in ADMIN_IDS: {item}"
            ) from exc

    return tuple(dict.fromkeys(result))


BOT_TOKEN: Final[str] = required_env("BOT_TOKEN")
DATABASE_URL: Final[str] = required_env("DATABASE_URL")
TWELVE_DATA_API_KEY: Final[str] = required_env(
    "TWELVE_DATA_API_KEY"
)

ADMIN_IDS: Final[tuple[int, ...]] = parse_int_list(
    required_env("ADMIN_IDS")
)

HOST: Final[str] = env(
    "HOST",
    "0.0.0.0",
) or "0.0.0.0"

PORT: Final[int] = env_int(
    "PORT",
    10000,
)

HEALTH_PATH: Final[str] = env(
    "HEALTH_PATH",
    "/health",
) or "/health"

TIMEZONE: Final[str] = env(
    "TIMEZONE",
    "Europe/Moscow",
) or "Europe/Moscow"


# ---------------------------------------------------------------------------
# ACCESS
# ---------------------------------------------------------------------------

STATUS_PENDING: Final[str] = "pending"
STATUS_APPROVED: Final[str] = "approved"
STATUS_REJECTED: Final[str] = "rejected"
STATUS_BLACKLISTED: Final[str] = "blacklisted"


# ---------------------------------------------------------------------------
# SIGNAL
# ---------------------------------------------------------------------------

MIN_SIGNAL_WINRATE: Final[float] = max(
    75.0,
    env_float(
        "MIN_SIGNAL_WINRATE",
        75.0,
    ),
)

MIN_SIGNAL_CONFIDENCE: Final[float] = max(
    75.0,
    env_float(
        "MIN_SIGNAL_CONFIDENCE",
        75.0,
    ),
)

MIN_SIGNAL_QUALITY: Final[float] = max(
    75.0,
    env_float(
        "MIN_SIGNAL_QUALITY",
        75.0,
    ),
)

MIN_SIGNAL_CONFIRMATIONS: Final[int] = max(
    3,
    env_int(
        "MIN_SIGNAL_CONFIRMATIONS",
        3,
    ),
)


MIN_EXPIRY_MINUTES: Final[int] = 1
MAX_EXPIRY_MINUTES: Final[int] = 20

DEFAULT_EXPIRY_MINUTES: Final[int] = min(
    MAX_EXPIRY_MINUTES,
    max(
        MIN_EXPIRY_MINUTES,
        env_int(
            "DEFAULT_EXPIRY_MINUTES",
            5,
        ),
    ),
)


# ---------------------------------------------------------------------------
# MARKET
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

# Intentionally empty until a real OTC data source is integrated.
# We NEVER generate fake OTC candles.
OTC_PAIRS: Final[tuple[str, ...]] = ()


# ---------------------------------------------------------------------------
# TWELVE DATA
# ---------------------------------------------------------------------------

TWELVE_DATA_BASE_URL: Final[str] = env(
    "TWELVE_DATA_BASE_URL",
    "https://api.twelvedata.com",
) or "https://api.twelvedata.com"

TWELVE_DATA_TIMEOUT: Final[float] = env_float(
    "TWELVE_DATA_TIMEOUT",
    20.0,
)

MAX_CANDLES: Final[int] = max(
    100,
    env_int(
        "MAX_CANDLES",
        250,
    ),
)

MIN_CANDLES_REQUIRED: Final[int] = max(
    80,
    env_int(
        "MIN_CANDLES_REQUIRED",
        100,
    ),
)

MAX_API_REQUESTS_PER_SCAN: Final[int] = max(
    1,
    env_int(
        "MAX_API_REQUESTS_PER_SCAN",
        4,
    ),
)


# ---------------------------------------------------------------------------
# INDICATORS
# ---------------------------------------------------------------------------

EMA_FAST_PERIOD: Final[int] = 9
EMA_SLOW_PERIOD: Final[int] = 21
EMA_TREND_PERIOD: Final[int] = 50

RSI_PERIOD: Final[int] = 14

MACD_FAST_PERIOD: Final[int] = 12
MACD_SLOW_PERIOD: Final[int] = 26
MACD_SIGNAL_PERIOD: Final[int] = 9

BOLLINGER_PERIOD: Final[int] = 20
BOLLINGER_STD: Final[float] = 2.0

STOCHASTIC_PERIOD: Final[int] = 14
STOCHASTIC_SMOOTHING: Final[int] = 3

ATR_PERIOD: Final[int] = 14


# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------

EMA_SCORE: Final[float] = 15.0
TREND_SCORE: Final[float] = 15.0
RSI_SCORE: Final[float] = 10.0
MACD_SCORE: Final[float] = 15.0
BOLLINGER_SCORE: Final[float] = 10.0
STOCHASTIC_SCORE: Final[float] = 10.0
PRICE_ACTION_SCORE: Final[float] = 10.0

MAX_SIGNAL_SCORE: Final[float] = (
    EMA_SCORE
    + TREND_SCORE
    + RSI_SCORE
    + MACD_SCORE
    + BOLLINGER_SCORE
    + STOCHASTIC_SCORE
    + PRICE_ACTION_SCORE
)


# ---------------------------------------------------------------------------
# RESULT
# ---------------------------------------------------------------------------

RESULT_PENDING: Final[str] = "pending"
RESULT_WIN: Final[str] = "win"
RESULT_LOSS: Final[str] = "loss"
RESULT_DRAW: Final[str] = "draw"
RESULT_CANCELLED: Final[str] = "cancelled"


# ---------------------------------------------------------------------------
# AUTO SIGNALS
# ---------------------------------------------------------------------------

AUTO_SIGNALS_ENABLED: Final[bool] = env_bool(
    "AUTO_SIGNALS_ENABLED",
    True,
)

AUTO_SIGNAL_INTERVAL_MINUTES: Final[int] = max(
    1,
    env_int(
        "AUTO_SIGNAL_INTERVAL_MINUTES",
        5,
    ),
)

AUTO_SIGNAL_MIN_WINRATE: Final[float] = max(
    75.0,
    env_float(
        "AUTO_SIGNAL_MIN_WINRATE",
        75.0,
    ),
)

AUTO_SIGNAL_MAX_PER_CYCLE: Final[int] = max(
    1,
    env_int(
        "AUTO_SIGNAL_MAX_PER_CYCLE",
        1,
    ),
)


# ---------------------------------------------------------------------------
# CHART
# ---------------------------------------------------------------------------

CHART_ENABLED: Final[bool] = env_bool(
    "CHART_ENABLED",
    True,
)

CHART_CANDLES: Final[int] = max(
    30,
    env_int(
        "CHART_CANDLES",
        80,
    ),
)

CHART_DPI: Final[int] = max(
    100,
    env_int(
        "CHART_DPI",
        120,
    ),
)


# ---------------------------------------------------------------------------
# TEMPORARY CANDLE FILTER
# ---------------------------------------------------------------------------

CANDLE_FILTER_ENABLED: Final[bool] = env_bool(
    "CANDLE_FILTER_ENABLED",
    False,
)

DEFAULT_IGNORED_LAST_CANDLES: Final[int] = max(
    0,
    env_int(
        "DEFAULT_IGNORED_LAST_CANDLES",
        0,
    ),
)

MAX_IGNORED_LAST_CANDLES: Final[int] = max(
    0,
    env_int(
        "MAX_IGNORED_LAST_CANDLES",
        50,
    ),
)


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

DB_POOL_SIZE: Final[int] = max(
    1,
    env_int(
        "DB_POOL_SIZE",
        5,
    ),
)

DB_MAX_OVERFLOW: Final[int] = max(
    0,
    env_int(
        "DB_MAX_OVERFLOW",
        5,
    ),
)


# ---------------------------------------------------------------------------
# SAFETY / RATE LIMITS
# ---------------------------------------------------------------------------

USER_SIGNAL_COOLDOWN_SECONDS: Final[int] = max(
    0,
    env_int(
        "USER_SIGNAL_COOLDOWN_SECONDS",
        15,
    ),
)

AUTO_SIGNAL_DEDUP_MINUTES: Final[int] = max(
    1,
    env_int(
        "AUTO_SIGNAL_DEDUP_MINUTES",
        10,
    ),
)

RESULT_CHECK_INTERVAL_SECONDS: Final[int] = max(
    10,
    env_int(
        "RESULT_CHECK_INTERVAL_SECONDS",
        30,
    ),
)


@dataclass(frozen=True, slots=True)
class SignalSettings:
    min_winrate: float = MIN_SIGNAL_WINRATE
    min_confidence: float = MIN_SIGNAL_CONFIDENCE
    min_quality: float = MIN_SIGNAL_QUALITY
    min_confirmations: int = MIN_SIGNAL_CONFIRMATIONS


SIGNAL_SETTINGS: Final[SignalSettings] = SignalSettings()


def validate_config() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty")

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is empty")

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is empty"
        )

    if not ADMIN_IDS:
        raise RuntimeError(
            "ADMIN_IDS must contain at least one Telegram ID"
        )

    if MIN_SIGNAL_WINRATE < 75:
        raise RuntimeError(
            "MIN_SIGNAL_WINRATE cannot be below 75"
        )

    if MIN_SIGNAL_CONFIDENCE < 75:
        raise RuntimeError(
            "MIN_SIGNAL_CONFIDENCE cannot be below 75"
        )

    if MIN_SIGNAL_QUALITY < 75:
        raise RuntimeError(
            "MIN_SIGNAL_QUALITY cannot be below 75"
        )

    if not NORMAL_PAIRS:
        raise RuntimeError(
            "NORMAL_PAIRS cannot be empty"
        )


validate_config()
