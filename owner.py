from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from candle_control import (
    candle_filter_status,
    disable_candle_filter,
    set_candle_filter,
)
from database import (
    User,
    get_session,
)
from keyboards import (
    owner_candles_keyboard,
    owner_keyboard,
    owner_texts_keyboard,
)
from messages import (
    DEFAULT_TEXTS,
    get_text,
    set_text,
)
from states import OwnerStates


router = Router()


def is_owner(
    telegram_id: int,
) -> bool:
    return telegram_id in ADMIN_IDS


@router.message(
    lambda message:
    message.text == "👑 Owner"
)
async def owner_menu_message(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    if not is_owner(
        message.from_user.id
    ):
        return

    await message.answer(
        "👑 <b>OWNER PANEL</b>",
        parse_mode="HTML",
        reply_markup=owner_keyboard(),
    )


@router.callback_query(
    lambda callback:
    callback.data == "owner:back"
)
async def owner_back(
    callback: CallbackQuery,
) -> None:
    if not is_owner(
        callback.from_user.id
    ):
        return

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "👑 <b>OWNER PANEL</b>",
            parse_mode="HTML",
            reply_markup=owner_keyboard(),
        )


@router.callback_query(
    lambda callback:
    callback.data == "owner:texts"
)
async def owner_texts(
    callback: CallbackQuery,
) -> None:
    if not is_owner(
        callback.from_user.id
    ):
        return

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "📝 <b>Редактор сообщений</b>\n\n"
            "Выбери сообщение:",
            parse_mode="HTML",
            reply_markup=owner_texts_keyboard(
                list(DEFAULT_TEXTS.keys())
            ),
        )


@router.callback_query(
    lambda callback:
    callback.data.startswith(
        "owner_text:"
    )
)
async def select_text(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not is_owner(
        callback.from_user.id
    ):
        return

    key = callback.data.split(
        ":",
        1,
    )[1]

    current = await get_text(key)

    await state.update_data(
        editing_text_key=key
    )

    await state.set_state(
        OwnerStates.editing_text
    )

    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "📝 <b>Редактирование</b>\n\n"
            f"Ключ: <code>{key}</code>\n\n"
            "Текущий текст:\n\n"
            f"{current}\n\n"
            "Отправь новый текст одним сообщением.",
            parse_mode="HTML",
        )


@router.message(
    OwnerStates.editing_text
)
async def save_edited_text(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not is_owner(
        message.from_user.id
    ):
        await state.clear()
        return

    data = await state.get_data()

    key = data.get(
        "editing_text_key"
    )

    if not key:
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "❌ Текст не может быть пустым."
        )
        return

    await set_text(
        key,
        message.text,
    )

    await state.clear()

    await message.answer(
        "✅ Текст сохранён."
    )


@router.callback_query(
    lambda callback:
    callback.data == "owner:candles"
)
async def owner_candles(
    callback: CallbackQuery,
) -> None:
    if not is_owner(
        callback.from_user.id
    ):
        return

    status = candle_filter_status()

    if status["enabled"]:
        status_text = (
            f"🟡 Сейчас исключены последние "
            f"<b>{status['ignored_last_candles']}</b> свечей."
        )
    else:
        status_text = (
            "🟢 Сейчас учитываются все свечи."
        )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "🕯 <b>Управление свечами</b>\n\n"
            f"{status_text}\n\n"
            "Настройка действует временно.",
            parse_mode="HTML",
            reply_markup=owner_candles_keyboard(),
        )


@router.callback_query(
    lambda callback:
    callback.data.startswith("candle:")
)
async def candle_action(
    callback: CallbackQuery,
) -> None:
    if not is_owner(
        callback.from_user.id
    ):
        return

    _, amount, duration = (
        callback.data.split(":")
    )

    amount = int(amount)
    duration = int(duration)

    if amount == 0:
        disable_candle_filter()

        await callback.answer(
            "Все свечи снова учитываются."
        )

    else:
        set_candle_filter(
            amount,
            duration,
        )

        await callback.answer(
            f"Исключены последние {amount} свечей "
            f"на {duration} минут."
        )


@router.callback_query(
    lambda callback:
    callback.data == "owner:users"
)
async def owner_users(
    callback: CallbackQuery,
) -> None:
    if not is_owner(
        callback.from_user.id
    ):
        return

    async with get_session() as session:
        from sqlalchemy import func
        from database import User

        result = await session.execute(
            func.count(
                User.id
            ).select()
        )

        total = result.scalar() or 0

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "👥 <b>Пользователи</b>\n\n"
            f"Всего зарегистрировано: "
            f"<b>{total}</b>",
            parse_mode="HTML",
            reply_markup=owner_keyboard(),
        )
