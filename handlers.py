from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import (
    MIN_SIGNAL_CONFIDENCE,
    MIN_SIGNAL_QUALITY,
)
from keyboards import (
    expiry_keyboard,
    main_keyboard,
    market_keyboard,
    pairs_keyboard,
    pending_keyboard,
)
from pair_selector import pair_selector
from services import request_access
from signal_scanner import SignalScanner
from signal_service import save_signal, broadcast_signal
from states import SignalStates
from time_utils import normalize_expiry


router = Router()


def user_info(message: Message) -> tuple[int, str | None, str | None]:
    if message.from_user is None:
        raise RuntimeError("Telegram user unavailable")

    return (
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    telegram_id, username, first_name = user_info(message)

    user, request = await request_access(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
    )

    if user.status == "approved":
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Доступ к сигналам активен.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    if user.status == "blacklisted":
        reason = user.blacklist_reason or "не указана"

        await message.answer(
            "🚫 <b>Доступ запрещён.</b>\n\n"
            f"Причина: <b>{reason}</b>",
            parse_mode="HTML",
        )
        return

    if user.status == "pending":
        await message.answer(
            "⏳ <b>Заявка ожидает одобрения.</b>\n\n"
            "Администратор должен подтвердить доступ.",
            parse_mode="HTML",
            reply_markup=pending_keyboard(),
        )
        return

    await message.answer(
        "❌ Доступ пока не одобрен.\n\n"
        "Можно отправить новую заявку позже.",
        reply_markup=pending_keyboard(),
    )


@router.message(lambda m: m.text == "🔄 Проверить доступ")
async def check_access(
    message: Message,
) -> None:
    telegram_id, username, first_name = user_info(message)

    user, _ = await request_access(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
    )

    if user.status == "approved":
        await message.answer(
            "✅ <b>Доступ одобрен!</b>\n\n"
            "Теперь можно получать сигналы.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    if user.status == "blacklisted":
        await message.answer(
            "🚫 Вы находитесь в чёрном списке.",
        )
        return

    await message.answer(
        "⏳ <b>Доступ ещё не одобрен.</b>\n\n"
        "Ожидайте решения администратора.",
        parse_mode="HTML",
        reply_markup=pending_keyboard(),
    )


@router.message(lambda m: m.text == "📡 Получить сигнал")
async def signal_start(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await state.set_state(
        SignalStates.choosing_market
    )

    await message.answer(
        "📡 <b>Получение сигнала</b>\n\n"
        "Выбери рынок:",
        parse_mode="HTML",
        reply_markup=market_keyboard(),
    )


@router.callback_query(
    SignalStates.choosing_market,
    lambda c: c.data.startswith("market:")
)
async def market_selected(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    market = callback.data.split(":", 1)[1]

    pairs = pair_selector.available_pairs(market)

    if not pairs:
        await callback.answer(
            "OTC сейчас недоступен: нет реального источника OTC-данных.",
            show_alert=True,
        )
        return

    await state.update_data(market=market)

    await state.set_state(
        SignalStates.choosing_pair
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "💱 <b>Выбери валютную пару:</b>",
            parse_mode="HTML",
            reply_markup=pairs_keyboard(pairs),
        )


@router.callback_query(
    SignalStates.choosing_pair,
    lambda c: c.data.startswith("pair:")
)
async def pair_selected(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    pair = callback.data.split(":", 1)[1]

    await state.update_data(pair=pair)

    await state.set_state(
        SignalStates.choosing_expiry
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            f"💱 Пара: <b>{pair}</b>\n\n"
            "⏱ Выбери время экспирации:",
            parse_mode="HTML",
            reply_markup=expiry_keyboard(),
        )


@router.callback_query(
    SignalStates.choosing_expiry,
    lambda c: c.data.startswith("expiry:")
)
async def expiry_selected(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    expiry_value = callback.data.split(":", 1)[1]

    expiry = normalize_expiry(expiry_value)

    data = await state.get_data()

    pair = data.get("pair")
    market = data.get("market")

    if not pair:
        await callback.answer(
            "Пара не выбрана.",
            show_alert=True,
        )
        return

    if not pair_selector.is_allowed(pair, market):
        await callback.answer(
            "Эта пара недоступна для выбранного рынка.",
            show_alert=True,
        )
        return

    await callback.answer(
        "🔎 Анализирую рынок..."
    )

    if callback.message:
        await callback.message.edit_text(
            "🔎 <b>Анализ рынка...</b>\n\n"
            f"💱 Пара: <b>{pair}</b>\n"
            f"⏱ Экспирация: <b>{expiry} мин.</b>\n\n"
            "Проверяю индикаторы и качество сигнала.",
            parse_mode="HTML",
        )

    scanner = SignalScanner()

    candidate = await scanner.scan_pair(
        pair=pair,
        expiry_minutes=expiry,
        source="manual",
    )

    await state.clear()

    if candidate is None:
        if callback.message:
            await callback.message.answer(
                "⚪ <b>Сильного сигнала сейчас нет.</b>\n\n"
                f"💱 {pair}\n"
                f"📊 Минимальная уверенность: "
                f"{MIN_SIGNAL_CONFIDENCE}%\n"
                f"⭐ Минимальное качество: "
                f"{MIN_SIGNAL_QUALITY}%\n\n"
                "Слабый сигнал специально не выдаю.",
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
        return

    signal = await save_signal(candidate)

    if callback.message:
        await callback.message.answer(
            "✅ <b>Сигнал найден!</b>\n\n"
            f"💱 Пара: <b>{signal.pair}</b>\n"
            f"📊 Направление: "
            f"<b>{signal.direction}</b>\n"
            f"⏱ Экспирация: "
            f"<b>{signal.expiry_minutes} мин.</b>\n"
            f"🎯 Уверенность: "
            f"<b>{signal.confidence:.1f}%</b>\n"
            f"⭐ Качество: "
            f"<b>{signal.quality:.1f}%</b>\n"
            f"💰 Вход: <b>{signal.entry_price}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )


@router.callback_query(lambda c: c.data == "signal:cancel")
async def signal_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer("Отменено")

    if callback.message:
        await callback.message.edit_text(
            "❌ Получение сигнала отменено."
        )


@router.callback_query(lambda c: c.data == "signal:back_market")
async def back_market(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(
        SignalStates.choosing_market
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "📡 <b>Выбери рынок:</b>",
            parse_mode="HTML",
            reply_markup=market_keyboard(),
        )


@router.callback_query(lambda c: c.data == "signal:back_pair")
async def back_pair(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    market = data.get("market")

    if not market:
        await callback.answer(
            "Рынок не выбран.",
            show_alert=True,
        )
        return

    await state.set_state(
        SignalStates.choosing_pair
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "💱 <b>Выбери валютную пару:</b>",
            parse_mode="HTML",
            reply_markup=pairs_keyboard(
                pair_selector.available_pairs(market)
            ),
        )


@router.message(lambda m: m.text == "📜 История")
async def history_handler(
    message: Message,
) -> None:
    await message.answer(
        "📜 История сигналов будет подключена "
        "в следующем модуле."
    )


@router.message(lambda m: m.text == "📊 Статистика")
async def stats_handler(
    message: Message,
) -> None:
    await message.answer(
        "📊 Статистика будет подключена "
        "в следующем модуле."
    )


@router.message(lambda m: m.text == "⚙️ Настройки")
async def settings_handler(
    message: Message,
) -> None:
    await message.answer(
        "⚙️ Настройки будут подключены "
        "в следующем модуле."
    )
