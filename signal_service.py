from __future__ import annotations

import json

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select

from database import (
    Signal,
    SignalRecipient,
    User,
    get_session,
)
from models import SignalCandidate
from time_utils import format_local_time


async def save_signal(
    candidate: SignalCandidate,
) -> Signal:
    async with get_session() as session:
        signal = Signal(
            pair=candidate.pair,
            market=candidate.market,
            direction=candidate.direction,
            expiry_minutes=candidate.expiry_minutes,
            confidence=candidate.confidence,
            quality=candidate.quality,
            winrate=candidate.winrate,
            entry_price=candidate.entry_price,
            result="pending",
            source=candidate.source,
            reasons=json.dumps(
                candidate.reasons,
                ensure_ascii=False,
            ),
            chart_path=candidate.chart_path,
            created_at=candidate.created_at,
            expires_at=candidate.expires_at,
        )

        session.add(signal)

        await session.commit()
        await session.refresh(signal)

        return signal


def signal_text(
    signal: Signal,
) -> str:
    direction = (
        "🟢 ВВЕРХ / CALL"
        if signal.direction == "UP"
        else "🔴 ВНИЗ / PUT"
    )

    return (
        "⚡ <b>НОВЫЙ СИГНАЛ</b>\n\n"
        f"💱 Пара: <b>{signal.pair}</b>\n"
        f"📊 Направление: <b>{direction}</b>\n"
        f"⏱ Экспирация: "
        f"<b>{signal.expiry_minutes} мин.</b>\n"
        f"🕐 Закрытие: "
        f"<b>{format_local_time(signal.expires_at)}</b>\n\n"
        f"🎯 Уверенность: "
        f"<b>{signal.confidence:.1f}%</b>\n"
        f"⭐ Качество: "
        f"<b>{signal.quality:.1f}%</b>\n"
        f"🏆 WINRATE: "
        f"<b>{signal.winrate:.1f}%</b>\n"
        f"💰 Вход: "
        f"<b>{signal.entry_price}</b>\n\n"
        "⚠️ Аналитическая рекомендация."
    )


async def add_recipient(
    signal_id: int,
    telegram_id: int,
    message_id: int | None,
) -> None:
    async with get_session() as session:
        session.add(
            SignalRecipient(
                signal_id=signal_id,
                telegram_id=telegram_id,
                message_id=message_id,
                created_at=__import__(
                    "datetime"
                ).datetime.utcnow(),
            )
        )

        await session.commit()


async def send_signal_to_user(
    bot: Bot,
    signal: Signal,
    telegram_id: int,
) -> bool:
    try:
        text = signal_text(signal)

        if (
            signal.chart_path
            and __import__(
                "os"
            ).path.exists(
                signal.chart_path
            )
        ):
            message = await bot.send_photo(
                telegram_id,
                FSInputFile(
                    signal.chart_path
                ),
                caption=text,
                parse_mode="HTML",
            )
        else:
            message = await bot.send_message(
                telegram_id,
                text,
                parse_mode="HTML",
            )

        await add_recipient(
            signal.id,
            telegram_id,
            message.message_id,
        )

        return True

    except Exception:
        return False


async def broadcast_signal(
    bot: Bot,
    signal: Signal,
) -> int:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.status == "approved",
                User.is_auto_signals_enabled.is_(True),
            )
        )

        users = list(
            result.scalars().all()
        )

    sent = 0

    for user in users:
        if await send_signal_to_user(
            bot,
            signal,
            user.telegram_id,
        ):
            sent += 1

    return sent
