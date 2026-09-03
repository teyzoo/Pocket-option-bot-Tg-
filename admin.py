from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from config import ADMIN_IDS
from database import JoinRequest, User, get_session
from keyboards import (
    admin_request_keyboard,
)
from services import (
    approve_user,
    blacklist_user,
    reject_user,
    unblacklist_user,
)
from states import OwnerStates


router = Router()


def admin(
    telegram_id: int,
) -> bool:
    return telegram_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_command(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    if not admin(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Доступ запрещён."
        )
        return

    async with get_session() as session:
        result = await session.execute(
            select(
                JoinRequest,
                User,
            )
            .join(
                User,
                User.telegram_id
                == JoinRequest.telegram_id,
            )
            .where(
                JoinRequest.status
                == "pending"
            )
            .order_by(
                JoinRequest.created_at.asc()
            )
        )

        rows = result.all()

    if not rows:
        await message.answer(
            "👑 <b>Админ-панель</b>\n\n"
            "📭 Новых заявок нет.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"📥 Заявок: <b>{len(rows)}</b>",
        parse_mode="HTML",
    )

    for request, user in rows:
        username = (
            f"@{user.username}"
            if user.username
            else "нет"
        )

        await message.answer(
            "📥 <b>Заявка</b>\n\n"
            f"👤 {user.first_name or '—'}\n"
            f"🔗 {username}\n"
            f"🆔 <code>{user.telegram_id}</code>",
            parse_mode="HTML",
            reply_markup=admin_request_keyboard(
                user.telegram_id
            ),
        )


@router.callback_query(
    lambda callback:
    callback.data.startswith(
        "admin:approve:"
    )
)
async def approve_callback(
    callback: CallbackQuery,
) -> None:
    if not admin(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )
        return

    telegram_id = int(
        callback.data.split(":")[2]
    )

    user = await approve_user(
        telegram_id,
        callback.from_user.id,
    )

    await callback.answer(
        "Одобрено"
    )

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Пользователь одобрен</b>\n\n"
            f"<code>{telegram_id}</code>",
            parse_mode="HTML",
        )


@router.callback_query(
    lambda callback:
    callback.data.startswith(
        "admin:reject:"
    )
)
async def reject_callback(
    callback: CallbackQuery,
) -> None:
    if not admin(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )
        return

    telegram_id = int(
        callback.data.split(":")[2]
    )

    await reject_user(
        telegram_id,
        callback.from_user.id,
    )

    await callback.answer(
        "Отклонено"
    )

    if callback.message:
        await callback.message.edit_text(
            "❌ <b>Заявка отклонена</b>",
            parse_mode="HTML",
        )


@router.callback_query(
    lambda callback:
    callback.data.startswith(
        "admin:blacklist:"
    )
)
async def blacklist_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not admin(
        callback.from_user.id
    ):
        return

    telegram_id = int(
        callback.data.split(":")[2]
    )

    await state.update_data(
        blacklist_telegram_id=telegram_id
    )

    await state.set_state(
        OwnerStates.blacklist_reason
    )

    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "🚫 Напиши причину добавления "
            "в чёрный список.\n\n"
            "Или отправь <code>-</code>.",
            parse_mode="HTML",
        )


@router.message(
    OwnerStates.blacklist_reason
)
async def blacklist_finish(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not admin(
        message.from_user.id
    ):
        await state.clear()
        return

    data = await state.get_data()

    telegram_id = data.get(
        "blacklist_telegram_id"
    )

    reason = (
        message.text
        if message.text != "-"
        else None
    )

    await blacklist_user(
        int(telegram_id),
        message.from_user.id,
        reason,
    )

    await state.clear()

    await message.answer(
        "🚫 <b>Пользователь добавлен в ЧС.</b>",
        parse_mode="HTML",
    )
