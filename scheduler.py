from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from config import (
    AUTO_SIGNAL_INTERVAL_MINUTES,
    MAX_AUTO_SCAN_PAIRS,
)
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

    def __init__(
        self,
        bot: Bot,
        scanner: SignalScanner | None = None,
        market=None,
        engine=None,
    ) -> None:

        self.bot = bot

        self.scanner = (
            scanner
            if scanner is not None
            else SignalScanner(
                market=market,
                engine=engine,
            )
        )

        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:

        if self._running:
            logger.warning(
                "Signal scheduler is already running"
            )
            return

        self._running = True

        self._task = asyncio.create_task(
            self._run_loop(),
            name="signal-scheduler",
        )

        logger.info(
            "Signal scheduler started"
        )

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
                    "Signal scheduler stopped with error"
                )

            self._task = None

        logger.info(
            "Signal scheduler stopped"
        )

    async def run(self) -> None:

        await self.start()

        if self._task is None:
            return

        try:
            await self._task

        except asyncio.CancelledError:
            pass

    async def _run_loop(self) -> None:

        logger.info(
            "Automatic signal loop is active"
        )

        while self._running:

            try:
                interval = await self._get_interval()

                target = next_n_minute_mark(
                    interval
                )

                wait_seconds = seconds_until(
                    target
                )

                logger.info(
                    "Next automatic signal scan: %s "
                    "(%.1f sec)",
                    target,
                    wait_seconds,
                )

                if wait_seconds > 0:
                    await asyncio.sleep(
                        wait_seconds
                    )

                if not self._running:
                    break

                sent = await self.run_once()

                logger.info(
                    "Automatic scan completed: "
                    "sent=%s",
                    sent,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "Unhandled scheduler error"
                )

                await asyncio.sleep(10)

    async def _get_interval(self) -> int:

        value = await get_int_setting(
            "auto_signals.interval_minutes",
            AUTO_SIGNAL_INTERVAL_MINUTES,
        )

        return max(
            1,
            min(
                20,
                int(value),
            ),
        )

    async def run_once(self) -> int:

        enabled = await get_bool_setting(
            "auto_signals.enabled",
            default=True,
        )

        if not enabled:

            logger.warning(
                "Automatic signals disabled "
                "by owner setting"
            )

            return 0

        users = await get_approved_auto_users()

        if not users:

            logger.warning(
                "No users enabled for automatic signals"
            )

            return 0

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

        logger.info(
            "Automatic scan started: "
            "users=%d pairs=%d",
            len(users),
            max_pairs,
        )

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

        if candidate is None:

            logger.info(
                "No qualifying automatic signal found"
            )

            return 0

        logger.info(
            "Automatic candidate found: "
            "%s %s %.2f%%",
            candidate.pair,
            candidate.direction,
            float(
                candidate.winrate or 0
            ),
        )

        try:

            signal = await save_signal(
                candidate
            )

        except Exception:

            logger.exception(
                "Failed to save automatic signal"
            )

            return 0

        chart_path = getattr(
            candidate,
            "chart_path",
            None,
        )

        telegram_ids = [
            int(user.telegram_id)
            for user in users
        ]

        try:

            sent = await broadcast_signal(
                bot=self.bot,
                signal=signal,
                telegram_ids=telegram_ids,
                chart_path=chart_path,
            )

        except Exception:

            logger.exception(
                "Failed to broadcast automatic signal"
            )

            return 0

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


async def run_scheduler_once(
    bot: Bot,
) -> int:

    scheduler = SignalScheduler(
        bot=bot,
    )

    return await scheduler.run_once()
