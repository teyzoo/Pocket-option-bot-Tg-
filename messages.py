from __future__ import annotations

import json

from sqlalchemy import select

from database import BotText, get_session


DEFAULT_TEXTS = {
    "start_approved": (
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Доступ активен."
    ),
    "start_pending": (
        "⏳ <b>Заявка отправлена.</b>\n\n"
        "Ожидайте одобрения администратора."
    ),
    "start_rejected": (
        "❌ <b>Ваша заявка отклонена.</b>"
    ),
    "start_blacklisted": (
        "🚫 <b>Вы находитесь в чёрном списке.</b>"
    ),
    "signal_search": (
        "📡 <b>Получение сигнала</b>\n\n"
        "Выберите рынок:"
    ),
    "no_signal": (
        "⚪ <b>Сильного сигнала сейчас нет.</b>\n\n"
        "Минимальный WINRATE: <b>{min_winrate}%</b>\n"
        "Слабые сигналы бот не выдаёт."
    ),
    "analysis": (
        "📈 <b>Анализ рынка</b>\n\n"
        "Выберите рынок:"
    ),
    "history": (
        "📜 <b>История сигналов</b>"
    ),
    "stats": (
        "📊 <b>Статистика</b>"
    ),
    "settings": (
        "⚙️ <b>Настройки</b>"
    ),
    "win": (
        "✅ <b>СИГНАЛ ЗАКРЫТ — WIN</b>\n\n"
        "Пара: <b>{pair}</b>\n"
        "Результат: <b>WIN</b>"
    ),
    "loss": (
        "❌ <b>СИГНАЛ ЗАКРЫТ — LOSS</b>\n\n"
        "Пара: <b>{pair}</b>\n"
        "Результат: <b>LOSS</b>"
    ),
    "draw": (
        "⚪ <b>СИГНАЛ ЗАКРЫТ — DRAW</b>\n\n"
        "Пара: <b>{pair}</b>\n"
        "Результат: <b>DRAW</b>"
    ),
}


async def get_text(
    key: str,
) -> str:
    async with get_session() as session:
        result = await session.execute(
            select(BotText).where(
                BotText.key == key
            )
        )

        item = result.scalar_one_or_none()

        if item:
            return item.text

    return DEFAULT_TEXTS.get(
        key,
        "",
    )


async def set_text(
    key: str,
    text: str,
) -> None:
    async with get_session() as session:
        result = await session.execute(
            select(BotText).where(
                BotText.key == key
            )
        )

        item = result.scalar_one_or_none()

        from datetime import datetime

        if item is None:
            item = BotText(
                key=key,
                text=text,
                updated_at=datetime.utcnow(),
            )

            session.add(item)

        else:
            item.text = text
            item.updated_at = datetime.utcnow()

        await session.commit()


def render_text(
    text: str,
    **values,
) -> str:
    try:
        return text.format(
            **values
        )
    except (KeyError, ValueError):
        return text
