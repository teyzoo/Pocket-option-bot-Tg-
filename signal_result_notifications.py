from __future__ import annotations

from aiogram import Bot
from sqlalchemy import select

from database import (
    Signal,
    SignalRecipient,
    get_session,
)
from messages import (
    get_text,
    render_text,
)


async def notify_result(
    bot: Bot,
    signal: Signal,
) -> None:
    if signal.result == "win":
        template = await get_text("win")

    elif signal.result == "loss":
        template = await get_text("loss")

    elif signal.result == "draw":
        template = await get_text("draw")

    else:
        return

    text = render_text(
        template,
        pair=signal.pair,
        result=signal.result.upper(),
    )

    async with get_session() as session:
        result = await session.execute(
            select(
                SignalRecipient
            ).where(
                SignalRecipient.signal_id
                == signal.id
            )
        )

        recipients = list(
            result.scalars().all()
        )

    for recipient in recipients:
        try:
            await bot.send_message(
                recipient.telegram_id,
                text,
                parse_mode="HTML",
            )
        except Exception:
            continue
