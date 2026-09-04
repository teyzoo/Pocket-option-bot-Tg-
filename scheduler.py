from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from config import AUTO_SIGNAL_INTERVAL_MINUTES

try:
    from config import MAX_AUTO_SCAN_PAIRS
except ImportError:
    MAX_AUTO_SCAN_PAIRS = 8

from services import get_approved_auto_users
from settings_service import (
    get_bool_setting,
    get_int_setting,
)
from signal_scanner import SignalScanner
from signal_service import (
    broadcast_signal,
    save_signal,
)
from time_utils import (
    next_n_minute_mark,
    seconds_until,
)


logger = logging.getLogger(__name__)


class SignalScheduler:
    """
    Планировщик автоматических сигналов.

    Основная схема:

        scheduler
            ↓
        SignalScanner
            ↓
        MarketClient
            ↓
        SignalEngine
            ↓
        SignalCandidate
            ↓
        DB
            ↓
        Telegram users
    """

    def __init__(
        self,
        bot: Bot,
        scanner: SignalScanner | None = None,
        market=None,
        engine=None,
    ) -> None:
        self.bot = bot

        # ----------------------------------------------------
        # Если scanner передан — используем его.
        # ----------------------------------------------------

        if scanner is not None:
            self.scanner = scanner

        # ----------------------------------------------------
        # Совместимость со старым main.py.
        # ----------------------------------------------------

        else:
            self.scanner = SignalScanner(
                market=market,
                engine=engine,
            )

        self._running = False
        self._task: asyncio.Task | None = None

    # ========================================================
    # START
    # ========================================================

    async def start(self) -> None:
        if self._running:
            return

        self._running = True

        self._task = asyncio.create_task(
            self._run_loop(),
            name="signal-scheduler",
        )

        logger.info(
            "Signal scheduler started"
        )

    # ========================================================
    # STOP
    # ========================================================

    async def stop(self) -> None:
        self._running = False

        if self._task is not None:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception(
                    "Signal scheduler task stopped with error"
                )

            self._task = None

        logger.info(
            "Signal scheduler stopped"
        )

    # ========================================================
    # COMPATIBILITY RUN
    # ========================================================

    async def run(self) -> None:
        """
        Совместимость со старым main.py.

        Можно использовать:

            await scheduler.run()

        Новый main.py использует start()/stop().
        """

        await self.start()

        if self._task is None:
            return

        try:
            await self._task
        except asyncio.CancelledError:
            pass

    # ========================================================
    # LOOP
    # ========================================================

    async def _run_loop(self) -> None:
        while self._running:
            try:
                interval = await self._get_interval()

                target = next_n_minute_mark(
                    interval
                )

                wait_seconds = seconds_until(
                    target
                )

                if wait_seconds > 0:
                    logger.info(
                        "Next automatic signal scan: %s "
                        "(%.1f sec)",
                        target,
                        wait_seconds,
                    )

                    await asyncio.sleep(
                        wait_seconds
                    )

                if not self._running:
                    break

                await self.run_once()

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "Unhandled scheduler error"
                )

                await asyncio.sleep(
                    10
                )

    # ========================================================
    # INTERVAL
    # ========================================================

    async def _get_interval(self) -> int:
        value = await get_int_setting(
            "auto_signals.interval_minutes",
            AUTO_SIGNAL_INTERVAL_MINUTES,
        )

        # ----------------------------------------------------
        # По ТЗ:
        # 1–20 минут.
        # ----------------------------------------------------

        return max(
            1,
            min(
                20,
                int(value),
            ),
        )

    # ========================================================
    # RUN ONCE
    # ========================================================

    async def run_once(self) -> int:
        """
        Один автоматический цикл поиска сигнала.

        Возвращает количество пользователей,
        которым реально отправлен сигнал.
        """

        # ----------------------------------------------------
        # Проверяем глобальный переключатель.
        # ----------------------------------------------------

        enabled = await get_bool_setting(
            "auto_signals.enabled",
            default=True,
        )

        if not enabled:
            logger.info(
                "Automatic signals disabled by owner"
            )
            return 0

        # ----------------------------------------------------
        # Получаем пользователей,
        # включивших автоматические сигналы.
        # ----------------------------------------------------

        users = await get_approved_auto_users()

        if not users:
            logger.info(
                "No users enabled for automatic signals"
            )
            return 0

        # ----------------------------------------------------
        # Максимальное количество пар.
        # ----------------------------------------------------

        max_pairs = await get_int_setting(
            "auto_signals.max_pairs",
            MAX_AUTO_SCAN_PAIRS,
        )

        max_pairs = max(
            1,
            min(
                10,
                int(max_pairs),
            ),
        )

        # ----------------------------------------------------
        # Ищем сигнал.
        #
        # expiry_minutes="any" означает:
        # scanner самостоятельно проверяет 1..20 минут.
        # ----------------------------------------------------

        try:
            candidate = await self.scanner.scan(
                market="regular",
                expiry_minutes="any",
                max_pairs=max_pairs,
                source="auto",
            )

        except Exception:
            logger.exception(
                "Automatic market scan failed"
            )
            return 0

        # ----------------------------------------------------
        # Сильного сигнала нет.
        # ----------------------------------------------------

        if candidate is None:
            logger.info(
                "No qualifying automatic signal found"
            )
            return 0

        # ----------------------------------------------------
        # Сохраняем сигнал.
        # ----------------------------------------------------

        signal = await save_signal(
            candidate
        )

        # ----------------------------------------------------
        # chart_path опционален.
        #
        # Если модель когда-нибудь получит это поле —
        # используем его.
        # ----------------------------------------------------

        chart_path = getattr(
            candidate,
            "chart_path",
            None,
        )

        # ----------------------------------------------------
        # Telegram IDs.
        # ----------------------------------------------------

        telegram_ids = [
            int(user.telegram_id)
            for user in users
        ]

        # ----------------------------------------------------
        # Рассылка.
        # ----------------------------------------------------

        sent = await broadcast_signal(
            bot=self.bot,
            signal=signal,
            telegram_ids=telegram_ids,
            chart_path=chart_path,
        )

        logger.info(
            "Automatic signal %s sent to %d users: "
            "%s %s, %.2f%% historical winrate",
            signal.id,
            sent,
            signal.pair,
            signal.direction,
            float(
                signal.winrate or 0
            ),
        )

        return sent


# ============================================================
# ONE-SHOT HELPER
# ============================================================

async def run_scheduler_once(
    bot: Bot,
) -> int:
    scheduler = SignalScheduler(
        bot=bot,
    )

    return await scheduler.run_once()
