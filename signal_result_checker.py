from __future__ import annotations

import asyncio
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from config import (
    RESULT_DRAW,
    RESULT_LOSS,
    RESULT_PENDING,
    RESULT_WIN,
    RESULT_CHECK_INTERVAL_SECONDS,
)
from database import Signal, get_session
from market import MarketClient
from signal_result_notifications import (
    notify_result,
)


class SignalResultChecker:
    def __init__(
        self,
        bot: Bot,
        market: MarketClient,
    ) -> None:
        self.bot = bot
        self.market = market
        self.running = True

    async def run(self) -> None:
        while self.running:
            try:
                await self.check_expired()
            except Exception:
                pass

            await asyncio.sleep(
                RESULT_CHECK_INTERVAL_SECONDS
            )

    async def check_expired(self) -> None:
        now = datetime.utcnow()

        async with get_session() as session:
            result = await session.execute(
                select(Signal)
                .where(
                    Signal.result
                    == RESULT_PENDING,
                    Signal.expires_at
                    <= now,
                )
                .order_by(
                    Signal.expires_at.asc()
                )
                .limit(10)
            )

            signals = list(
                result.scalars().all()
            )

        for signal in signals:
            await self._process(
                signal
            )

    async def _process(
        self,
        signal: Signal,
    ) -> None:
        try:
            df = await self.market.get_candles(
                signal.pair,
                interval="1min",
                outputsize=5,
            )

            close_price = float(
                df.iloc[-1]["close"]
            )

            if close_price == signal.entry_price:
                result = RESULT_DRAW

            elif (
                signal.direction == "UP"
                and close_price
                > signal.entry_price
            ):
                result = RESULT_WIN

            elif (
                signal.direction == "DOWN"
                and close_price
                < signal.entry_price
            ):
                result = RESULT_WIN

            else:
                result = RESULT_LOSS

            async with get_session() as session:
                db_result = await session.execute(
                    select(Signal).where(
                        Signal.id == signal.id
                    )
                )

                db_signal = (
                    db_result.scalar_one_or_none()
                )

                if db_signal is None:
                    return

                if db_signal.result != RESULT_PENDING:
                    return

                db_signal.close_price = (
                    close_price
                )

                db_signal.result = result
                db_signal.checked_at = (
                    datetime.utcnow()
                )

                await session.commit()

                signal = db_signal

            await notify_result(
                self.bot,
                signal,
            )

        except Exception:
            return
