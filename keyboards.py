from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    MAX_EXPIRY_MINUTES,
    MIN_EXPIRY_MINUTES,
)


def main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎯 Получить сигнал",
            callback_data="signal:start",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📊 История",
            callback_data="history",
        ),
        InlineKeyboardButton(
            text="📈 Статистика",
            callback_data="stats",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="settings",
        )
    )

    return builder.as_markup()


def pending_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить доступ",
            callback_data="check_access",
        )
    )

    return builder.as_markup()


def signal_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🌐 Обычные пары",
            callback_data="signal_type:regular",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🟣 OTC",
            callback_data="signal_type:otc",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔀 Любая пара",
            callback_data="signal_type:any",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="main",
        )
    )

    return builder.as_markup()


def regular_pairs_keyboard(
    pairs: list[str],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for index in range(0, len(pairs), 2):
        row = pairs[index:index + 2]

        buttons = []

        for pair in row:
            buttons.append(
                InlineKeyboardButton(
                    text=pair,
                    callback_data=(
                        f"pair:{pair}"
                    ),
                )
            )

        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(
            text="🔀 Любая обычная пара",
            callback_data="pair:any_regular",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="signal:start",
        )
    )

    return builder.as_markup()


def otc_pairs_keyboard(
    pairs: list[str],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not pairs:
        builder.row(
            InlineKeyboardButton(
                text="⚠️ OTC недоступен",
                callback_data="otc:unavailable",
            )
        )
    else:
        for index in range(0, len(pairs), 2):
            row = pairs[index:index + 2]

            builder.row(
                *[
                    InlineKeyboardButton(
                        text=pair,
                        callback_data=f"pair:{pair}",
                    )
                    for pair in row
                ]
            )

        builder.row(
            InlineKeyboardButton(
                text="🔀 Любая OTC пара",
                callback_data="pair:any_otc",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="signal:start",
        )
    )

    return builder.as_markup()


def expiry_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    values = range(
        MIN_EXPIRY_MINUTES,
        MAX_EXPIRY_MINUTES + 1,
    )

    row = []

    for minutes in values:
        row.append(
            InlineKeyboardButton(
                text=f"{minutes} мин",
                callback_data=f"expiry:{minutes}",
            )
        )

        if len(row) == 4:
            builder.row(*row)
            row = []

    if row:
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(
            text="⚡ Любое время",
            callback_data="expiry:any",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="signal:start",
        )
    )

    return builder.as_markup()


def admin_request_keyboard(
    telegram_id: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=(
                f"admin:approve:{telegram_id}"
            ),
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=(
                f"admin:reject:{telegram_id}"
            ),
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="🚫 В чёрный список",
            callback_data=(
                f"admin:blacklist:{telegram_id}"
            ),
        )
    )

    return builder.as_markup()


def blacklist_keyboard(
    telegram_id: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔓 Убрать из ЧС",
            callback_data=(
                f"admin:unblacklist:{telegram_id}"
            ),
        )
    )

    return builder.as_markup()


def back_keyboard(
    callback_data: str = "main",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=callback_data,
        )
    )

    return builder.as_markup()
