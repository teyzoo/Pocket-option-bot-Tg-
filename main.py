from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from fastapi import FastAPI

from admin import router as admin_router
from config import BOT_TOKEN
from database import (
    close_db,
    init_db,
)
from handlers import router as user_router
from market import market_client
from owner import router as owner_router
from scheduler import SignalScheduler
from signal_engine import SignalEngine
from signal_result_checker import (
    SignalResultChecker,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "teyzoo"
)


bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()

dp.include_router(
    admin_router
)

dp.include_router(
    owner_router
)

dp.include_router(
    user_router
)


engine = SignalEngine()

scheduler = SignalScheduler(
    bot=bot,
    market=market_client,
    engine=engine,
)

result_checker = SignalResultChecker(
    bot=bot,
    market=market_client,
)


async def polling_loop() -> None:
    logger.info(
        "Telegram polling starting"
    )

    await dp.start_polling(
        bot,
        allowed_updates=(
            dp.resolve_used_update_types()
        ),
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
        polling_loop()
    )

    scheduler_task = asyncio.create_task(
        scheduler.run()
    )

    result_task = asyncio.create_task(
        result_checker.run()
    )

    logger.info(
        "TEYZOO Signal Bot started"
    )

    try:
        yield

    finally:
        logger.info(
            "Stopping bot"
        )

        for task in (
            polling_task,
            scheduler_task,
            result_task,
        ):
            task.cancel()

        await asyncio.gather(
            polling_task,
            scheduler_task,
            result_task,
            return_exceptions=True,
        )

        await bot.session.close()

        await close_db()

        logger.info(
            "Bot stopped"
        )


app = FastAPI(
    title="TEYZOO Signal Bot",
    version="2.0.0",
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
