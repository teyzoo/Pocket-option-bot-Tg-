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


# ============================================================
# LOGGING
# ============================================================

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


# ============================================================
# TELEGRAM
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
)

dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(owner_router)
dp.include_router(user_router)


# ============================================================
# SIGNAL ENGINE / SCANNER
# ============================================================

engine = SignalEngine()

scanner = SignalScanner(
    market=market_client,
    engine=engine,
)


# ============================================================
# SCHEDULER
# ============================================================

scheduler = SignalScheduler(
    bot=bot,
    scanner=scanner,
)


# ============================================================
# RESULT CHECKER
# ============================================================

result_checker = SignalResultChecker(
    bot=bot,
    market_client=market_client,
)


# ============================================================
# TELEGRAM POLLING
# ============================================================

async def polling_loop() -> None:
    """
    Надёжный Telegram polling.

    Если Telegram сообщает ConflictError, приложение не падает.
    Повторяем подключение с задержкой.

    ВАЖНО:
    если реально запущены два независимых процесса с одним BOT_TOKEN,
    только один из них сможет получать updates.
    """

    logger.info(
        "Telegram polling starting"
    )

    retry_delay = 5

    while True:
        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
            )

            logger.warning(
                "Telegram polling stopped normally; "
                "restarting in %s seconds",
                retry_delay,
            )

            await asyncio.sleep(
                retry_delay
            )

        except TelegramConflictError:
            logger.error(
                "Telegram polling conflict: "
                "another process is using the same BOT_TOKEN. "
                "Retrying in 15 seconds."
            )

            await asyncio.sleep(15)

        except asyncio.CancelledError:
            logger.info(
                "Telegram polling cancelled"
            )
            raise

        except Exception:
            logger.exception(
                "Telegram polling stopped with error; "
                "retrying in 10 seconds"
            )

            await asyncio.sleep(10)


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

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

    # --------------------------------------------------------
    # Telegram polling
    # --------------------------------------------------------

    polling_task = asyncio.create_task(
        polling_loop(),
        name="telegram-polling",
    )

    # --------------------------------------------------------
    # Scheduler
    # --------------------------------------------------------

    await scheduler.start()

    # --------------------------------------------------------
    # Result checker
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # Scheduler
        # ----------------------------------------------------

        try:
            await scheduler.stop()

        except Exception:
            logger.exception(
                "Failed to stop signal scheduler"
            )

        # ----------------------------------------------------
        # Result checker
        # ----------------------------------------------------

        try:
            await result_checker.stop()

        except Exception:
            logger.exception(
                "Failed to stop result checker"
            )

        # ----------------------------------------------------
        # Telegram polling
        # ----------------------------------------------------

        polling_task.cancel()

        try:
            await polling_task

        except asyncio.CancelledError:
            pass

        except Exception:
            logger.exception(
                "Telegram polling shutdown error"
            )

        # ----------------------------------------------------
        # Telegram session
        # ----------------------------------------------------

        try:
            await bot.session.close()

        except Exception:
            logger.exception(
                "Failed to close Telegram bot session"
            )

        # ----------------------------------------------------
        # Database
        # ----------------------------------------------------

        try:
            await close_db()

        except Exception:
            logger.exception(
                "Failed to close database"
            )

        # ----------------------------------------------------
        # Market client
        # ----------------------------------------------------

        try:
            await market_client.close()

        except Exception:
            logger.exception(
                "Failed to close market client"
            )

        logger.info(
            "TEYZOO Signal Bot stopped"
        )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="TEYZOO Signal Bot",
    version="2.1.0",
    lifespan=lifespan,
)


# ============================================================
# ROUTES
# ============================================================

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
