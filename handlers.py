from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import (
    ADMIN_IDS,
    OWNER_IDS,
    SIGNAL_RESULT_DRAW,
    SIGNAL_RESULT_LOSS,
    SIGNAL_RESULT_WIN,
)
from database import (
    User,
    get_session,
)
from keyboards import (
    back_to_main_keyboard,
    expiry_keyboard,
    main_menu_keyboard,
    market_keyboard,
    pair_keyboard,
    settings_keyboard,
)
from messages import render_message
from market import market_client
from signal_engine import SignalEngine
from signal_result_notifications import get_user_result_statistics
from signal_scanner import SignalScanner
from signal_service import get_user_signal_history
from states import SignalStates
from services import (
    get_user_access_status,
    request_access,
    set_auto_signals,
)
from utils import (
    format_datetime,
    format_pair,
    format_price,
)

logger = logging.getLogger(__name__)

router = Router()

# ---------------------------------------------------------------------------
# Signal scanner
# ---------------------------------------------------------------------------
#
# SignalScanner требует MarketClient и SignalEngine.
# Раньше здесь было:
#
#     scanner = SignalScanner()
#
# что вызывало:
#
#     TypeError: SignalScanner.__init__() missing 2 required positional arguments
#
# Используем уже существующий singleton market_client.
# ---------------------------------------------------------------------------

scanner = SignalScanner(
    market=market_client,
    engine=SignalEngine(),
)


# ---------------------------------------------------------------------------
# Access helpers
# ---------------------------------------------------------------------------

def is_owner(telegram_id: int) -> bool:
    return int(telegram_id) in OWNER_IDS


def is_admin(telegram_id: int) -> bool:
    return (
        int(telegram_id) in ADMIN_IDS
        or is_owner(telegram_id)
    )


async def get_current_user(
    telegram_id: int,
) -> User | None:
    async with get_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(
                User.telegram_id == int(telegram_id)
            )
        )

        return result.scalar_one_or_none()


async def require_approved(
    message: Message,
) -> bool:
    telegram_id = int(message.from_user.id)

    status = await get_user_access_status(
        telegram_id
    )

    if status == "approved":
        return True

    if status == "blacklisted":
        await message.answer(
            render_message(
                "start_blacklisted"
            )
        )
        return False

    if status == "pending":
        await message.answer(
            render_message(
                "start_pending"
            )
        )
        return False

    await message.answer(
        render_message(
            "access_required"
        ),
        reply_markup=back_to_main_keyboard(),
    )

    return False


