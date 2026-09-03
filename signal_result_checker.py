from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select

from config import (
    RESULT_CHECKER_INTERVAL_SECONDS,
    SIGNAL_RESULT_DRAW,
    SIGNAL_RESULT_LOSS,
    SIGNAL_RESULT_PENDING,
    SIGNAL_RESULT_WIN,
)
from database import Signal, get_session
from market import MarketClient
from signal_result_notifications import notify_signal_result
from time_utils import ensure_utc, utc_now

logger = logging.getLogger(__name__)


class SignalResultChecker:
    def __init__(
        self,
        bot,
        market_client: MarketClient | None = None,
    ) -> None:
        self.bot = bot
        self.market = market_client or MarketClient()

        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return

        self._running = True

        self._task = asyncio.create_task(
            self._run_loop(),
            name="signal-result-checker",
        )

        logger.info("Signal result checker started")

    async def stop(self) -> None:
        self._running = False

        if self._task is not None:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

        logger.info("Signal result checker stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self.check_expired_signals()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Unhandled error in signal result checker"
                )

            await asyncio.sleep(
                max(5, RESULT_CHECKER_INTERVAL_SECONDS)
            )

    async def get_expired_signals(self) -> list[Signal]:
        now = utc_now()

        async with get_session() as session:
            query = (
                select(Signal)
                .where(
                    Signal.result == SIGNAL_RESULT_PENDING,
                    Signal.expires_at <= now,
                )
                .order_by(
                    Signal.expires_at.asc(),
                )
                .limit(100)
            )

            result = await session.execute(query)

            return list(result.scalars().all())

    async def check_expired_signals(self) -> int:
        signals = await self.get_expired_signals()

        if not signals:
            return 0

        grouped: dict[str, list[Signal]] = defaultdict(list)

        for signal in signals:
            grouped[signal.pair].append(signal)

        processed = 0

        for pair, pair_signals in grouped.items():
            try:
                candles = await self.market.get_candles(
                    pair=pair,
                    interval="1min",
                    outputsize=300,
                    force_refresh=True,
                )
            except Exception:
                logger.exception(
                    "Failed to fetch result candles for %s",
                    pair,
                )
                continue

            if candles is None or candles.empty:
                logger.warning(
                    "No candles available for result checking: %s",
                    pair,
                )
                continue

            for signal in pair_signals:
                try:
                    close_price = self.market.get_close_for_expiry(
                        candles,
                        signal.expires_at,
                    )

                    if close_price is None:
                        logger.warning(
                            "Expiry candle unavailable for signal %s",
                            signal.id,
                        )
                        continue

                    result = self._calculate_result(
                        direction=signal.direction,
                        entry_price=float(signal.entry_price),
                        close_price=float(close_price),
                    )

                    updated_signal = await self._save_result(
                        signal_id=signal.id,
                        result=result,
                        close_price=float(close_price),
                    )

                    if updated_signal is None:
                        continue

                    await notify_signal_result(
                        bot=self.bot,
                        signal=updated_signal,
                    )

                    processed += 1

                except Exception:
                    logger.exception(
                        "Failed to process signal %s",
                        signal.id,
                    )

        return processed

    @staticmethod
    def _calculate_result(
        *,
        direction: str,
        entry_price: float,
        close_price: float,
    ) -> str:
        epsilon = max(
            abs(entry_price) * 1e-8,
            1e-10,
        )

        direction = direction.upper().strip()

        if abs(close_price - entry_price) <= epsilon:
            return SIGNAL_RESULT_DRAW

        if direction in {"UP", "CALL", "BUY"}:
            if close_price > entry_price:
                return SIGNAL_RESULT_WIN

            return SIGNAL_RESULT_LOSS

        if direction in {"DOWN", "PUT", "SELL"}:
            if close_price < entry_price:
                return SIGNAL_RESULT_WIN

            return SIGNAL_RESULT_LOSS

        return SIGNAL_RESULT_DRAW

    async def _save_result(
        self,
        *,
        signal_id: int,
        result: str,
        close_price: float,
    ) -> Signal | None:
        async with get_session() as session:
            signal = await session.get(
                Signal,
                signal_id,
            )

            if signal is None:
                return None

            if signal.result != SIGNAL_RESULT_PENDING:
                return signal

            signal.result = result
            signal.close_price = close_price
            signal.checked_at = utc_now()

            await session.commit()
            await session.refresh(signal)

            return signal


async def run_result_check_once(
    bot,
    market_client: MarketClient | None = None,
) -> int:
    checker = SignalResultChecker(
        bot=bot,
        market_client=market_client,
    )

    try:
        return await checker.check_expired_signals()
    finally:
        try:
            await checker.market.close()
        except Exception:
            pass
