from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import (
    MIN_SIGNAL_WINRATE,
)
from database import get_user
from keyboards import (
    expiry_keyboard,
    main_keyboard,
    market_keyboard,
    pairs_keyboard,
    pending_keyboard,
)
from messages import (
    get_text,
    render_text,
)
from pair_selector import pair_selector
from services import request_access
from signal_engine import SignalEngine
from signal_scanner import SignalScanner
from signal_service import save_signal
from market import market_client
from analysis_service import AnalysisService
from states import (
    AnalysisStates,
    SignalStates,
)
from time_utils import normalize_expiry


router = Router()

engine = SignalEngine()

scanner = SignalScanner(
    market_client,
    engine,
)

analysis_service = AnalysisService(
    market_client,
    engine,
)


async def require_approved(
    telegram_id: int,
) -> bool:
    user = await get_user(
        telegram_id
    )

    return bool(
        user
        and user.status == "approved"
    )


@router.message(
    lambda message:
    message.text == "🔄 Проверить доступ"
)
async def check_access(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    user, _ = await request_access(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )

    if user.status == "approved":
        text = await get_text(
            "start_approved"
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    elif user.status == "blacklisted":
        text = await get_text(
            "start_blacklisted"
        )

        await message.answer(
            text,
            parse_mode="HTML",
        )

    else:
        text = await get_text(
            "start_pending"
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=pending_keyboard(),
        )


@router.message(
    lambda message:
    message.text == "📡 Получить сигнал"
)
async def signal_start(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not await require_approved(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Сначала получи доступ."
        )
        return

    await state.clear()

    await state.set_state(
        SignalStates.choosing_market
    )

    text = await get_text(
        "signal_search"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=market_keyboard(
            "market"
        ),
    )


@router.callback_query(
    SignalStates.choosing_market,
    lambda callback:
    callback.data.startswith(
        "market:"
    ),
)
async def signal_market(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    market = callback.data.split(
        ":",
        1,
    )[1]

    pairs = pair_selector.available_pairs(
        market
    )

    if not pairs:
        await callback.answer(
            "🌙 Реальных OTC-данных сейчас нет.",
            show_alert=True,
        )
        return

    await state.update_data(
        market=market
    )

    await state.set_state(
        SignalStates.choosing_pair
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "💱 <b>Выбери пару:</b>",
            parse_mode="HTML",
            reply_markup=pairs_keyboard(
                pairs,
                "pair",
            ),
        )


@router.callback_query(
    SignalStates.choosing_pair,
    lambda callback:
    callback.data.startswith(
        "pair:"
    ),
)
async def signal_pair(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    pair = callback.data.split(
        ":",
        1,
    )[1]

    await state.update_data(
        pair=pair
    )

    await state.set_state(
        SignalStates.choosing_expiry
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            f"💱 Пара: <b>{pair}</b>\n\n"
            "⏱ <b>Выбери экспирацию:</b>",
            parse_mode="HTML",
            reply_markup=expiry_keyboard(),
        )


@router.callback_query(
    SignalStates.choosing_expiry,
    lambda callback:
    callback.data.startswith(
        "expiry:"
    ),
)
async def signal_expiry(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    value = callback.data.split(
        ":",
        1,
    )[1]

    expiry = normalize_expiry(
        value
    )

    data = await state.get_data()

    pair = data.get(
        "pair"
    )

    market = data.get(
        "market"
    )

    if not pair or not market:
        await callback.answer(
            "Сессия устарела.",
            show_alert=True,
        )
        await state.clear()
        return

    await callback.answer(
        "🔎 Анализирую..."
    )

    if callback.message:
        await callback.message.edit_text(
            "🔎 <b>Анализ рынка...</b>\n\n"
            f"💱 {pair}\n"
            f"⏱ {expiry} мин.\n\n"
            "Проверяю историю и условия "
            "WINRATE ≥ 75%.",
            parse_mode="HTML",
        )

    candidate = await scanner.scan_pair(
        pair=pair,
        market=market,
        expiry_minutes=expiry,
        source="manual",
    )

    await state.clear()

    if candidate is None:
        text = await get_text(
            "no_signal"
        )

        await callback.message.answer(
            render_text(
                text,
                min_winrate=MIN_SIGNAL_WINRATE,
            ),
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

        return

    from chart_generator import (
        chart_generator,
    )

    try:
        df = await market_client.get_candles(
            pair,
            interval="1min",
            outputsize=120,
        )

        from candle_filter import (
            candle_filter,
        )

        df = candle_filter.apply(
            df
        )

        candidate.chart_path = (
            chart_generator.generate(
                df,
                candidate,
            )
        )
    except Exception:
        candidate.chart_path = None

    signal = await save_signal(
        candidate
    )

    from signal_service import (
        send_signal_to_user,
    )

    await send_signal_to_user(
        callback.bot,
        signal,
        callback.from_user.id,
    )


@router.message(
    lambda message:
    message.text == "📈 Анализ рынка"
)
async def analysis_start(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not await require_approved(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Сначала получи доступ."
        )
        return

    await state.clear()

    await state.set_state(
        AnalysisStates.choosing_market
    )

    text = await get_text(
        "analysis"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=market_keyboard(
            "analysis_market"
        ),
    )


@router.callback_query(
    AnalysisStates.choosing_market,
    lambda callback:
    callback.data.startswith(
        "analysis_market:"
    ),
)
async def analysis_market(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    market = callback.data.split(
        ":",
        1,
    )[1]

    pairs = pair_selector.available_pairs(
        market
    )

    if not pairs:
        await callback.answer(
            "Реального OTC-источника нет.",
            show_alert=True,
        )
        return

    await state.update_data(
        market=market
    )

    await state.set_state(
        AnalysisStates.choosing_pair
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "📈 <b>Выбери пару:</b>",
            parse_mode="HTML",
            reply_markup=pairs_keyboard(
                pairs,
                "analysis_pair",
            ),
        )


@router.callback_query(
    AnalysisStates.choosing_pair,
    lambda callback:
    callback.data.startswith(
        "analysis_pair:"
    ),
)
async def analysis_pair(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    pair = callback.data.split(
        ":",
        1,
    )[1]

    data = await state.get_data()

    market = data.get(
        "market"
    )

    await state.clear()

    await callback.answer(
        "📈 Строю анализ..."
    )

    candidate, df = (
        await analysis_service.analyze(
            pair=pair,
            market=market,
            expiry_minutes=5,
        )
    )

    if (
        candidate is None
        or not candidate.chart_path
    ):
        await callback.message.answer(
            "📈 Анализ выполнен, но "
            "подходящего сигнала ≥75% "
            "сейчас нет.",
            reply_markup=main_keyboard(),
        )
        return

    from aiogram.types import FSInputFile

    await callback.message.answer_photo(
        FSInputFile(
            candidate.chart_path
        ),
        caption=(
            f"📈 <b>АНАЛИЗ {pair}</b>\n\n"
            f"🎯 Уверенность: "
            f"<b>{candidate.confidence:.1f}%</b>\n"
            f"🏆 Исторический WINRATE: "
            f"<b>{candidate.winrate:.1f}%</b>\n"
            f"⭐ Качество: "
            f"<b>{candidate.quality:.1f}%</b>\n\n"
            "График построен по реальным "
            "рыночным данным."
        ),
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@router.message(
    lambda message:
    message.text == "📊 Статистика"
)
async def stats_handler(
    message: Message,
) -> None:
    from stats_service import (
        get_signal_stats,
    )

    stats = await get_signal_stats()

    await message.answer(
        "📊 <b>СТАТИСТИКА</b>\n\n"
        f"📡 Всего сигналов: "
        f"<b>{stats['total']}</b>\n"
        f"✅ WIN: <b>{stats['wins']}</b>\n"
        f"❌ LOSS: <b>{stats['losses']}</b>\n"
        f"⚪ DRAW: <b>{stats['draws']}</b>\n\n"
        f"🏆 Фактический WINRATE: "
        f"<b>{stats['winrate']:.1f}%</b>",
        parse_mode="HTML",
    )


@router.message(
    lambda message:
    message.text == "📜 История"
)
async def history_handler(
    message: Message,
) -> None:
    from history_service import (
        get_user_history,
    )

    signals = await get_user_history()

    if not signals:
        await message.answer(
            "📜 История пока пустая."
        )
        return

    lines = [
        "📜 <b>ИСТОРИЯ</b>\n"
    ]

    for signal in signals:
        result = signal.result.upper()

        icon = {
            "WIN": "✅",
            "LOSS": "❌",
            "DRAW": "⚪",
            "PENDING": "⏳",
        }.get(
            result,
            "•",
        )

        lines.append(
            f"{icon} {signal.pair} "
            f"{signal.direction} "
            f"{signal.winrate:.1f}% "
            f"— {result}"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
    )


@router.message(
    lambda message:
    message.text == "⚙️ Настройки"
)
async def settings_handler(
    message: Message,
) -> None:
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Автоматические сигналы доступны "
        "для одобренных пользователей.\n\n"
        "Настройки Owner находятся "
        "в отдельном Owner Menu.",
        parse_mode="HTML",
    )


@router.callback_query(
    lambda callback:
    callback.data == "flow:cancel"
)
async def flow_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await callback.answer(
        "Отменено"
    )

    if callback.message:
        await callback.message.edit_text(
            "❌ Отменено."
        )


@router.callback_query(
    lambda callback:
    callback.data == "flow:back_market"
)
async def flow_back_market(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    if "market" not in data:
        await callback.answer()
        return

    await state.set_state(
        SignalStates.choosing_market
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "📡 <b>Выбери рынок:</b>",
            parse_mode="HTML",
            reply_markup=market_keyboard(
                "market"
            ),
        )


@router.callback_query(
    lambda callback:
    callback.data == "flow:back_pair"
)
async def flow_back_pair(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    market = data.get(
        "market"
    )

    if not market:
        await callback.answer()
        return

    await state.set_state(
        SignalStates.choosing_pair
    )

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "💱 <b>Выбери пару:</b>",
            parse_mode="HTML",
            reply_markup=pairs_keyboard(
                pair_selector.available_pairs(
                    market
                ),
                "pair",
            ),
        )
