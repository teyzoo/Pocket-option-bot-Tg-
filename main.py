from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from fastapi import FastAPI

from admin import router as admin_router
from config import BOT_TOKEN
from database import close_db, init_db
from handlers import router as user_router
from scheduler import SignalScheduler
from signal_result_checker import SignalResultChecker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("teyzoo")


bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(user_router)


scheduler: SignalScheduler | None = None
result_checker: SignalResultChecker | None = None

bot_task: asyncio.Task | None = None
scheduler_task: asyncio.Task | None = None
result_checker_task: asyncio.Task | None = None


async def polling_loop() -> None:
    logger.info("Starting Telegram polling...")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Telegram polling stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    global result_checker
    global bot_task
    global scheduler_task
    global result_checker_task

    logger.info("Initializing database...")

    await init_db()

    logger.info("Database initialized")

    scheduler = SignalScheduler(bot)
    result_checker = SignalResultChecker(bot)

    bot_task = asyncio.create_task(
        polling_loop()
    )

    scheduler_task = asyncio.create_task(
        scheduler.run()
    )

    result_checker_task = asyncio.create_task(
        result_checker.run()
    )

    logger.info("TEYZOO SIGNAL BOT started")

    try:
        yield

    finally:
        logger.info("Stopping TEYZOO SIGNAL BOT...")

        tasks = [
            bot_task,
            scheduler_task,
            result_checker_task,
        ]

        for task in tasks:
            if task is not None:
                task.cancel()

        await asyncio.gather(
            *[
                task
                for task in tasks
                if task is not None
            ],
            return_exceptions=True,
        )

        await bot.session.close()

        await close_db()

        logger.info("TEYZOO SIGNAL BOT stopped")


app = FastAPI(
    title="TEYZOO Signal Bot",
    version="1.0.0",
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
