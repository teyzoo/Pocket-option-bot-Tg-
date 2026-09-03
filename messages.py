from __future__ import annotations

from datetime import datetime
from typing import Any


DEFAULT_MESSAGES: dict[str, str] = {
    "start_approved": (
        "👋 Привет, {name}!\n\n"
        "Доступ одобрен.\n"
        "Выбирай нужный раздел в меню."
    ),
    "start_pending": (
        "⏳ Твоя заявка уже находится на рассмотрении.\n\n"
        "После одобрения доступ откроется автоматически."
    ),
    "start_blacklisted": (
        "🚫 Доступ запрещён.\n\n"
        "Ты находишься в чёрном списке."
    ),
    "access_required": (
        "🔐 Для использования бота необходимо получить доступ у администратора."
    ),
    "access_request_sent": (
        "📨 Заявка отправлена администрации.\n\n"
        "Ожидай решения."
    ),
    "access_approved": (
        "✅ Твоя заявка одобрена!\n\n"
        "Теперь тебе доступен бот."
    ),
    "access_rejected": (
        "❌ Заявка отклонена администрацией."
    ),
    "access_blacklisted": (
        "🚫 Твой доступ был заблокирован.\n\n"
        "Причина: {reason}"
    ),
    "access_pending_again": (
        "♻️ Ты был снят с чёрного списка.\n\n"
        "Тебе необходимо повторно дождаться одобрения администрации."
    ),
    "main_menu": (
        "🏠 <b>Главное меню</b>\n\n"
        "Выбери действие ниже."
    ),
    "signal_choose_market": (
        "📡 <b>Выбор рынка</b>\n\n"
        "Выбери рынок для анализа."
    ),
    "analysis_choose_market": (
        "📈 <b>Анализ рынка</b>\n\n"
        "Выбери рынок. Анализ может быть показан даже при отсутствии подходящего сигнала."
    ),
    "otc_unavailable": (
        "📡 <b>OTC сейчас недоступен</b>\n\n"
        "Для OTC нет подтверждённого источника реальных котировок, поэтому бот не создаёт фиктивные OTC-сигналы."
    ),
    "choose_pair": (
        "💱 <b>Выбери валютную пару</b>"
    ),
    "choose_expiry": (
        "⏱ <b>Выбери время экспирации</b>\n\n"
        "Доступно от 1 до 20 минут."
    ),
    "analyzing": (
        "🔎 <b>Анализирую рынок...</b>\n\n"
        "Пара: {pair}\n"
        "Экспирация: {expiry}\n\n"
        "Проверяю индикаторы, историческую статистику и качество сетапа."
    ),
    "no_signal": (
        "⚪ <b>Подходящий сигнал не найден</b>\n\n"
        "Пара: {pair}\n\n"
        "Бот не будет выдавать сигнал только ради того, чтобы что-то показать.\n"
        "Исторический WINRATE должен быть не ниже 75%."
    ),
    "analysis_error": (
        "⚠️ Во время анализа произошла ошибка.\n\n"
        "Попробуй ещё раз через некоторое время."
    ),
    "generic_error": (
        "⚠️ Не удалось выполнить действие."
    ),
    "signal": (
        "🚨 <b>СИГНАЛ</b>\n\n"
        "💱 Пара: <b>{pair}</b>\n"
        "📊 Рынок: {market}\n"
        "🎯 Направление: <b>{direction}</b>\n\n"
        "💰 Вход: <b>{entry_price}</b>\n"
        "⏱ Экспирация: <b>{expiry_minutes} мин</b>\n"
        "🕐 Закрытие: <b>{close_time}</b>\n\n"
        "🏆 Исторический WINRATE: <b>{winrate}</b>\n"
        "🧠 Текущая уверенность: <b>{confidence}%</b>\n"
        "⭐ Качество: <b>{quality}%</b>\n"
        "✅ Подтверждений: <b>{confirmations}</b>\n\n"
        "<b>Почему сигнал:</b>\n"
        "{reasons}"
    ),
    "analysis": (
        "📈 <b>Анализ рынка</b>\n\n"
        "💱 Пара: <b>{pair}</b>\n"
        "📊 Рынок: {market}\n"
        "🎯 Направление: <b>{direction}</b>\n"
        "💰 Цена: <b>{entry_price}</b>\n\n"
        "🏆 Исторический WINRATE: <b>{winrate}</b>\n"
        "🧠 Уверенность: <b>{confidence}%</b>\n"
        "⭐ Качество: <b>{quality}%</b>\n"
        "✅ Подтверждений: <b>{confirmations}</b>\n\n"
        "{reasons}"
    ),
    "history_empty": (
        "📜 История пока пустая."
    ),
    "stats": (
        "📊 <b>Твоя статистика</b>\n\n"
        "Всего сигналов: <b>{total}</b>\n"
        "Завершено: <b>{completed}</b>\n\n"
        "✅ WIN: <b>{wins}</b>\n"
        "❌ LOSS: <b>{losses}</b>\n"
        "➖ DRAW: <b>{draws}</b>\n\n"
        "🏆 WINRATE: <b>{winrate}</b>"
    ),
    "settings": (
        "⚙️ <b>Настройки</b>\n\n"
        "Автоматические сигналы: <b>{auto_status}</b>\n\n"
        "Автосигналы получают только пользователи с одобренным доступом."
    ),
    "result": (
        "{result_title}\n\n"
        "💱 Пара: <b>{pair}</b>\n"
        "🎯 Направление: <b>{direction}</b>\n\n"
        "💰 Вход: <b>{entry_price}</b>\n"
        "🏁 Цена закрытия: <b>{close_price}</b>\n"
        "⏱ Экспирация: <b>{expiry_minutes} мин</b>\n"
        "🕐 Время закрытия: <b>{close_time}</b>\n\n"
        "🏆 Исторический WINRATE: <b>{winrate}</b>\n"
        "🧠 Уверенность: <b>{confidence}%</b>"
    ),
    "admin_no_requests": (
        "📥 Новых заявок нет."
    ),
    "admin_requests_header": (
        "📥 <b>Заявки на доступ</b>\n\n"
        "Всего: <b>{count}</b>"
    ),
    "admin_request": (
        "👤 <b>Новая заявка</b>\n\n"
        "Telegram ID: <code>{telegram_id}</code>\n"
        "Username: {username}\n"
        "Имя: {first_name}\n"
        "Дата: {created_at}"
    ),
    "admin_user_not_found": (
        "⚠️ Пользователь не найден."
    ),
    "admin_approved": (
        "✅ Пользователь <code>{telegram_id}</code> одобрен."
    ),
    "admin_rejected": (
        "❌ Пользователь <code>{telegram_id}</code> отклонён."
    ),
    "admin_blacklist_prompt": (
        "🚫 Введи причину добавления пользователя "
        "<code>{telegram_id}</code> в чёрный список."
    ),
    "admin_blacklisted": (
        "🚫 Пользователь <code>{telegram_id}</code> добавлен в ЧС.\n\n"
        "Причина: {reason}"
    ),
    "admin_unblacklisted": (
        "♻️ Пользователь <code>{telegram_id}</code> снят с ЧС "
        "и переведён в ожидание повторного одобрения."
    ),
    "owner_panel": (
        "👑 <b>Панель владельца</b>\n\n"
        "Здесь можно управлять доступом, текстами, свечами, автосигналами и рассылками."
    ),
    "owner_message_list": (
        "💬 <b>Редактор сообщений</b>\n\n"
        "Выбери сообщение, текст которого нужно изменить."
    ),
    "owner_unknown_message": (
        "⚠️ Такое сообщение не найдено."
    ),
    "owner_message_prompt": (
        "💬 <b>Редактирование сообщения</b>\n\n"
        "Ключ: <code>{key}</code>\n\n"
        "Текущий текст:\n"
        "────────────\n"
        "{current_text}\n"
        "────────────\n\n"
        "Отправь новый текст одним сообщением."
    ),
    "owner_message_empty": (
        "⚠️ Текст не может быть пустым."
    ),
    "owner_message_saved": (
        "✅ Сообщение <code>{key}</code> сохранено."
    ),
    "owner_candle_status": (
        "🕯 <b>Фильтр свечей</b>\n\n"
        "Статус: <b>{enabled}</b>\n"
        "Исключаемых последних свечей: <b>{count}</b>\n"
        "До: <b>{expires_at}</b>\n\n"
        "Исключение свечей не удаляет рыночные данные."
    ),
    "owner_candle_saved": (
        "✅ Фильтр свечей включён.\n\n"
        "Исключено последних свечей: <b>{count}</b>\n"
        "Срок: <b>{duration} мин</b>\n"
        "До: <b>{expires_at}</b>"
    ),
    "owner_candle_disabled": (
        "▶️ Фильтр свечей отключён."
    ),
    "owner_auto": (
        "📡 <b>Автосигналы</b>\n\n"
        "Глобальный статус: <b>{enabled}</b>\n\n"
        "Минимальный исторический WINRATE: <b>75%</b>.\n"
        "Понизить этот порог невозможно."
    ),
    "owner_stats": (
        "📊 <b>Статистика системы</b>\n\n"
        "Пользователей: <b>{users}</b>\n"
        "Одобрено: <b>{approved}</b>\n"
        "На рассмотрении: <b>{pending}</b>\n"
        "ЧС: <b>{blacklisted}</b>\n\n"
        "Сигналов: <b>{signals}</b>\n"
        "WIN: <b>{wins}</b>\n"
        "LOSS: <b>{losses}</b>\n"
        "WINRATE: <b>{winrate}</b>"
    ),
    "owner_broadcast_prompt": (
        "📢 <b>Рассылка</b>\n\n"
        "Отправь текст сообщения, которое получат все одобренные пользователи."
    ),
    "owner_broadcast_empty": (
        "⚠️ Сообщение рассылки не может быть пустым."
    ),
    "owner_broadcast_done": (
        "📢 Рассылка завершена.\n\n"
        "Отправлено: <b>{sent}</b>\n"
        "Получателей: <b>{total}</b>"
    ),
}


class _SafeFormatDict(dict):
    def __missing__(
        self,
        key: str,
    ) -> str:
        return "{" + key + "}"


def _normalize_value(
    value: Any,
) -> Any:
    if isinstance(value, datetime):
        return value.strftime(
            "%d.%m.%Y %H:%M"
        )

    return value


def render_message(
    key: str,
    **kwargs: Any,
) -> str:
    template = DEFAULT_MESSAGES.get(
        key,
        DEFAULT_MESSAGES["generic_error"],
    )

    normalized = {
        name: _normalize_value(value)
        for name, value in kwargs.items()
    }

    try:
        return template.format_map(
            _SafeFormatDict(normalized)
        )
    except Exception:
        return template


def get_default_message(
    key: str,
) -> str:
    return DEFAULT_MESSAGES.get(
        key,
        DEFAULT_MESSAGES["generic_error"],
    )


def message_keys() -> list[str]:
    return list(
        DEFAULT_MESSAGES.keys()
    )
