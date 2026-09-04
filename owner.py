from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from config import ALL_PRIVILEGED_IDS

from keyboards import (
    owner_auto_keyboard,
    owner_candle_keyboard,
    owner_keyboard,
    owner_message_keyboard,
)

from messages import (
    DEFAULT_MESSAGES,
    render_message,
)

from settings_service import (
    get_message,
    get_setting,
    set_message,
)

from states import OwnerStates

from candle_filter import CandleFilter

from database import (
    JoinRequest,
    Signal,
    User,
    get_session,
)


logger = logging.getLogger(__name__)

router = Router()

candle_filter = CandleFilter()


def is_owner(
    telegram_id: int,
) -> bool:

    try:
        user_id = int(telegram_id)
    except (
        TypeError,
        ValueError,
    ):
        return False

    return user_id in {
        int(value)
        for value in ALL_PRIVILEGED_IDS
    }


async def owner_check(
    message: Message,
) -> bool:

    if message.from_user is None:
        return False

    return is_owner(
        message.from_user.id
    )


async def owner_callback_check(
    callback: CallbackQuery,
) -> bool:

    if callback.from_user is None:
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return False

    if not is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )
        return False

    return True


@router.message(
    F.text == "👑 Панель владельца"
)
async def owner_panel_message(
    message: Message,
) -> None:

    if not await owner_check(message):
        return

    await message.answer(
        render_message(
            "owner_panel"
        ),
        reply_markup=owner_keyboard(),
    )


