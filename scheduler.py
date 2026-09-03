from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from config import (
    AUTO_SIGNAL_INTERVAL_MINUTES,
    AUTO_SIGNALS_ENABLED,
    DEFAULT_EXPIRY_MINUTES,
)
from market import MarketClient
from signal_engine import SignalEngine
from signal_scanner import SignalScanner
from signal_service import (
    broadcast_signal,
    save_signal,
)
from time_utils import utc_now


logger = logging.getLogger(
    "teyzoo.scheduler"
)


class SignalScheduler:
    def __init__(
        self,
        bot: Bot,
        market: MarketClient,
        engine: SignalEngine,
    ) -> None:
        self.bot = bot
        self.market = market
        self.engine = engine

        self.scanner = SignalScanner(
            market,
            engine,
        )

        self.running = True

        self.last_signal_key: str | None = None

    async def run(self) -> None:
        if not AUTO_SIGNALS_ENABLED:
            logger.info(
                "Automatic signals disabled"
            )

            return

        while self.running:
            try:
                await self.run_cycle()
            except Exception:
                logger.exception(
                    "Scheduler cycle failed"
                )

            await asyncio.sleep(
                AUTO_SIGNAL_INTERVAL_MINUTES
                * 60
            )

    async def run_cycle(self) -> None:
        candidate = await self.scanner.scan(
            market="regular",
            expiry_minutes=(
                DEFAULT_EXPIRY_MINUTES
            ),
            source="auto",
        )

        if candidate is None:
            logger.info(
                "No qualifying signal"
            )
            return

        key = (
            f"{candidate.pair}:"
            f"{candidate.direction}:"
            f"{candidate.expiry_minutes}"
        )

        if key == self.last_signal_key:
            logger.info(
                "Duplicate signal skipped"
            )
            return

        self.last_signal_key = key

        from chart_generator import (
            chart_generator,
        )

        try:
            from market import MarketClient

            df = await self.market.get_candles(
                candidate.pair,
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

        sent = await broadcast_signal(
            self.bot,
            signal,
        )

        logger.info(
            "Auto signal %s sent to %s users",
            signal.id,
            sent,
        )
