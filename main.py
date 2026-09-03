from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from fastapi import FastAPI
from sqlalchemy import select

from config import (
    ADMIN_IDS,
    BOT_NAME,
    HOST,
    PORT,
    USER_STATUS_APPROVED,
    USER_STATUS_BLACKLISTED,
    USER_STATUS_PENDING,
    USER_STATUS_REJECTED,
)
from database import (
    JoinRequest,
    SessionLocal,
    User,
    create_join_request,
    get_or_create_user,
    init_db,
)
from keyboards import (
    admin_request_keyboard,
    blacklist_keyboard,
    expiry_keyboard,
    main_keyboard,
    otc_pairs_keyboard,
    pending_keyboard,
    regular_pairs_keyboard,
    signal_type_keyboard,
)
from market import MarketClient
from signal_engine import SignalEngine
from signal_result_checker import SignalResultChecker
from signal_scanner import SignalScanner
from scheduler import SignalScheduler


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


bot = Bot(
    token=__import__("config").BOT_TOKEN,
)

dp = Dispatcher()

market = MarketClient()
engine = SignalEngine()
scanner = SignalScanner(
    market=market,
    engine=engine,
)

scheduler = SignalScheduler(
    bot=bot,
    scanner=scanner,
)

result_checker = SignalResultChecker(
    market=market,
)

app = FastAPI(
    title=BOT_NAME,
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": BOT_NAME,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "bot": BOT_NAME,
    }


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def get_current_user(
    telegram_user,
) -> User:
    async with SessionLocal() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
        )

        return user


async def request_access(
    message: Message,
) -> None:
    telegram_user = message.from_user

    if telegram_user is None:
        return

    async with SessionLocal() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
        )

        if user.status == USER_STATUS_APPROVED:
            await message.answer(
                "✅ У вас уже есть доступ.",
                reply_markup=main_keyboard(),
            )
            return

        if user.status == USER_STATUS_BLACKLISTED:
            await message.answer(
                "🚫 Вы находитесь в чёрном списке.\n\n"
                "Доступ к боту заблокирован."
            )
            return

        if user.status == USER_STATUS_REJECTED:
            user.status = USER_STATUS_PENDING
            await session.commit()

        request = await create_join_request(
            session=session,
            telegram_id=telegram_user.id,
        )

        if request is None:
            await message.answer(
                "⏳ Ваша заявка уже находится "
                "на рассмотрении.",
                reply_markup=pending_keyboard(),
            )
            return

    await message.answer(
        "⏳ <b>Заявка отправлена.</b>\n\n"
        "Ожидайте одобрения администратора.",
        reply_markup=pending_keyboard(),
    )

    admin_text = (
        "👤 <b>НОВАЯ ЗАЯВКА</b>\n\n"
        f"🆔 ID: <code>{telegram_user.id}</code>\n"
        f"👤 Имя: "
        f"{telegram_user.full_name}\n"
        f"🔗 Username: "
        f"@{telegram_user.username}"
        if telegram_user.username
        else (
            "👤 <b>НОВАЯ ЗАЯВКА</b>\n\n"
            f"🆔 ID: <code>{telegram_user.id}</code>\n"
            f"👤 Имя: "
            f"{telegram_user.full_name}\n"
            "🔗 Username: отсутствует"
        )
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=admin_request_keyboard(
                    telegram_user.id
                ),
            )
        except Exception:
            logger.exception(
                "Не удалось уведомить администратора"
            )


@dp.message(CommandStart())
async def start_handler(
    message: Message,
) -> None:
    user = await get_current_user(
        message.from_user
    )

    if user.status == USER_STATUS_APPROVED:
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Выберите действие:",
            reply_markup=main_keyboard(),
        )
        return

    if user.status == USER_STATUS_BLACKLISTED:
        await message.answer(
            "🚫 <b>Доступ заблокирован.</b>\n\n"
            "Вы находитесь в чёрном списке."
        )
        return

    if user.status == USER_STATUS_PENDING:
        await request_access(message)
        return

    await request_access(message)


@dp.message(Command("admin"))
async def admin_handler(
    message: Message,
) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Здесь будут управление заявками, "
        "пользователями и чёрным списком."
    )


