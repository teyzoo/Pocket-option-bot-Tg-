from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramConflictError
from fastapi import FastAPI

from admin import router as admin_router
from config import BOT_TOKEN
from database import close_db, init_db
from handlers import router as user_router
from market import market_client
from owner import router as owner_router
from scheduler import SignalScheduler
from signal_engine import SignalEngine
from signal_result_checker import SignalResultChecker
from signal_scanner import SignalScanner


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("teyzoo")


bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(owner_router)
dp.include_router(user_router)


engine = SignalEngine()

scanner = SignalScanner(
    market=market_client,
    engine=engine,
)

scheduler = SignalScheduler(
    bot=bot,
    scanner=scanner,
)

result_checker = SignalResultChecker(
    bot=bot,
    market_client=market_client,
)


_polling_started = False


async def polling_loop() -> None:
    global _polling_started

    if _polling_started:
        logger.warning(
            "Telegram polling already started; duplicate start prevented"
        )
        return

    _polling_started = True

    logger.info("Telegram polling starting")

    try:
        # Убираем webhook, если он остался после предыдущего запуска.
        try:
            await bot.delete_webhook(
                drop_pending_updates=False
            )
            logger.info(
                "Telegram webhook removed before polling"
            )
        except Exception:
            logger.exception(
                "Failed to remove Telegram webhook"
            )

        retry_delay = 15

        while True:
            try:
                logger.info(
                    "Starting Telegram getUpdates polling"
                )

                await dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                )

                logger.warning(
                    "Telegram polling stopped normally; "
                    "retrying in %s seconds",
                    retry_delay,
                )

                await asyncio.sleep(retry_delay)

            except TelegramConflictError:
                logger.error(
                    "Telegram Conflict: another bot process "
                    "is currently using getUpdates. "
                    "Waiting %s seconds before retry.",
                    retry_delay,
                )

                await asyncio.sleep(retry_delay)

            except asyncio.CancelledError:
                logger.info(
                    "Telegram polling cancelled"
                )
                raise

            except Exception:
                logger.exception(
                    "Telegram polling error; "
                    "retrying in %s seconds",
                    retry_delay,
                )

                await asyncio.sleep(retry_delay)

    finally:
        _polling_started = False

        logger.info(
            "Telegram polling stopped"
        )


@asynccontextmanager
async def lifespan(
    application: FastAPI,
):
    logger.info(
        "Initializing database"
    )

    await init_db()

    logger.info(
        "Database initialized"
    )

    polling_task = asyncio.create_task(
        polling_loop(),
        name="telegram-polling",
    )

    await scheduler.start()

    await result_checker.start()

    logger.info(
        "TEYZOO Signal Bot started"
    )

    try:
        yield

    finally:
        logger.info(
            "Stopping TEYZOO Signal Bot"
        )

        try:
            await scheduler.stop()
        except Exception:
            logger.exception(
                "Failed to stop signal scheduler"
            )

        try:
            await result_checker.stop()
        except Exception:
            logger.exception(
                "Failed to stop result checker"
            )

        polling_task.cancel()

        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception(
                "Telegram polling shutdown error"
            )

        try:
            await bot.session.close()
        except Exception:
            logger.exception(
                "Failed to close Telegram bot session"
            )

        try:
            await market_client.close()
        except Exception:
            logger.exception(
                "Failed to close market client"
            )

        try:
            await close_db()
        except Exception:
            logger.exception(
                "Failed to close database"
            )

        logger.info(
            "TEYZOO Signal Bot stopped"
        )


app = FastAPI(
    title="TEYZOO Signal Bot",
    version="2.2.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "service": "TEYZOO Signal Bot",
    }


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "TEYZOO Signal Bot",
    }
