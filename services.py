from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from database import (
    JoinRequest,
    User,
    get_or_create_user,
    get_session,
)


async def request_access(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
):
    user = await get_or_create_user(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
    )

    if user.status in {
        "approved",
        "blacklisted",
    }:
        return user, None

    async with get_session() as session:
        result = await session.execute(
            select(JoinRequest)
            .where(
                JoinRequest.telegram_id
                == telegram_id,
                JoinRequest.status
                == "pending",
            )
            .order_by(
                JoinRequest.id.desc()
            )
        )

        request = result.scalars().first()

        if request is not None:
            return user, request

        request = JoinRequest(
            telegram_id=telegram_id,
            status="pending",
            created_at=datetime.utcnow(),
        )

        user_result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        db_user = user_result.scalar_one()

        db_user.status = "pending"
        db_user.updated_at = datetime.utcnow()

        session.add(request)

        await session.commit()

        return db_user, request


async def approve_user(
    telegram_id: int,
    admin_id: int,
) -> User | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        user.status = "approved"
        user.blacklist_reason = None
        user.updated_at = datetime.utcnow()

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id
                == telegram_id,
                JoinRequest.status
                == "pending",
            )
        )

        for request in requests.scalars():
            request.status = "approved"
            request.processed_at = datetime.utcnow()
            request.processed_by = admin_id

        await session.commit()

        return user


async def reject_user(
    telegram_id: int,
    admin_id: int,
) -> User | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        user.status = "rejected"
        user.updated_at = datetime.utcnow()

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id
                == telegram_id,
                JoinRequest.status
                == "pending",
            )
        )

        for request in requests.scalars():
            request.status = "rejected"
            request.processed_at = datetime.utcnow()
            request.processed_by = admin_id

        await session.commit()

        return user


async def blacklist_user(
    telegram_id: int,
    admin_id: int,
    reason: str | None,
) -> User | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        user.status = "blacklisted"
        user.blacklist_reason = reason
        user.updated_at = datetime.utcnow()

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id
                == telegram_id,
                JoinRequest.status
                == "pending",
            )
        )

        for request in requests.scalars():
            request.status = "rejected"
            request.processed_at = datetime.utcnow()
            request.processed_by = admin_id

        await session.commit()

        return user


async def unblacklist_user(
    telegram_id: int,
) -> User | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        user.status = "pending"
        user.blacklist_reason = None
        user.updated_at = datetime.utcnow()

        await session.commit()

        return user