@router.callback_query(
    F.data == "owner:panel"
)
async def owner_panel_callback(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    await callback.message.edit_text(
        render_message(
            "owner_panel"
        ),
        reply_markup=owner_keyboard(),
    )


@router.callback_query(
    F.data == "owner:messages"
)
async def owner_messages_callback(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    keys = list(
        DEFAULT_MESSAGES.keys()
    )

    await callback.message.edit_text(
        render_message(
            "owner_message_list"
        ),
        reply_markup=owner_message_keyboard(
            keys
        ),
    )


@router.callback_query(
    F.data.startswith("ownermsg:")
)
async def owner_message_select(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    key = callback.data.split(
        ":",
        1,
    )[1]

    if key not in DEFAULT_MESSAGES:
        await callback.message.answer(
            render_message(
                "owner_unknown_message"
            )
        )
        return

    current_text = await get_message(
        key
    )

    await state.update_data(
        message_key=key
    )

    await state.set_state(
        OwnerStates.waiting_message_text
    )

    await callback.message.answer(
        render_message(
            "owner_message_prompt",
            key=key,
            current_text=current_text,
        )
    )


@router.message(
    OwnerStates.waiting_message_text
)
async def owner_message_save(
    message: Message,
    state: FSMContext,
) -> None:

    if not await owner_check(message):
        await state.clear()
        return

    data = await state.get_data()

    key = data.get(
        "message_key"
    )

    if not key:
        await state.clear()
        return

    text = (
        message.text
        if message.text is not None
        else ""
    )

    if not text.strip():
        await message.answer(
            render_message(
                "owner_message_empty"
            )
        )
        return

    await set_message(
        key=key,
        text=text,
        updated_by=int(
            message.from_user.id
        ),
    )

    await state.clear()

    await message.answer(
        render_message(
            "owner_message_saved",
            key=key,
        ),
        reply_markup=owner_keyboard(),
    )


@router.callback_query(
    F.data == "owner:candles"
)
async def owner_candles_callback(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    settings = await candle_filter.get_settings()

    await callback.message.edit_text(
        render_message(
            "owner_candle_status",
            enabled=(
                "ВКЛ"
                if settings.enabled
                else "ВЫКЛ"
            ),
            count=settings.ignored_last_candles,
            expires_at=settings.expires_at,
        ),
        reply_markup=owner_candle_keyboard(),
    )


@router.callback_query(
    F.data.startswith("candle:")
)
async def owner_candle_callback(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    parts = callback.data.split(":")

    if (
        len(parts) == 2
        and parts[1] == "disable"
    ):
        await candle_filter.disable(
            updated_by=int(
                callback.from_user.id
            )
        )

        await callback.message.edit_text(
            render_message(
                "owner_candle_disabled"
            ),
            reply_markup=owner_candle_keyboard(),
        )

        return

    if len(parts) != 3:
        return

    try:
        count = int(parts[1])
        duration = int(parts[2])
    except ValueError:
        return

    await candle_filter.configure(
        ignored_last_candles=count,
        duration_minutes=duration,
        updated_by=int(
            callback.from_user.id
        ),
    )

    settings = await candle_filter.get_settings()

    await callback.message.edit_text(
        render_message(
            "owner_candle_saved",
            count=count,
            duration=duration,
            expires_at=settings.expires_at,
        ),
        reply_markup=owner_candle_keyboard(),
    )


@router.callback_query(
    F.data == "owner:auto"
)
async def owner_auto_callback(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    enabled = (
        await get_setting(
            "auto_signals.enabled",
            default="true",
        )
    ).lower() == "true"

    await callback.message.edit_text(
        render_message(
            "owner_auto",
            enabled=(
                "ВКЛ"
                if enabled
                else "ВЫКЛ"
            ),
        ),
        reply_markup=owner_auto_keyboard(
            enabled
        ),
    )


@router.callback_query(
    F.data == "owner:auto_toggle"
)
async def owner_auto_toggle(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    current = (
        await get_setting(
            "auto_signals.enabled",
            default="true",
        )
    ).lower() == "true"

    new_value = not current

    from settings_service import set_setting

    await set_setting(
        key="auto_signals.enabled",
        value=(
            "true"
            if new_value
            else "false"
        ),
        updated_by=int(
            callback.from_user.id
        ),
    )

    await callback.message.edit_text(
        render_message(
            "owner_auto",
            enabled=(
                "ВКЛ"
                if new_value
                else "ВЫКЛ"
            ),
        ),
        reply_markup=owner_auto_keyboard(
            new_value
        ),
    )


@router.callback_query(
    F.data == "owner:stats"
)
async def owner_stats_callback(
    callback: CallbackQuery,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    async with get_session() as session:

        users = await session.scalar(
            select(
                func.count(User.id)
            )
        )

        approved = await session.scalar(
            select(
                func.count(User.id)
            ).where(
                User.status == "approved"
            )
        )

        pending = await session.scalar(
            select(
                func.count(User.id)
            ).where(
                User.status == "pending"
            )
        )

        blacklisted = await session.scalar(
            select(
                func.count(User.id)
            ).where(
                User.status == "blacklisted"
            )
        )

        signals = await session.scalar(
            select(
                func.count(Signal.id)
            )
        )

        wins = await session.scalar(
            select(
                func.count(Signal.id)
            ).where(
                Signal.result == "win"
            )
        )

        losses = await session.scalar(
            select(
                func.count(Signal.id)
            ).where(
                Signal.result == "loss"
            )
        )

    completed = (
        int(wins or 0)
        + int(losses or 0)
    )

    winrate = (
        int(wins or 0)
        / completed
        * 100
        if completed
        else 0
    )

    await callback.message.edit_text(
        render_message(
            "owner_stats",
            users=int(users or 0),
            approved=int(approved or 0),
            pending=int(pending or 0),
            blacklisted=int(blacklisted or 0),
            signals=int(signals or 0),
            wins=int(wins or 0),
            losses=int(losses or 0),
            winrate=f"{winrate:.2f}%",
        ),
        reply_markup=owner_keyboard(),
    )


@router.callback_query(
    F.data == "owner:broadcast"
)
async def owner_broadcast_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not await owner_callback_check(
        callback
    ):
        return

    await callback.answer()

    if callback.message is None:
        return

    await state.set_state(
        OwnerStates.waiting_broadcast_text
    )

    await callback.message.answer(
        render_message(
            "owner_broadcast_prompt"
        )
    )


@router.message(
    OwnerStates.waiting_broadcast_text
)
async def owner_broadcast_message(
    message: Message,
    state: FSMContext,
) -> None:

    if not await owner_check(message):
        await state.clear()
        return

    text = (
        message.text
        if message.text
        else ""
    ).strip()

    if not text:
        await message.answer(
            render_message(
                "owner_broadcast_empty"
            )
        )
        return

    async with get_session() as session:

        result = await session.execute(
            select(User).where(
                User.status == "approved"
            )
        )

        users = list(
            result.scalars().all()
        )

    sent = 0

    for user in users:
        try:
            await message.bot.send_message(
                chat_id=int(
                    user.telegram_id
                ),
                text=text,
            )

            sent += 1

        except Exception:
            logger.exception(
                "Broadcast failed for %s",
                user.telegram_id,
            )

    await state.clear()

    await message.answer(
        render_message(
            "owner_broadcast_done",
            sent=sent,
            total=len(users),
        ),
        reply_markup=owner_keyboard(),
    )