@dp.callback_query(F.data == "check_access")
async def check_access(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    async with SessionLocal() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        status = user.status

    if status == USER_STATUS_APPROVED:
        await callback.message.edit_text(
            "✅ <b>Доступ одобрен!</b>\n\n"
            "Теперь вы можете получать сигналы.",
            reply_markup=main_keyboard(),
        )

    elif status == USER_STATUS_BLACKLISTED:
        await callback.message.edit_text(
            "🚫 <b>Доступ заблокирован.</b>"
        )

    else:
        await callback.message.edit_text(
            "⏳ <b>Заявка ещё рассматривается.</b>\n\n"
            "Попробуйте проверить доступ позже.",
            reply_markup=pending_keyboard(),
        )


@dp.callback_query(F.data == "signal:start")
async def signal_start(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    async with SessionLocal() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

        if user.status != USER_STATUS_APPROVED:
            await callback.message.edit_text(
                "🚫 У вас пока нет доступа.",
                reply_markup=pending_keyboard(),
            )
            return

    await callback.message.edit_text(
        "📊 <b>Выберите тип рынка:</b>",
        reply_markup=signal_type_keyboard(),
    )


@dp.callback_query(F.data == "signal_type:regular")
async def signal_regular(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    pairs = scanner.get_available_pairs(
        "regular"
    )

    await callback.message.edit_text(
        "🌐 <b>Обычные пары</b>\n\n"
        "Выберите конкретную пару "
        "или случайную доступную пару:",
        reply_markup=regular_pairs_keyboard(
            pairs
        ),
    )


@dp.callback_query(F.data == "signal_type:otc")
async def signal_otc(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    # Сейчас OTC специально пустой:
    # бот не подделывает OTC-котировки.
    await callback.message.edit_text(
        "🟣 <b>OTC</b>\n\n"
        "⚠️ Реальный OTC-источник пока "
        "не подключён.\n\n"
        "Поэтому бот не выдаёт фиктивные "
        "OTC-сигналы.",
        reply_markup=otc_pairs_keyboard([]),
    )


@dp.callback_query(F.data == "signal_type:any")
async def signal_any(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    pairs = scanner.get_available_pairs(
        "any"
    )

    await callback.message.edit_text(
        "🔀 <b>Любая доступная пара</b>\n\n"
        "Будет выбрана только пара из "
        "разрешённого списка.",
        reply_markup=regular_pairs_keyboard(
            pairs
        ),
    )


@dp.callback_query(F.data.startswith("pair:"))
async def pair_selected(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    pair = callback.data.split(
        ":",
        1,
    )[1]

    if pair == "any_regular":
        await callback.message.edit_text(
            "🔀 <b>Любая обычная пара</b>\n\n"
            "Выберите время экспирации:",
            reply_markup=expiry_keyboard(),
        )
        return

    if pair == "any_otc":
        await callback.message.edit_text(
            "⚠️ Реальные OTC-котировки "
            "пока не подключены."
        )
        return

    await callback.message.edit_text(
        f"💱 Пара: <b>{pair}</b>\n\n"
        "Выберите время экспирации:",
        reply_markup=expiry_keyboard(),
    )


@dp.callback_query(F.data.startswith("expiry:"))
async def expiry_selected(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    expiry = callback.data.split(
        ":",
        1,
    )[1]

    if expiry == "any":
        await callback.message.edit_text(
            "⚡ <b>Любое время</b>\n\n"
            "Бот сам выберет подходящую "
            "экспирацию от 1 до 20 минут.\n\n"
            "🔎 Ищу сильный сигнал..."
        )

        # В будущем здесь можно использовать
        # оптимальный expiry из анализа.
        selected_expiry = 5

    else:
        selected_expiry = int(expiry)

        await callback.message.edit_text(
            f"⏱ Экспирация: "
            f"<b>{selected_expiry} мин</b>\n\n"
            "🔎 Ищу сильный сигнал..."
        )

    signal = await scanner.scan(
        expiry_minutes=selected_expiry,
        source="manual",
    )

    if not signal:
        await callback.message.edit_text(
            "⚪ <b>Сильного сигнала сейчас нет.</b>\n\n"
            "Я не буду выдавать слабый сигнал "
            "только ради того, чтобы что-то показать.",
            reply_markup=main_keyboard(),
        )
        return

    direction = (
        "🟢 ВВЕРХ ⬆️"
        if signal.direction == "UP"
        else "🔴 ВНИЗ ⬇️"
    )

    reasons = "\n".join(
        f"• {item}"
        for item in signal.reasons[:8]
    )

    await callback.message.edit_text(
        "🚨 <b>СИГНАЛ НАЙДЕН</b>\n\n"
        f"💱 Пара: <b>{signal.pair}</b>\n"
        f"📊 Направление: <b>{direction}</b>\n"
        f"⏱ Время: "
        f"<b>{signal.expiry_minutes} мин</b>\n"
        f"🎯 Уверенность: "
        f"<b>{signal.confidence:.1f}%</b>\n"
        f"⭐ Качество: "
        f"<b>{signal.quality:.1f}%</b>\n"
        f"💵 Вход: "
        f"<b>{signal.entry_price:.5f}</b>\n\n"
        "<b>Подтверждения:</b>\n"
        f"{reasons}\n\n"
        "⚠️ Аналитический сигнал, "
        "не гарантия результата.",
        reply_markup=main_keyboard(),
    )


@dp.callback_query(
    F.data.startswith("admin:")
)
async def admin_action(
    callback: CallbackQuery,
) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer()
        return

    action = parts[1]
    telegram_id = int(parts[2])

    async with SessionLocal() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=telegram_id,
        )

        if action == "approve":
            user.status = USER_STATUS_APPROVED
            user.blacklist_reason = None

            result = await session.execute(
                select(JoinRequest)
                .where(
                    JoinRequest.telegram_id
                    == telegram_id,
                    JoinRequest.status
                    == "pending",
                )
            )

            for request in result.scalars().all():
                request.status = "approved"
                request.processed_at = (
                    __import__(
                        "datetime"
                    ).datetime.now(
                        __import__(
                            "datetime"
                        ).timezone.utc
                    )
                )
                request.processed_by = (
                    callback.from_user.id
                )

            await session.commit()

            await callback.message.edit_text(
                callback.message.text
                + "\n\n✅ <b>ОДОБРЕНО</b>"
            )

            try:
                await bot.send_message(
                    telegram_id,
                    "🎉 <b>Ваша заявка одобрена!</b>\n\n"
                    "Теперь вы можете пользоваться "
                    "ботом и получать сигналы.",
                    reply_markup=main_keyboard(),
                )
            except Exception:
                pass

            await callback.answer(
                "Пользователь одобрен."
            )
            return

        if action == "reject":
            user.status = USER_STATUS_REJECTED

            await session.commit()

            await callback.message.edit_text(
                callback.message.text
                + "\n\n❌ <b>ОТКЛОНЕНО</b>"
            )

            try:
                await bot.send_message(
                    telegram_id,
                    "❌ Ваша заявка была отклонена."
                )
            except Exception:
                pass

            await callback.answer(
                "Заявка отклонена."
            )
            return

        if action == "blacklist":
            user.status = USER_STATUS_BLACKLISTED
            user.blacklist_reason = (
                "Заблокирован администратором"
            )
            user.is_auto_signals_enabled = False

            await session.commit()

            await callback.message.edit_text(
                callback.message.text
                + "\n\n🚫 <b>ДОБАВЛЕН В ЧЁРНЫЙ СПИСОК</b>",
                reply_markup=blacklist_keyboard(
                    telegram_id
                ),
            )

            try:
                await bot.send_message(
                    telegram_id,
                    "🚫 <b>Вы добавлены "
                    "в чёрный список.</b>\n\n"
                    "Доступ к боту заблокирован."
                )
            except Exception:
                pass

            await callback.answer(
                "Пользователь добавлен в ЧС."
            )
            return

        if action == "unblacklist":
            user.status = USER_STATUS_PENDING
            user.blacklist_reason = None

            await session.commit()

            await callback.message.edit_text(
                callback.message.text
                + "\n\n🔓 <b>УДАЛЁН ИЗ ЧС</b>"
            )

            try:
                await bot.send_message(
                    telegram_id,
                    "🔓 Вы удалены из чёрного списка.\n\n"
                    "Теперь необходимо дождаться "
                    "повторного одобрения заявки."
                )
            except Exception:
                pass

            await callback.answer(
                "Пользователь удалён из ЧС."
            )
            return


@dp.callback_query(F.data == "main")
async def main_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=main_keyboard(),
    )


@dp.callback_query(F.data == "history")
async def history_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "📊 <b>История сигналов</b>\n\n"
        "Раздел будет заполняться "
        "по мере появления сигналов.",
        reply_markup=main_keyboard(),
    )


@dp.callback_query(F.data == "stats")
async def stats_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    async with SessionLocal() as session:
        from database import Signal

        result = await session.execute(
            select(Signal)
        )

        signals = list(
            result.scalars().all()
        )

    total = len(signals)
    wins = sum(
        1
        for signal in signals
        if signal.result == "win"
    )
    losses = sum(
        1
        for signal in signals
        if signal.result == "loss"
    )

    completed = wins + losses

    winrate = (
        wins / completed * 100
        if completed
        else 0
    )

    await callback.message.edit_text(
        "📈 <b>Статистика</b>\n\n"
        f"Всего сигналов: <b>{total}</b>\n"
        f"🟢 WIN: <b>{wins}</b>\n"
        f"🔴 LOSS: <b>{losses}</b>\n"
        f"🎯 WINRATE: <b>{winrate:.1f}%</b>",
        reply_markup=main_keyboard(),
    )


@dp.callback_query(F.data == "settings")
async def settings_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Автоматические сигналы будут "
        "настраиваться здесь.",
        reply_markup=main_keyboard(),
    )


async def run_bot() -> None:
    await init_db()

    await scheduler.start()
    await result_checker.start()

    try:
        await dp.start_polling(
            bot
        )
    finally:
        await result_checker.stop()
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(
        run_bot()
    )
