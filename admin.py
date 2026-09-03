from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from config import ADMIN_IDS
from database import JoinRequest, User, get_session
from keyboards import admin_request_keyboard
from services import (
    approve_user,
    blacklist_user,
    reject_user,
    unblacklist_user,
)
from states import AdminStates


router = Router()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_command(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with get_session() as session:
        result = await session.execute(
            select(JoinRequest, User)
            .join(
                User,
                User.telegram_id == JoinRequest.telegram_id,
            )
            .where(JoinRequest.status == "pending")
            .order_by(JoinRequest.created_at.asc())
        )

        requests = result.all()

    if not requests:
        await message.answer(
            "👑 <b>Админ-панель</b>\n\n"
            "📭 Новых заявок нет.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"👑 <b>Админ-панель</b>\n\n"
        f"📥 Ожидающих заявок: <b>{len(requests)}</b>",
        parse_mode="HTML",
    )

    for request, user in requests:
        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        text = (
            "📥 <b>Новая заявка</b>\n\n"
            f"👤 Имя: <b>{user.first_name or '—'}</b>\n"
            f"🔗 Username: <b>{username}</b>\n"
            f"🆔 ID: <code>{user.telegram_id}</code>\n"
            f"📅 Заявка: {request.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=admin_request_keyboard(
                user.telegram_id
            ),
        )


@router.callback_query(lambda c: c.data.startswith("admin:approve:"))
async def approve_callback(
    callback: CallbackQuery,
) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    telegram_id = int(callback.data.split(":")[2])

    user = await approve_user(
        telegram_id=telegram_id,
        admin_id=callback.from_user.id,
    )

    if user is None:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return

    await callback.answer("Пользователь одобрен")

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Пользователь одобрен</b>\n\n"
            f"🆔 <code>{telegram_id}</code>",
            parse_mode="HTML",
        )


@router.callback_query(lambda c: c.data.startswith("admin:reject:"))
async def reject_callback(
    callback: CallbackQuery,
) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    telegram_id = int(callback.data.split(":")[2])

    user = await reject_user(
        telegram_id=telegram_id,
        admin_id=callback.from_user.id,
    )

    if user is None:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return

    await callback.answer("Заявка отклонена")

    if callback.message:
        await callback.message.edit_text(
            "❌ <b>Заявка отклонена</b>\n\n"
            f"🆔 <code>{telegram_id}</code>",
            parse_mode="HTML",
        )


@router.callback_query(lambda c: c.data.startswith("admin:blacklist:"))
async def blacklist_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    telegram_id = int(callback.data.split(":")[2])

    await state.update_data(
        blacklist_telegram_id=telegram_id
    )

    await state.set_state(
        AdminStates.waiting_blacklist_reason
    )

    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "🚫 <b>Добавление в чёрный список</b>\n\n"
            "Напиши причину одним сообщением.\n\n"
            "Если причина не нужна — отправь <code>-</code>.",
            parse_mode="HTML",
        )


@router.message(AdminStates.waiting_blacklist_reason)
async def blacklist_reason(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    data = await state.get_data()

    telegram_id = data.get("blacklist_telegram_id")

    if not telegram_id:
        await state.clear()
        await message.answer("Ошибка: пользователь не найден.")
        return

    reason = message.text or ""

    if reason.strip() == "-":
        reason = None

    user = await blacklist_user(
        telegram_id=int(telegram_id),
        admin_id=message.from_user.id,
        reason=reason,
    )

    await state.clear()

    if user is None:
        await message.answer("❌ Пользователь не найден.")
        return

    await message.answer(
        "🚫 <b>Пользователь добавлен в ЧС.</b>\n\n"
        f"🆔 <code>{telegram_id}</code>\n"
        f"Причина: <b>{reason or 'не указана'}</b>",
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:unblacklist:"))
async def unblacklist_callback(
    callback: CallbackQuery,
) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    telegram_id = int(callback.data.split(":")[2])

    user = await unblacklist_user(
        telegram_id=telegram_id
    )

    if user is None:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return

    await callback.answer(
        "Пользователь возвращён на повторное одобрение"
    )

    if callback.message:
        await callback.message.edit_text(
            "♻️ <b>Пользователь убран из ЧС</b>\n\n"
            f"🆔 <code>{telegram_id}</code>\n\n"
            "Теперь он снова находится в статусе ожидания "
            "и должен получить одобрение администратора.",
            parse_mode="HTML",
        )
