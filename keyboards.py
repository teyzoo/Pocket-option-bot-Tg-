from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📡 Получить сигнал"),
                KeyboardButton(text="📜 История"),
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
    )


def pending_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Проверить доступ"),
            ],
        ],
        resize_keyboard=True,
    )


def market_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💱 Обычный рынок",
                    callback_data="market:regular",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌙 OTC",
                    callback_data="market:otc",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Любой рынок",
                    callback_data="market:any",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="signal:cancel",
                ),
            ],
        ]
    )


def pairs_keyboard(
    pairs: list[str],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for pair in pairs:
        rows.append(
            [
                InlineKeyboardButton(
                    text=pair,
                    callback_data=f"pair:{pair}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="signal:back_market",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def expiry_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    row: list[InlineKeyboardButton] = []

    for minute in range(1, 11):
        row.append(
            InlineKeyboardButton(
                text=f"{minute} мин.",
                callback_data=f"expiry:{minute}",
            )
        )

        if len(row) == 5:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    row = []

    for minute in range(11, 21):
        row.append(
            InlineKeyboardButton(
                text=f"{minute} мин.",
                callback_data=f"expiry:{minute}",
            )
        )

        if len(row) == 5:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="⚡ Любое время",
                callback_data="expiry:any",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="signal:back_pair",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
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
    blacklisted: bool = False,
) -> InlineKeyboardMarkup:
    if blacklisted:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="♻️ Убрать из ЧС",
                        callback_data=f"admin:unblacklist:{telegram_id}",
                    )
                ]
            ]
        )

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
