from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select

from config import (
    ADMIN_IDS,
    AUTO_SIGNAL_MAX_PER_CYCLE,
    AUTO_SIGNALS_ENABLED,
    AUTO_SIGNAL_INTERVAL_MINUTES,
    MIN_SIGNAL_CONFIDENCE,
    USER_STATUS_APPROVED,
)
from database import (
    SessionLocal,
    Signal,
    SignalRecipient,
    User,
)
from keyboards import main_keyboard
from signal_scanner import SignalScanner


logger = logging.getLogger(__name__)


class SignalScheduler:
    def __init__(
        self,
        bot: Bot,
        scanner: SignalScanner,
    ) -> None:
        self.bot = bot
        self.scanner = scanner
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        self._running = True

        self._task = asyncio.create_task(
            self._loop()
        )

        logger.info(
            "Signal scheduler started"
        )

    async def stop(self) -> None:
        self._running = False

        if self._task:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

        logger.info(
            "Signal scheduler stopped"
        )

    async def _loop(self) -> None:
        while self._running:
            try:
                if AUTO_SIGNALS_ENABLED:
                    await self.run_cycle()

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "Ошибка автоматического сканирования"
                )

            await asyncio.sleep(
                AUTO_SIGNAL_INTERVAL_MINUTES * 60
            )

    async def run_cycle(self) -> None:
        sent = 0

        # Автоматический режим использует фиксированную
        # экспирацию, если пользователь не выбирал её.
        expiry = 5

        while sent < AUTO_SIGNAL_MAX_PER_CYCLE:
            signal = await self.scanner.scan(
                expiry_minutes=expiry,
                source="auto",
            )

            if not signal:
                return

            if (
                signal.confidence
                < MIN_SIGNAL_CONFIDENCE
            ):
                return

            await self._save_and_broadcast(
                signal
            )

            sent += 1

    async def _save_and_broadcast(
        self,
        candidate,
    ) -> None:
        async with SessionLocal() as session:
            db_signal = Signal(
                pair=candidate.pair,
                direction=candidate.direction,
                expiry_minutes=candidate.expiry_minutes,
                confidence=candidate.confidence,
                quality=candidate.quality,
                entry_price=candidate.entry_price,
                result="pending",
                source=candidate.source,
                reasons=" | ".join(
                    candidate.reasons
                ),
                created_at=candidate.created_at,
                expires_at=candidate.expires_at,
            )

            session.add(db_signal)
            await session.commit()
            await session.refresh(db_signal)

            result = await session.execute(
                select(User.telegram_id).where(
                    User.status == USER_STATUS_APPROVED,
                    User.is_auto_signals_enabled.is_(True),
                )
            )

            users = list(result.scalars().all())

            for telegram_id in users:
                text = self._format_signal(
                    candidate
                )

                try:
                    message = await self.bot.send_message(
                        telegram_id,
                        text,
                        reply_markup=main_keyboard(),
                    )

                    recipient = SignalRecipient(
                        signal_id=db_signal.id,
                        telegram_id=telegram_id,
                        message_id=message.message_id,
                    )

                    session.add(recipient)

                except Exception as exc:
                    logger.warning(
                        "Не удалось отправить сигнал "
                        "пользователю %s: %s",
                        telegram_id,
                        exc,
                    )

            await session.commit()

    @staticmethod
    def _format_signal(
        signal,
    ) -> str:
        direction = (
            "🟢 ВВЕРХ ⬆️"
            if signal.direction == "UP"
            else "🔴 ВНИЗ ⬇️"
        )

        reasons = "\n".join(
            f"• {reason}"
            for reason in signal.reasons[:6]
        )

        close_time = signal.expires_at.astimezone(
            timezone.utc
        ).strftime("%H:%M:%S")

        return (
            "🚨 <b>НОВЫЙ СИГНАЛ</b>\n\n"
            f"💱 Пара: <b>{signal.pair}</b>\n"
            f"📊 Направление: <b>{direction}</b>\n"
            f"⏱ Экспирация: "
            f"<b>{signal.expiry_minutes} мин</b>\n"
            f"🕐 Закрытие: <b>{close_time} UTC</b>\n\n"
            f"🎯 Уверенность: "
            f"<b>{signal.confidence:.1f}%</b>\n"
            f"⭐ Качество: "
            f"<b>{signal.quality:.1f}%</b>\n"
            f"💵 Цена входа: "
            f"<b>{signal.entry_price:.5f}</b>\n\n"
            "<b>Подтверждения:</b>\n"
            f"{reasons}\n\n"
            "⚠️ Сигнал является аналитическим "
            "прогнозом и не гарантирует прибыль."
        )
