from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import NORMAL_PAIRS


def main_menu_keyboard(
    *,
    is_owner: bool = False,
) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                text="🔎 Найти сигнал"
            ),
            KeyboardButton(
                text="📈 Анализ рынка"
            ),
        ],
        [
            KeyboardButton(
                text="📜 История"
            ),
            KeyboardButton(
                text="📊 Статистика"
            ),
        ],
        [
            KeyboardButton(
                text="⚙️ Настройки"
            ),
        ],
    ]

    if is_owner:
        rows.append(
            [
                KeyboardButton(
                    text="👑 Панель владельца"
                )
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )


def market_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💱 FOREX",
                    callback_data="market:regular",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📡 OTC",
                    callback_data="market:otc",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu:main",
                ),
            ],
        ]
    )


def pair_keyboard(
    pairs: tuple[str, ...] | list[str] | None = None,
) -> InlineKeyboardMarkup:
    if pairs is None:
        pairs = NORMAL_PAIRS

    buttons: list[list[InlineKeyboardButton]] = []

    row: list[InlineKeyboardButton] = []

    for pair in pairs:
        callback_pair = pair.replace(
            "/",
            "",
        )

        row.append(
            InlineKeyboardButton(
                text=pair,
                callback_data=f"pair:{callback_pair}",
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # ============================================================
    # ВСЕ ПАРЫ
    # ============================================================

    buttons.append(
        [
            InlineKeyboardButton(
                text="🌐 Все пары",
                callback_data="pair:ALL",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="menu:signal",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def expiry_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    row: list[InlineKeyboardButton] = []

    for minutes in range(1, 21):
        row.append(
            InlineKeyboardButton(
                text=f"{minutes} мин",
                callback_data=f"expiry:{minutes}",
            )
        )

        if len(row) == 4:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="⚡ Любое время",
                callback_data="expiry:any",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="menu:pairs",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def analysis_expiry_keyboard() -> InlineKeyboardMarkup:
    return expiry_keyboard()


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main",
                )
            ]
        ]
    )


def settings_keyboard(
    auto_enabled: bool,
) -> InlineKeyboardMarkup:
    auto_text = (
        "🔴 Автосигналы: ВЫКЛ"
        if auto_enabled
        else "🟢 Автосигналы: ВКЛ"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=auto_text,
                    callback_data="settings:auto",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main",
                )
            ],
        ]
    )


def admin_request_keyboard(
    telegram_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"admin:approve:{telegram_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"admin:reject:{telegram_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 В чёрный список",
                    callback_data=f"admin:blacklist:{telegram_id}",
                ),
            ],
        ]
    )


def admin_user_keyboard(
    telegram_id: int,
    status: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if status == "pending":
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"admin:approve:{telegram_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"admin:reject:{telegram_id}",
                ),
            ]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text="🚫 В чёрный список",
                    callback_data=f"admin:blacklist:{telegram_id}",
                )
            ]
        )

    elif status == "approved":
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚫 В чёрный список",
                    callback_data=f"admin:blacklist:{telegram_id}",
                )
            ]
        )

    elif status == "blacklisted":
        rows.append(
            [
                InlineKeyboardButton(
                    text="♻️ Снять ЧС",
                    callback_data=f"admin:unblacklist:{telegram_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📥 Заявки",
                    callback_data="owner:requests",
                ),
                InlineKeyboardButton(
                    text="👥 Пользователи",
                    callback_data="owner:users",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💬 Тексты бота",
                    callback_data="owner:messages",
                ),
                InlineKeyboardButton(
                    text="🕯 Свечи",
                    callback_data="owner:candles",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📡 Автосигналы",
                    callback_data="owner:auto",
                ),
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="owner:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="owner:broadcast",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main",
                )
            ],
        ]
    )


def owner_message_keyboard(
    message_keys: list[str],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for key in message_keys:
        rows.append(
            [
                InlineKeyboardButton(
                    text=key[:50],
                    callback_data=f"ownermsg:{key}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Панель владельца",
                callback_data="owner:panel",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def owner_candle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏸ Убрать 1 свечу на 15 мин",
                    callback_data="candle:1:15",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏸ Убрать 2 свечи на 30 мин",
                    callback_data="candle:2:30",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏸ Убрать 3 свечи на 60 мин",
                    callback_data="candle:3:60",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏸ Убрать 5 свечей на 120 мин",
                    callback_data="candle:5:120",
                )
            ],
            [
                InlineKeyboardButton(
                    text="▶️ Отключить фильтр",
                    callback_data="candle:disable",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Панель владельца",
                    callback_data="owner:panel",
                )
            ],
        ]
    )


def owner_auto_keyboard(
    enabled: bool,
) -> InlineKeyboardMarkup:
    toggle_text = (
        "🔴 Выключить автосигналы"
        if enabled
        else "🟢 Включить автосигналы"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data="owner:auto_toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Панель владельца",
                    callback_data="owner:panel",
                )
            ],
        ]
    )
