from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import (
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    DATABASE_URL,
)


def normalize_database_url(url: str) -> str:
    url = url.strip()

    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]

    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]

    return url


DATABASE_ASYNC_URL = normalize_database_url(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
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
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )

    blacklist_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_auto_signals_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    join_requests: Mapped[list["JoinRequest"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )

    processed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(
        back_populates="join_requests",
    )


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    market: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="regular",
        index=True,
    )

    pair: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
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

    winrate_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    winrate_wins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    winrate_losses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    winrate_draws: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    confirmations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
    )

    reasons: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
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
        autoincrement=True,
    )

    signal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "signal_id",
            "telegram_id",
            name="uq_signal_recipient",
        ),
    )


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    key: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OwnerSetting(Base):
    __tablename__ = "owner_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    key: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


engine: AsyncEngine = create_async_engine(
    DATABASE_ASYNC_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def get_user(
    session: AsyncSession,
    telegram_id: int,
) -> User | None:
    result = await session.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    user = await get_user(session, telegram_id)

    if user is not None:
        changed = False

        if username != user.username:
            user.username = username
            changed = True

        if first_name != user.first_name:
            user.first_name = first_name
            changed = True

        if changed:
            await session.commit()
            await session.refresh(user)

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
) -> JoinRequest:
    request = JoinRequest(
        telegram_id=telegram_id,
        status="pending",
    )

    session.add(request)

    await session.commit()
    await session.refresh(request)

    return request
