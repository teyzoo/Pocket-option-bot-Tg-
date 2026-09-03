from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import (
    DB_MAX_OVERFLOW,
    DB_POOL_SIZE,
    DATABASE_URL,
)


def normalize_database_url(url: str) -> str:
    url = url.strip()

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        url = (
            "postgresql+asyncpg://"
            + url[len("postgresql://"):]
        )

    return url


DATABASE_ASYNC_URL = normalize_database_url(
    DATABASE_URL
)


engine = create_async_engine(
    DATABASE_ASYNC_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
)


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
        nullable=False,
    )

    blacklist_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_auto_signals_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    processed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    pair: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
    )

    market: Mapped[str] = mapped_column(
        String(20),
        default="regular",
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    expiry_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    quality: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    winrate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    close_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    result: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        default="manual",
        nullable=False,
    )

    reasons: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    chart_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SignalRecipient(Base):
    __tablename__ = "signal_recipients"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    signal_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        nullable=False,
    )

    message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class BotText(Base):
    __tablename__ = "bot_texts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class BotSetting(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )


async def close_db() -> None:
    await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_user(
    telegram_id: int,
) -> User | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        return result.scalar_one_or_none()


async def get_or_create_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    now = datetime.utcnow()

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                status="pending",
                is_auto_signals_enabled=True,
                created_at=now,
                updated_at=now,
            )

            session.add(user)

        else:
            user.username = username
            user.first_name = first_name
            user.updated_at = now

        await session.commit()
        await session.refresh(user)

        return user


async def create_join_request(
    telegram_id: int,
) -> JoinRequest:
    now = datetime.utcnow()

    async with get_session() as session:
        result = await session.execute(
            select(JoinRequest)
            .where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == "pending",
            )
            .order_by(JoinRequest.id.desc())
        )

        existing = result.scalars().first()

        if existing:
            return existing

        request = JoinRequest(
            telegram_id=telegram_id,
            status="pending",
            created_at=now,
        )

        session.add(request)

        await session.commit()
        await session.refresh(request)

        return request
