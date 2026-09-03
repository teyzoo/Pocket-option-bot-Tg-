from __future__ import annotations

from candle_filter import candle_filter


def set_candle_filter(
    ignored_last_candles: int,
    duration_minutes: int,
):
    return candle_filter.configure(
        ignored_last_candles=ignored_last_candles,
        duration_minutes=duration_minutes,
    )


def disable_candle_filter() -> None:
    candle_filter.disable()


def candle_filter_status() -> dict:
    settings = candle_filter.settings

    return {
        "enabled": candle_filter.active(),
        "ignored_last_candles": (
            settings.ignored_last_candles
        ),
        "expires_at": settings.expires_at,
    }
