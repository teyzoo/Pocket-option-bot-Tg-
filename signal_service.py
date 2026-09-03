from __future__ import annotations

import json
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from database import (
    Signal,
    SignalRecipient,
    User,
    get_session,
)
from models import SignalCandidate


async def save_signal(
    candidate: SignalCandidate,
) -> Signal:
    async with get_session() as session:
        signal = Signal(
            pair=candidate.pair,
            direction=candidate.direction,
            expiry_minutes=candidate.expiry_minutes,
            confidence=candidate.confidence,
            quality=candidate.quality,
            entry_price=candidate.entry_price,
            close_price=None,
            result="pending",
            source=candidate.source,
            reasons=json.dumps(
                candidate.reasons,
                ensure_ascii=False,
            ),
            created_at=candidate.created_at,
            expires_at=candidate.expires_at,
            checked_at=None,
        )

        session.add(signal)

        await session.commit()
        await session.refresh(signal)

        return signal


async def get_approved_users() -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.status == "approved",
                User.is_auto_signals_enabled.is_(True),
            )
        )

        return list(result.scalars().all())


async def add_recipient(
    signal_id: int,
    telegram_id: int,
    message_id: int | None,
) -> None:
    async with get_session() as session:
        recipient = SignalRecipient(
            signal_id=signal_id,
            telegram_id=telegram_id,
            message_id=message_id,
            created_at=datetime.utcnow(),
        )

        session.add(recipient)

        await session.commit()


def format_signal_message(
    signal: Signal,
) -> str:
    direction = (
        "🟢 ВВЕРХ / CALL"
        if signal.direction == "UP"
        else "🔴 ВНИЗ / PUT"
    )

    close_time = signal.expires_at.strftime("%H:%M:%S")

    return (
        "⚡ <b>НОВЫЙ СИГНАЛ</b>\n\n"
        f"💱 Пара: <b>{signal.pair}</b>\n"
        f"📊 Направление: <b>{direction}</b>\n"
        f"⏱ Экспирация: <b>{signal.expiry_minutes} мин.</b>\n"
        f"🕐 Закрытие: <b>{close_time}</b>\n\n"
        f"🎯 Уверенность: <b>{signal.confidence:.1f}%</b>\n"
        f"⭐ Качество: <b>{signal.quality:.1f}%</b>\n"
        f"💰 Вход: <b>{signal.entry_price}</b>\n\n"
        "⚠️ Сигнал является аналитической рекомендацией, "
        "а не гарантией результата."
    )


async def broadcast_signal(
    bot: Bot,
    signal: Signal,
) -> int:
    users = await get_approved_users()

    sent = 0

    text = format_signal_message(signal)

    for user in users:
        try:
            message = await bot.send_message(
                user.telegram_id,
                text,
                parse_mode="HTML",
            )

            await add_recipient(
                signal_id=signal.id,
                telegram_id=user.telegram_id,
                message_id=message.message_id,
            )

            sent += 1

        except Exception:
            continue

    return sent
