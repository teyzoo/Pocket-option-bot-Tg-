from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip()

    return value if value else default


def _get_required_env(name: str) -> str:
    value = _get_env(name)

    if not value:
        raise RuntimeError(
            f"Не задана обязательная переменная окружения: {name}"
        )

    return value


def _get_int_env(name: str, default: int) -> int:
    value = _get_env(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Переменная {name} должна быть целым числом."
        ) from exc


def _get_float_env(name: str, default: float) -> float:
    value = _get_env(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Переменная {name} должна быть числом."
        ) from exc


def _get_bool_env(name: str, default: bool) -> bool:
    value = _get_env(name)

    if value is None:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "да",
    }


def _get_int_list_env(name: str) -> tuple[int, ...]:
    value = _get_env(name)

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
                f"Переменная {name} содержит некорректный ID: {item}"
            ) from exc

    return tuple(dict.fromkeys(result))


# ============================================================
# ОСНОВНЫЕ НАСТРОЙКИ
# ============================================================

BOT_TOKEN: Final[str] = _get_required_env("BOT_TOKEN")

DATABASE_URL: Final[str] = _get_required_env("DATABASE_URL")

TWELVE_DATA_API_KEY: Final[str] = _get_required_env(
    "TWELVE_DATA_API_KEY"
)


# ============================================================
# АДМИНИСТРАТОРЫ
# ============================================================

ADMIN_IDS: Final[tuple[int, ...]] = _get_int_list_env("ADMIN_IDS")


# ============================================================
# WEB / RENDER
# ============================================================

HOST: Final[str] = _get_env(
    "HOST",
    "0.0.0.0",
) or "0.0.0.0"

PORT: Final[int] = _get_int_env(
    "PORT",
    10000,
)

HEALTH_PATH: Final[str] = "/health"


# ============================================================
# ЧАСОВОЙ ПОЯС
# ============================================================

TIMEZONE: Final[str] = _get_env(
    "TIMEZONE",
    "Europe/Moscow",
) or "Europe/Moscow"


# ============================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================

USER_STATUS_PENDING: Final[str] = "pending"
USER_STATUS_APPROVED: Final[str] = "approved"
USER_STATUS_REJECTED: Final[str] = "rejected"
USER_STATUS_BLACKLISTED: Final[str] = "blacklisted"


# ============================================================
# СИГНАЛЫ
# ============================================================

MIN_SIGNAL_CONFIDENCE: Final[float] = _get_float_env(
    "MIN_SIGNAL_CONFIDENCE",
    75.0,
)

MIN_SIGNAL_QUALITY: Final[float] = _get_float_env(
    "MIN_SIGNAL_QUALITY",
    75.0,
)

MIN_EXPIRY_MINUTES: Final[int] = 1

MAX_EXPIRY_MINUTES: Final[int] = 20

DEFAULT_EXPIRY_MINUTES: Final[int] = _get_int_env(
    "DEFAULT_EXPIRY_MINUTES",
    5,
)


# ============================================================
# СКАНИРОВАНИЕ
# ============================================================

SCAN_INTERVAL_SECONDS: Final[int] = _get_int_env(
    "SCAN_INTERVAL_SECONDS",
    60,
)

AUTO_SIGNAL_INTERVAL_MINUTES: Final[int] = _get_int_env(
    "AUTO_SIGNAL_INTERVAL_MINUTES",
    5,
)

MAX_CANDLES: Final[int] = _get_int_env(
    "MAX_CANDLES",
    200,
)

MIN_CANDLES_REQUIRED: Final[int] = _get_int_env(
    "MIN_CANDLES_REQUIRED",
    80,
)


# ============================================================
# TWELVE DATA
# ============================================================

TWELVE_DATA_BASE_URL: Final[str] = _get_env(
    "TWELVE_DATA_BASE_URL",
    "https://api.twelvedata.com",
) or "https://api.twelvedata.com"

TWELVE_DATA_TIMEOUT: Final[float] = _get_float_env(
    "TWELVE_DATA_TIMEOUT",
    15.0,
)

