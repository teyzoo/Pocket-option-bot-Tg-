from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, OWNER_IDS
from database import User
from keyboards import admin_request_keyboard
from messages import render_message
from services import (
    approve_user,
    blacklist_user,
    get_pending_requests,
    reject_user,
    unblacklist_user,
)
from states import AdminStates

logger = logging.getLogger(__name__)

router = Router()


def is_admin(telegram_id: int) -> bool:
    return (
        int(telegram_id) in ADMIN_IDS
        or int(telegram_id) in OWNER_IDS
    )


def admin_required(
    telegram_id: int,
) -> bool:
    return is_admin(telegram_id)


@router.message(Command("admin"))
async def admin_command(
    message: Message,
) -> None:
    if not is_admin(
        int(message.from_user.id)
    ):
        return

    await show_pending_requests(
        message
    )


@router.callback_query(
    F.data == "owner:requests"
)
async def owner_requests_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(
        int(callback.from_user.id)
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return

    await callback.answer()

    await show_pending_requests(
        callback.message
    )


async def show_pending_requests(
    message: Message,
) -> None:
    requests = await get_pending_requests()

    if not requests:
        await message.answer(
            render_message(
                "admin_no_requests"
            )
        )
        return

    await message.answer(
        render_message(
            "admin_requests_header",
            count=len(requests),
        )
    )

    for request in requests:
        username = (
            f"@{request.username}"
            if request.username
            else "нет username"
        )

        text = render_message(
            "admin_request",
            telegram_id=request.telegram_id,
            username=username,
            first_name=request.first_name or "—",
            created_at=request.created_at,
        )

        await message.answer(
            text,
            reply_markup=admin_request_keyboard(
                request.telegram_id
            ),
        )


@router.callback_query(
    F.data.startswith("admin:approve:")
)
async def approve_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(
        int(callback.from_user.id)
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return

    await callback.answer()

    telegram_id = _extract_telegram_id(
        callback.data
    )

    if telegram_id is None:
        return

    user = await approve_user(
        telegram_id=telegram_id,
        processed_by=int(
            callback.from_user.id
        ),
    )

    if user is None:
        await callback.message.answer(
            render_message(
                "admin_user_not_found"
            )
        )
        return

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        render_message(
            "admin_approved",
            telegram_id=telegram_id,
        )
    )

    try:
        await callback.bot.send_message(
            chat_id=telegram_id,
            text=render_message(
                "access_approved"
            ),
        )
    except Exception:
        logger.exception(
            "Failed to notify approved user %s",
            telegram_id,
        )


@router.callback_query(
    F.data.startswith("admin:reject:")
)
async def reject_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(
        int(callback.from_user.id)
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return

    await callback.answer()

    telegram_id = _extract_telegram_id(
        callback.data
    )

    if telegram_id is None:
        return

    user = await reject_user(
        telegram_id=telegram_id,
        processed_by=int(
            callback.from_user.id
        ),
    )

    if user is None:
        await callback.message.answer(
            render_message(
                "admin_user_not_found"
            )
        )
        return

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        render_message(
            "admin_rejected",
            telegram_id=telegram_id,
        )
    )

    try:
        await callback.bot.send_message(
            chat_id=telegram_id,
            text=render_message(
                "access_rejected"
            ),
        )
    except Exception:
        logger.exception(
            "Failed to notify rejected user %s",
            telegram_id,
        )


@router.callback_query(
    F.data.startswith("admin:blacklist:")
)
async def blacklist_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not is_admin(
        int(callback.from_user.id)
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return

    await callback.answer()

    telegram_id = _extract_telegram_id(
        callback.data
    )

    if telegram_id is None:
        return

    await state.update_data(
        blacklist_telegram_id=telegram_id
    )

    await state.set_state(
        AdminStates.waiting_blacklist_reason
    )

    await callback.message.answer(
        render_message(
            "admin_blacklist_prompt",
            telegram_id=telegram_id,
        )
    )


@router.message(
    AdminStates.waiting_blacklist_reason
)
async def blacklist_reason_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(
        int(message.from_user.id)
    ):
        await state.clear()
        return

    data = await state.get_data()

    telegram_id = data.get(
        "blacklist_telegram_id"
    )

    if not telegram_id:
        await state.clear()
        return

    reason = (
        message.text.strip()
        if message.text
        else "Без указания причины"
    )

    user = await blacklist_user(
        telegram_id=int(telegram_id),
        reason=reason,
        processed_by=int(
            message.from_user.id
        ),
    )

    await state.clear()

    if user is None:
        await message.answer(
            render_message(
                "admin_user_not_found"
            )
        )
        return

    await message.answer(
        render_message(
            "admin_blacklisted",
            telegram_id=telegram_id,
            reason=reason,
        )
    )

    try:
        await message.bot.send_message(
            chat_id=int(telegram_id),
            text=render_message(
                "access_blacklisted",
                reason=reason,
            ),
        )
    except Exception:
        logger.exception(
            "Failed to notify blacklisted user %s",
            telegram_id,
        )


@router.callback_query(
    F.data.startswith("admin:unblacklist:")
)
async def unblacklist_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(
        int(callback.from_user.id)
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return

    await callback.answer()

    telegram_id = _extract_telegram_id(
        callback.data
    )

    if telegram_id is None:
        return

    user = await unblacklist_user(
        telegram_id=telegram_id,
        processed_by=int(
            callback.from_user.id
        ),
    )

    if user is None:
        await callback.message.answer(
            render_message(
                "admin_user_not_found"
            )
        )
        return

    await callback.message.answer(
        render_message(
            "admin_unblacklisted",
            telegram_id=telegram_id,
        )
    )

    try:
        await callback.bot.send_message(
            chat_id=telegram_id,
            text=render_message(
                "access_pending_again"
            ),
        )
    except Exception:
        logger.exception(
            "Failed to notify unblacklisted user %s",
            telegram_id,
        )


def _extract_telegram_id(
    callback_data: str | None,
) -> int | None:
    if not callback_data:
        return None

    parts = callback_data.split(":")

    if len(parts) != 3:
        return None

    try:
        return int(parts[2])
    except ValueError:
        return None