async def _callback_approved(
    callback: CallbackQuery,
) -> bool:
    status = await get_user_access_status(
        int(callback.from_user.id)
    )

    if status == "approved":
        return True

    if status == "blacklisted":
        await callback.message.answer(
            render_message(
                "start_blacklisted"
            )
        )
    else:
        await callback.message.answer(
            render_message(
                "access_required"
            )
        )

    return False


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    telegram_id = int(
        message.from_user.id
    )

    status = await get_user_access_status(
        telegram_id
    )

    if status == "blacklisted":
        await message.answer(
            render_message(
                "start_blacklisted"
            )
        )
        return

    if status == "approved":
        await message.answer(
            render_message(
                "start_approved",
                name=(
                    message.from_user.first_name
                    or "пользователь"
                ),
            ),
            reply_markup=main_menu_keyboard(
                is_owner=is_owner(telegram_id)
            ),
        )
        return

    if status == "pending":
        await message.answer(
            render_message(
                "start_pending"
            )
        )
        return

    request = await request_access(
        telegram_id=telegram_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if request.status == "pending":
        await message.answer(
            render_message(
                "access_request_sent"
            )
        )
        return

    if request.status == "blacklisted":
        await message.answer(
            render_message(
                "start_blacklisted"
            )
        )
        return

    await message.answer(
        render_message(
            "start_pending"
        )
    )


# ---------------------------------------------------------------------------
# Find signal
# ---------------------------------------------------------------------------

@router.message(
    F.text == "🔎 Найти сигнал"
)
async def find_signal_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_approved(message):
        return

    await state.clear()

    await state.set_state(
        SignalStates.choosing_market
    )

    await message.answer(
        render_message(
            "signal_choose_market"
        ),
        reply_markup=market_keyboard(),
    )


@router.callback_query(
    F.data == "menu:signal"
)
async def menu_signal_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    if not await _callback_approved(callback):
        return

    await state.clear()

    await state.set_state(
        SignalStates.choosing_market
    )

    await callback.message.edit_text(
        render_message(
            "signal_choose_market"
        ),
        reply_markup=market_keyboard(),
    )


# ---------------------------------------------------------------------------
# Market selection
# ---------------------------------------------------------------------------

@router.callback_query(
    F.data.startswith("market:")
)
async def choose_market_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    if not await _callback_approved(callback):
        return

    market = callback.data.split(
        ":",
        1,
    )[1]

    if market == "otc":
        await callback.message.edit_text(
            render_message(
                "otc_unavailable"
            ),
            reply_markup=market_keyboard(),
        )
        return

    await state.update_data(
        market=market
    )

    await state.set_state(
        SignalStates.choosing_pair
    )

    await callback.message.edit_text(
        render_message(
            "choose_pair"
        ),
        reply_markup=pair_keyboard(),
    )


# ---------------------------------------------------------------------------
# Pair selection
# ---------------------------------------------------------------------------

@router.callback_query(
    F.data.startswith("pair:")
)
async def choose_pair_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    if not await _callback_approved(callback):
        return

    encoded_pair = callback.data.split(
        ":",
        1,
    )[1]

    pair = _decode_pair(
        encoded_pair
    )

    if pair is None:
        await callback.message.answer(
            render_message(
                "generic_error"
            )
        )
        return

    await state.update_data(
        pair=pair
    )

    await state.set_state(
        SignalStates.choosing_expiry
    )

    await callback.message.edit_text(
        render_message(
            "choose_expiry"
        ),
        reply_markup=expiry_keyboard(),
    )


# ---------------------------------------------------------------------------
# Expiry selection
# ---------------------------------------------------------------------------

@router.callback_query(
    F.data.startswith("expiry:")
)
async def choose_expiry_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    if not await _callback_approved(callback):
        return

    value = callback.data.split(
        ":",
        1,
    )[1]

    if value == "any":
        expiry: int | str = "any"
    else:
        try:
            expiry = int(value)
        except ValueError:
            await callback.message.answer(
                render_message(
                    "generic_error"
                )
            )
            return

    # ---------------------------------------------------------------
    # Защита диапазона срока.
    # ---------------------------------------------------------------

    if isinstance(expiry, int):
        if expiry < 1 or expiry > 20:
            await callback.message.answer(
                render_message(
                    "generic_error"
                )
            )
            return

    data = await state.get_data()

    pair = data.get("pair")
    market = data.get(
        "market",
        "regular",
    )

    if not pair:
        await callback.message.answer(
            render_message(
                "generic_error"
            )
        )
        return

    await state.set_state(
        SignalStates.analyzing
    )

    await callback.message.edit_text(
        render_message(
            "analyzing",
            pair=format_pair(pair),
            expiry=(
                "любое время"
                if expiry == "any"
                else f"{expiry} мин"
            ),
        )
    )

    try:
        # -----------------------------------------------------------
        # Обычный срок.
        # -----------------------------------------------------------

        if isinstance(expiry, int):
            candidate = await scanner.scan_pair(
                pair=pair,
                expiry_minutes=expiry,
                market=market,
                source="manual",
            )

        # -----------------------------------------------------------
        # "Любое время":
        #
        # перебираем все сроки 1..20 минут и выбираем лучший
        # найденный сигнал.
        #
        # Важно: здесь НЕ передаётся строка "any" в SignalEngine.
        # -----------------------------------------------------------

        else:
            expiry_candidates = range(
                1,
                21,
            )

            async def scan_expiry(
                expiry_minutes: int,
            ):
                try:
                    return await scanner.scan_pair(
                        pair=pair,
                        expiry_minutes=expiry_minutes,
                        market=market,
                        source="manual",
                    )
                except Exception:
                    logger.exception(
                        "Expiry scan failed: "
                        "pair=%s expiry=%s",
                        pair,
                        expiry_minutes,
                    )
                    return None

            results = await asyncio.gather(
                *(
                    scan_expiry(
                        expiry_minutes
                    )
                    for expiry_minutes in expiry_candidates
                )
            )

            candidates = [
                result
                for result in results
                if result is not None
            ]

            if candidates:
                candidate = max(
                    candidates,
                    key=lambda item: (
                        float(
                            getattr(
                                item,
                                "winrate",
                                0,
                            )
                            or 0
                        ),
                        float(
                            getattr(
                                item,
                                "quality",
                                0,
                            )
                            or 0
                        ),
                        float(
                            getattr(
                                item,
                                "confidence",
                                0,
                            )
                            or 0
                        ),
                    ),
                )
            else:
                candidate = None

        if candidate is None:
            await callback.message.answer(
                render_message(
                    "no_signal",
                    pair=format_pair(pair),
                ),
                reply_markup=back_to_main_keyboard(),
            )
            return

        # -----------------------------------------------------------
        # Scanner сейчас возвращает только SignalCandidate.
        # График не обязателен для signal_service.
        # -----------------------------------------------------------

        chart_path = None

        from signal_service import save_signal

        signal = await save_signal(
            candidate
        )

        from signal_service import send_manual_signal

        await send_manual_signal(
            bot=callback.bot,
            signal=signal,
            telegram_id=int(
                callback.from_user.id
            ),
            chart_path=chart_path,
        )

    except Exception:
        logger.exception(
            "Manual signal scan failed"
        )

        await callback.message.answer(
            render_message(
                "analysis_error"
            ),
            reply_markup=back_to_main_keyboard(),
        )

    finally:
        await state.clear()


# ---------------------------------------------------------------------------
# Market analysis
# ---------------------------------------------------------------------------

@router.message(
    F.text == "📈 Анализ рынка"
)
async def analysis_market_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_approved(message):
        return

    await state.clear()

    await state.update_data(
        analysis_only=True
    )

    await state.set_state(
        SignalStates.choosing_market
    )

    await message.answer(
        render_message(
            "analysis_choose_market"
        ),
        reply_markup=market_keyboard(),
    )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@router.message(
    F.text == "📜 История"
)
async def history_handler(
    message: Message,
) -> None:
    if not await require_approved(message):
        return

    history = await get_user_signal_history(
        telegram_id=int(
            message.from_user.id
        ),
        limit=20,
    )

    if not history:
        await message.answer(
            render_message(
                "history_empty"
            ),
            reply_markup=main_menu_keyboard(
                is_owner=is_owner(
                    int(
                        message.from_user.id
                    )
                )
            ),
        )
        return

    lines = [
        "📜 <b>История сигналов</b>",
        "",
    ]

    for signal in history:
        result_icon = {
            SIGNAL_RESULT_WIN: "✅",
            SIGNAL_RESULT_LOSS: "❌",
            SIGNAL_RESULT_DRAW: "➖",
        }.get(
            signal.result,
            "⏳",
        )

        lines.append(
            f"{result_icon} "
            f"<b>{format_pair(signal.pair)}</b> "
            f"{signal.direction}"
        )

        lines.append(
            f"   Вход: "
            f"{format_price(signal.entry_price)}"
        )

        if signal.close_price is not None:
            lines.append(
                f"   Закрытие: "
                f"{format_price(signal.close_price)}"
            )

        lines.append(
            f"   {signal.expiry_minutes} мин • "
            f"{format_datetime(signal.created_at)}"
        )

        lines.append("")

    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(
            is_owner=is_owner(
                int(
                    message.from_user.id
                )
            )
        ),
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.message(
    F.text == "📊 Статистика"
)
async def stats_handler(
    message: Message,
) -> None:
    if not await require_approved(message):
        return

    stats = await get_user_result_statistics(
        telegram_id=int(
            message.from_user.id
        )
    )

    await message.answer(
        render_message(
            "stats",
            total=stats["total"],
            completed=stats["completed"],
            wins=stats["wins"],
            losses=stats["losses"],
            draws=stats["draws"],
            winrate=f'{stats["winrate"]:.2f}%',
        ),
        reply_markup=main_menu_keyboard(
            is_owner=is_owner(
                int(
                    message.from_user.id
                )
            )
        ),
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@router.message(
    F.text == "⚙️ Настройки"
)
async def settings_handler(
    message: Message,
) -> None:
    if not await require_approved(message):
        return

    user = await get_current_user(
        int(message.from_user.id)
    )

    enabled = bool(
        user
        and user.is_auto_signals_enabled
    )

    await message.answer(
        render_message(
            "settings",
            auto_status=(
                "ВКЛ"
                if enabled
                else "ВЫКЛ"
            ),
        ),
        reply_markup=settings_keyboard(
            enabled
        ),
    )


@router.callback_query(
    F.data == "settings:auto"
)
async def settings_auto_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    if not await _callback_approved(callback):
        return

    user = await get_current_user(
        int(callback.from_user.id)
    )

    if user is None:
        return

    new_value = not bool(
        user.is_auto_signals_enabled
    )

    await set_auto_signals(
        telegram_id=int(
            callback.from_user.id
        ),
        enabled=new_value,
    )

    await callback.message.edit_text(
        render_message(
            "settings",
            auto_status=(
                "ВКЛ"
                if new_value
                else "ВЫКЛ"
            ),
        ),
        reply_markup=settings_keyboard(
            new_value
        ),
    )


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

@router.callback_query(
    F.data == "menu:main"
)
async def main_menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.clear()

    telegram_id = int(
        callback.from_user.id
    )

    status = await get_user_access_status(
        telegram_id
    )

    if status != "approved":
        await callback.message.answer(
            render_message(
                "access_required"
            )
        )
        return

    await callback.message.answer(
        render_message(
            "main_menu"
        ),
        reply_markup=main_menu_keyboard(
            is_owner=is_owner(
                telegram_id
            )
        ),
    )


# ---------------------------------------------------------------------------
# Pair menu
# ---------------------------------------------------------------------------

@router.callback_query(
    F.data == "menu:pairs"
)
async def menu_pairs_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    if not await _callback_approved(callback):
        return

    await state.set_state(
        SignalStates.choosing_pair
    )

    await callback.message.edit_text(
        render_message(
            "choose_pair"
        ),
        reply_markup=pair_keyboard(),
    )


# ---------------------------------------------------------------------------
# Pair decoder
# ---------------------------------------------------------------------------

def _decode_pair(
    value: str,
) -> str | None:
    normalized = value.upper()

    mapping = {
        pair.replace("/", "").upper(): pair
        for pair in (
            "EUR/USD",
            "GBP/USD",
            "USD/JPY",
            "USD/CHF",
            "AUD/USD",
            "USD/CAD",
            "NZD/USD",
            "EUR/GBP",
            "EUR/JPY",
            "GBP/JPY",
        )
    }

    return mapping.get(
        normalized
    )


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

@router.message()
async def fallback_handler(
    message: Message,
) -> None:
    if not await require_approved(message):
        return

    await message.answer(
        render_message(
            "main_menu"
        ),
        reply_markup=main_menu_keyboard(
            is_owner=is_owner(
                int(
                    message.from_user.id
                )
            )
        ),
    )
