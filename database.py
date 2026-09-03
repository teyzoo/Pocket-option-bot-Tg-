from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import (
    DATABASE_URL,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )

    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
        nullable=False,
    )

    blacklist_reason: Mapped[str | None] = mapped_column(Text)
    is_auto_signals_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer,
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
        default=utcnow,
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    processed_by: Mapped[int | None] = mapped_column(Integer)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    pair: Mapped[str] = mapped_column(
        String(30),
        index=True,
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

    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    close_price: Mapped[float | None] = mapped_column(Float)

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

    reasons: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class SignalRecipient(Base):
    __tablename__ = "signal_recipients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    signal_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )

    telegram_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )

    message_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_user(
    session: AsyncSession,
    telegram_id: int,
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    user = await get_user(session, telegram_id)

    if user:
        changed = False

        if username != user.username:
            user.username = username
            changed = True

        if first_name != user.first_name:
            user.first_name = first_name
            changed = True

        if changed:
            await session.commit()

        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        status="pending",
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def create_join_request(
    session: AsyncSession,
    telegram_id: int,
) -> JoinRequest | None:
    existing = await session.execute(
        select(JoinRequest)
        .where(
            JoinRequest.telegram_id == telegram_id,
            JoinRequest.status == "pending",
        )
        .order_by(JoinRequest.id.desc())
    )

    if existing.scalar_one_or_none():
        return None

    request = JoinRequest(
        telegram_id=telegram_id,
        status="pending",
    )

    session.add(request)
    await session.commit()
    await session.refresh(request)

    return request
