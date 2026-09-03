from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from config import (
    SIGNAL_RESULT_LOSS,
    SIGNAL_RESULT_PENDING,
    SIGNAL_RESULT_WIN,
)
from database import Signal, SessionLocal
from market import MarketClient


logger = logging.getLogger(__name__)


class SignalResultChecker:
    def __init__(
        self,
        market: MarketClient,
    ) -> None:
        self.market = market
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
            "Signal result checker started"
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

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.check_expired_signals()

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "Ошибка проверки результатов"
                )

            await asyncio.sleep(30)

    async def check_expired_signals(self) -> None:
        now = datetime.now(timezone.utc)

        async with SessionLocal() as session:
            result = await session.execute(
                select(Signal).where(
                    Signal.result == SIGNAL_RESULT_PENDING,
                    Signal.expires_at <= now,
                )
            )

            signals = list(
                result.scalars().all()
            )

            for signal in signals:
                try:
                    close_price = (
                        await self.market.get_price(
                            signal.pair
                        )
                    )

                    signal.close_price = close_price

                    if (
                        signal.direction == "UP"
                    ):
                        if close_price > signal.entry_price:
                            signal.result = SIGNAL_RESULT_WIN
                        elif close_price < signal.entry_price:
                            signal.result = SIGNAL_RESULT_LOSS
                        else:
                            signal.result = "draw"

                    else:
                        if close_price < signal.entry_price:
                            signal.result = SIGNAL_RESULT_WIN
                        elif close_price > signal.entry_price:
                            signal.result = SIGNAL_RESULT_LOSS
                        else:
                            signal.result = "draw"

                    signal.checked_at = now

                except Exception as exc:
                    logger.warning(
                        "Не удалось проверить сигнал %s: %s",
                        signal.id,
                        exc,
                    )

            await session.commit()
