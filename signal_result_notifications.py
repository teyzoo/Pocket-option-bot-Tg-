from __future__ import annotations

import logging
from collections import defaultdict

from aiogram import Bot
from sqlalchemy import select

from config import (
    SIGNAL_RESULT_CANCELLED,
    SIGNAL_RESULT_DRAW,
    SIGNAL_RESULT_LOSS,
    SIGNAL_RESULT_WIN,
)
from database import Signal, SignalRecipient, get_session
from messages import render_message
from utils import (
    direction_text,
    format_datetime,
    format_pair,
    format_price,
)

logger = logging.getLogger(__name__)


RESULT_TITLES = {
    SIGNAL_RESULT_WIN: "✅ WIN",
    SIGNAL_RESULT_LOSS: "❌ LOSS",
    SIGNAL_RESULT_DRAW: "➖ DRAW",
    SIGNAL_RESULT_CANCELLED: "⚪ ОТМЕНЁН",
}


def format_result_message(signal: Signal) -> str:
    result = signal.result or SIGNAL_RESULT_CANCELLED

    title = RESULT_TITLES.get(
        result,
        "📊 РЕЗУЛЬТАТ",
    )

    pair = format_pair(signal.pair)
    direction = direction_text(signal.direction)

    entry_price = format_price(
        signal.entry_price
    )

    close_price = format_price(
        signal.close_price
    )

    winrate = float(
        getattr(signal, "winrate", 0) or 0
    )

    confidence = float(
        getattr(signal, "confidence", 0) or 0
    )

    expiry_minutes = int(
        getattr(signal, "expiry_minutes", 0) or 0
    )

    close_time = format_datetime(
        signal.expires_at
    )

    text = render_message(
        "result",
        result_title=title,
        pair=pair,
        direction=direction,
        entry_price=entry_price,
        close_price=close_price,
        expiry_minutes=expiry_minutes,
        close_time=close_time,
        winrate=f"{winrate:.2f}%",
        confidence=f"{confidence:.2f}%",
    )

    return text


async def get_signal_recipients(
    signal_id: int,
) -> list[SignalRecipient]:
    async with get_session() as session:
        query = (
            select(SignalRecipient)
            .where(
                SignalRecipient.signal_id == signal_id,
            )
            .order_by(
                SignalRecipient.id.asc(),
            )
        )

        result = await session.execute(query)

        return list(result.scalars().all())


async def notify_signal_result(
    bot: Bot,
    signal: Signal,
) -> int:
    recipients = await get_signal_recipients(
        signal.id
    )

    if not recipients:
        return 0

    text = format_result_message(signal)

    sent = 0

    for recipient in recipients:
        try:
            await bot.send_message(
                chat_id=int(recipient.telegram_id),
                text=text,
            )

            sent += 1

        except Exception as exc:
            logger.warning(
                "Failed to send result for signal %s to %s: %s",
                signal.id,
                recipient.telegram_id,
                exc,
            )

    return sent


async def notify_many_signal_results(
    bot: Bot,
    signals: list[Signal],
) -> int:
    total = 0

    for signal in signals:
        total += await notify_signal_result(
            bot=bot,
            signal=signal,
        )

    return total


async def get_user_result_statistics(
    telegram_id: int,
) -> dict[str, int | float]:
    async with get_session() as session:
        query = (
            select(
                Signal.result,
            )
            .join(
                SignalRecipient,
                SignalRecipient.signal_id == Signal.id,
            )
            .where(
                SignalRecipient.telegram_id == int(
                    telegram_id
                ),
            )
        )

        result = await session.execute(query)

        rows = list(result.scalars().all())

    stats = defaultdict(int)

    for item in rows:
        stats[item] += 1

    wins = stats[SIGNAL_RESULT_WIN]
    losses = stats[SIGNAL_RESULT_LOSS]
    draws = stats[SIGNAL_RESULT_DRAW]

    completed = wins + losses + draws

    if completed:
        winrate = (
            wins / completed
        ) * 100.0
    else:
        winrate = 0.0

    return {
        "total": len(rows),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "cancelled": stats[SIGNAL_RESULT_CANCELLED],
        "completed": completed,
        "winrate": winrate,
    }
