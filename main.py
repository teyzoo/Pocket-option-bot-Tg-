from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramConflictError
from fastapi import FastAPI
from sqlalchemy import text

from admin import router as admin_router
from config import BOT_TOKEN
from database import close_db, engine as db_engine, init_db
from handlers import router as handlers_router
from owner import router as owner_router
from scheduler import SignalScheduler
from signal_engine import SignalEngine
from signal_result_checker import SignalResultChecker
from signal_scanner import SignalScanner


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("main")


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(owner_router)
dp.include_router(admin_router)
dp.include_router(handlers_router)


signal_engine = SignalEngine()
scanner = SignalScanner(engine=signal_engine)

scheduler = SignalScheduler(
    bot=bot,
    scanner=scanner,
)

result_checker = SignalResultChecker(
    bot=bot,
)


# Один advisory-lock PostgreSQL на весь бот.
#
# Даже если Render на короткое время поднимет второй процесс
# во время перезапуска/деплоя, только один процесс получит lock
# и будет выполнять Telegram polling + scheduler + result checker.
BOT_LEADER_LOCK_ID = 8921947623

_bot_lock_connection = None
_bot_lock_acquired = False


async def acquire_bot_leader_lock() -> bool:
    """
    Получает PostgreSQL advisory lock.

    Важно:
    connection необходимо держать открытым всё время,
    пока процесс является лидером.
    """

    global _bot_lock_connection
    global _bot_lock_acquired

    if _bot_lock_acquired:
        return True

    while True:
        connection = None

        try:
            connection = await db_engine.connect()

            result = await connection.execute(
                text(
                    "SELECT pg_try_advisory_lock(:lock_id)"
                ),
                {
                    "lock_id": BOT_LEADER_LOCK_ID,
                },
            )

            acquired = bool(result.scalar())

            if acquired:
                _bot_lock_connection = connection
                _bot_lock_acquired = True

                logger.info(
                    "Bot leader lock acquired. "
                    "This process will run Telegram polling and background jobs."
                )

                return True

            await connection.close()

            logger.warning(
                "Another bot process is already leader. "
                "Waiting for leader lock..."
            )

        except asyncio.CancelledError:
            if connection is not None:
                try:
                    await connection.close()
                except Exception:
                    pass
            raise

        except Exception:
            logger.exception(
                "Failed to acquire PostgreSQL leader lock. "
                "Retrying in 5 seconds..."
            )

            if connection is not None:
                try:
                    await connection.close()
                except Exception:
                    pass

        await asyncio.sleep(5)


async def release_bot_leader_lock() -> None:
    """
    Освобождает advisory lock.
    """

    global _bot_lock_connection
    global _bot_lock_acquired

    connection = _bot_lock_connection

    _bot_lock_connection = None
    _bot_lock_acquired = False

    if connection is None:
        return

    try:
        await connection.execute(
            text(
                "SELECT pg_advisory_unlock(:lock_id)"
            ),
            {
                "lock_id": BOT_LEADER_LOCK_ID,
            },
        )
    except Exception:
        logger.exception("Failed to release bot leader lock")
    finally:
        try:
            await connection.close()
        except Exception:
            logger.exception("Failed to close leader lock connection")


async def polling_loop() -> None:
    """
    Telegram polling.

    Вторая копия бота не должна запускать polling благодаря
    PostgreSQL advisory lock.

    TelegramConflictError дополнительно обрабатывается,
    чтобы временный конфликт не убивал приложение.
    """

    while True:
        try:
            logger.info("Removing Telegram webhook...")
            await bot.delete_webhook(drop_pending_updates=False)

            logger.info("Telegram polling starting...")
            await dp.start_polling(
                bot,
                handle_signals=False,
            )

            logger.warning(
                "Telegram polling stopped normally. "
                "Restarting in 5 seconds..."
            )

        except asyncio.CancelledError:
            logger.info("Telegram polling task cancelled.")
            raise

        except TelegramConflictError:
            logger.error(
                "TelegramConflictError: another getUpdates request "
                "is currently active. Waiting 15 seconds..."
            )
            await asyncio.sleep(15)

        except Exception:
            logger.exception(
                "Telegram polling crashed. Restarting in 15 seconds..."
            )
            await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle.
    """

    global scanner
    global scheduler
    global result_checker

    logger.info("Initializing database...")

    await init_db()

    leader_acquired = False
    polling_task: Optional[asyncio.Task] = None
    background_started = False

    try:
        # Получаем глобальный lock до запуска фоновых задач.
        await acquire_bot_leader_lock()
        leader_acquired = True

        logger.info("Starting Telegram polling task...")
        polling_task = asyncio.create_task(
            polling_loop(),
            name="telegram-polling",
        )

        logger.info("Starting signal scheduler...")
        await scheduler.start()

        logger.info("Starting signal result checker...")
        await result_checker.start()

        background_started = True

        logger.info(
            "TEYZOO Signal Bot started successfully."
        )

        logger.info(
            "Automatic signal loop is active."
        )

        yield

    except asyncio.CancelledError:
        raise

    finally:
        logger.info("Stopping TEYZOO Signal Bot...")

        if background_started:
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
                    "Failed to stop signal result checker"
                )

        if polling_task is not None:
            polling_task.cancel()

            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception(
                    "Telegram polling task stopped with error"
                )

        if leader_acquired:
            await release_bot_leader_lock()

        try:
            await bot.session.close()
        except Exception:
            logger.exception(
                "Failed to close Telegram bot session"
            )

        await close_db()

        logger.info("TEYZOO Signal Bot stopped.")


app = FastAPI(
    title="TEYZOO Signal Bot",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "TEYZOO Signal Bot",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "TEYZOO Signal Bot",
        "leader": _bot_lock_acquired,
    }