# Безопасное ограничение количества запросов одного цикла.
MAX_API_REQUESTS_PER_SCAN: Final[int] = _get_int_env(
    "MAX_API_REQUESTS_PER_SCAN",
    6,
)


# ============================================================
# РАЗРЕШЁННЫЕ ОБЫЧНЫЕ ПАРЫ POCKET OPTION
# ============================================================

POCKET_OPTION_REGULAR_PAIRS: Final[tuple[str, ...]] = (
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


# ============================================================
# OTC
# ============================================================

# OTC НЕ считается доступным автоматически.
#
# Пока список пустой, чтобы бот никогда не выдавал
# выдуманные OTC-сигналы.
#
# Позже сюда можно добавить пары только после подключения
# реального источника OTC-котировок.

POCKET_OPTION_OTC_PAIRS: Final[tuple[str, ...]] = ()


# ============================================================
# ИНДИКАТОРЫ
# ============================================================

EMA_FAST_PERIOD: Final[int] = 9
EMA_SLOW_PERIOD: Final[int] = 21

EMA_TREND_PERIOD: Final[int] = 50

RSI_PERIOD: Final[int] = 14

MACD_FAST_PERIOD: Final[int] = 12
MACD_SLOW_PERIOD: Final[int] = 26
MACD_SIGNAL_PERIOD: Final[int] = 9

BOLLINGER_PERIOD: Final[int] = 20
BOLLINGER_STD: Final[float] = 2.0

STOCHASTIC_K_PERIOD: Final[int] = 14
STOCHASTIC_D_PERIOD: Final[int] = 3

ATR_PERIOD: Final[int] = 14


# ============================================================
# СИСТЕМА ОЦЕНКИ СИГНАЛА
# ============================================================

SCORE_TREND: Final[float] = 20.0
SCORE_EMA: Final[float] = 15.0
SCORE_RSI: Final[float] = 15.0
SCORE_MACD: Final[float] = 15.0
SCORE_BOLLINGER: Final[float] = 10.0
SCORE_STOCHASTIC: Final[float] = 10.0
SCORE_SUPPORT_RESISTANCE: Final[float] = 5.0
SCORE_CANDLE: Final[float] = 10.0


# ============================================================
# ТИПЫ СИГНАЛОВ
# ============================================================

SIGNAL_UP: Final[str] = "UP"
SIGNAL_DOWN: Final[str] = "DOWN"

SIGNAL_TYPE_REGULAR: Final[str] = "regular"
SIGNAL_TYPE_OTC: Final[str] = "otc"
SIGNAL_TYPE_ANY: Final[str] = "any"


# ============================================================
# РЕЗУЛЬТАТЫ СИГНАЛОВ
# ============================================================

SIGNAL_RESULT_PENDING: Final[str] = "pending"
SIGNAL_RESULT_WIN: Final[str] = "win"
SIGNAL_RESULT_LOSS: Final[str] = "loss"
SIGNAL_RESULT_DRAW: Final[str] = "draw"
SIGNAL_RESULT_CANCELLED: Final[str] = "cancelled"


# ============================================================
# АВТОМАТИЧЕСКАЯ РАССЫЛКА
# ============================================================

AUTO_SIGNALS_ENABLED: Final[bool] = _get_bool_env(
    "AUTO_SIGNALS_ENABLED",
    True,
)

AUTO_SIGNAL_MIN_CONFIDENCE: Final[float] = _get_float_env(
    "AUTO_SIGNAL_MIN_CONFIDENCE",
    75.0,
)

AUTO_SIGNAL_MAX_PER_CYCLE: Final[int] = _get_int_env(
    "AUTO_SIGNAL_MAX_PER_CYCLE",
    1,
)


# ============================================================
# ЗАЩИТА ОТ СПАМА
# ============================================================

USER_SIGNAL_COOLDOWN_SECONDS: Final[int] = _get_int_env(
    "USER_SIGNAL_COOLDOWN_SECONDS",
    30,
)

MAX_MANUAL_REQUESTS_PER_MINUTE: Final[int] = _get_int_env(
    "MAX_MANUAL_REQUESTS_PER_MINUTE",
    3,
)


# ============================================================
# ДАТАБАЗА
# ============================================================

DB_POOL_SIZE: Final[int] = _get_int_env(
    "DB_POOL_SIZE",
    5,
)

DB_MAX_OVERFLOW: Final[int] = _get_int_env(
    "DB_MAX_OVERFLOW",
    5,
)

DB_POOL_TIMEOUT: Final[int] = _get_int_env(
    "DB_POOL_TIMEOUT",
    30,
)

DB_POOL_RECYCLE: Final[int] = _get_int_env(
    "DB_POOL_RECYCLE",
    1800,
)


# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_PARSE_MODE: Final[str] = "HTML"

BOT_NAME: Final[str] = _get_env(
    "BOT_NAME",
    "TEYZOO SIGNAL",
) or "TEYZOO SIGNAL"


# ============================================================
# ДАННЫЕ АДМИНА
# ============================================================

@dataclass(frozen=True)
class AdminConfig:
    ids: tuple[int, ...]

    @property
    def enabled(self) -> bool:
        return bool(self.ids)


ADMIN_CONFIG: Final[AdminConfig] = AdminConfig(
    ids=ADMIN_IDS,
)


# ============================================================
# ВАЛИДАЦИЯ КОНФИГА
# ============================================================

def validate_config() -> None:
    """
    Проверяет основные настройки при запуске приложения.
    """

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан.")

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не задан.")

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY не задан."
        )

    if not ADMIN_IDS:
        raise RuntimeError(
            "ADMIN_IDS не задан. "
            "Укажи хотя бы один Telegram ID администратора."
        )

    if not 0 <= MIN_SIGNAL_CONFIDENCE <= 100:
        raise RuntimeError(
            "MIN_SIGNAL_CONFIDENCE должен быть от 0 до 100."
        )

    if not 0 <= MIN_SIGNAL_QUALITY <= 100:
        raise RuntimeError(
            "MIN_SIGNAL_QUALITY должен быть от 0 до 100."
        )

    if MIN_EXPIRY_MINUTES < 1:
        raise RuntimeError(
            "MIN_EXPIRY_MINUTES не может быть меньше 1."
        )

    if MAX_EXPIRY_MINUTES > 20:
        raise RuntimeError(
            "MAX_EXPIRY_MINUTES не может быть больше 20."
        )

    if MIN_EXPIRY_MINUTES > MAX_EXPIRY_MINUTES:
        raise RuntimeError(
            "Минимальное время экспирации больше максимального."
        )

    if DEFAULT_EXPIRY_MINUTES < MIN_EXPIRY_MINUTES:
        raise RuntimeError(
            "DEFAULT_EXPIRY_MINUTES меньше минимального значения."
        )

    if DEFAULT_EXPIRY_MINUTES > MAX_EXPIRY_MINUTES:
        raise RuntimeError(
            "DEFAULT_EXPIRY_MINUTES больше максимального значения."
        )

    if MIN_CANDLES_REQUIRED < 50:
        raise RuntimeError(
            "MIN_CANDLES_REQUIRED должен быть не меньше 50."
        )

    if MAX_CANDLES < MIN_CANDLES_REQUIRED:
        raise RuntimeError(
            "MAX_CANDLES меньше MIN_CANDLES_REQUIRED."
        )

    if MAX_API_REQUESTS_PER_SCAN < 1:
        raise RuntimeError(
            "MAX_API_REQUESTS_PER_SCAN должен быть больше 0."
        )

    if DB_POOL_SIZE < 1:
        raise RuntimeError(
            "DB_POOL_SIZE должен быть больше 0."
        )

    if DB_MAX_OVERFLOW < 0:
        raise RuntimeError(
            "DB_MAX_OVERFLOW не может быть отрицательным."
        )


validate_config()
