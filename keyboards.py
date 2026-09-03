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
                KeyboardButton(
                    text="📡 Получить сигнал"
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
        ],
        resize_keyboard=True,
    )


def pending_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🔄 Проверить доступ"
                )
            ]
        ],
        resize_keyboard=True,
    )


def market_keyboard(
    prefix: str = "market",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💱 Обычный рынок",
                    callback_data=f"{prefix}:regular",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌙 OTC",
                    callback_data=f"{prefix}:otc",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Любой рынок",
                    callback_data=f"{prefix}:any",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="flow:cancel",
                )
            ],
        ]
    )


def pairs_keyboard(
    pairs: list[str],
    prefix: str,
) -> InlineKeyboardMarkup:
    rows = []

    for pair in pairs:
        rows.append(
            [
                InlineKeyboardButton(
                    text=pair,
                    callback_data=(
                        f"{prefix}:"
                        f"{pair}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="flow:back_market",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def expiry_keyboard() -> InlineKeyboardMarkup:
    rows = []

    for start in (
        1,
        6,
        11,
        16,
    ):
        row = []

        for minute in range(
            start,
            min(
                start + 5,
                21,
            ),
        ):
            row.append(
                InlineKeyboardButton(
                    text=f"{minute} мин.",
                    callback_data=(
                        f"expiry:{minute}"
                    ),
                )
            )

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
                callback_data="flow:back_pair",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def analysis_actions_keyboard(
    market: str,
    pair: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Новый анализ",
                    callback_data=(
                        f"analysis:repeat:"
                        f"{market}:"
                        f"{pair}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📡 Найти сигнал",
                    callback_data=(
                        f"analysis:signal:"
                        f"{market}:"
                        f"{pair}"
                    ),
                )
            ],
        ]
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
                    text="📝 Тексты",
                    callback_data="owner:texts",
                ),
                InlineKeyboardButton(
                    text="🕯 Свечи",
                    callback_data="owner:candles",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="owner:stats",
                ),
            ],
        ]
    )


def owner_texts_keyboard(
    keys: list[str],
) -> InlineKeyboardMarkup:
    rows = []

    for key in keys:
        rows.append(
            [
                InlineKeyboardButton(
                    text=key,
                    callback_data=f"owner_text:{key}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="owner:back",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def owner_candles_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Все свечи",
                    callback_data="candle:0:0",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕯 Убрать 5",
                    callback_data="candle:5:30",
                ),
                InlineKeyboardButton(
                    text="🕯 Убрать 10",
                    callback_data="candle:10:30",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🕯 Убрать 20",
                    callback_data="candle:20:30",
                ),
                InlineKeyboardButton(
                    text="🕯 Убрать 30",
                    callback_data="candle:30:30",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🕯 Убрать 50",
                    callback_data="candle:50:30",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="owner:back",
                )
            ],
        ]
    )
