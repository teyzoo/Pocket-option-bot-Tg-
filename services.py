from __future__ import annotations

import logging
import os

from sqlalchemy import select

from config import (
    ACCESS_APPROVED,
    ACCESS_BLACKLISTED,
    ACCESS_PENDING,
    ACCESS_REJECTED,
)
from database import (
    JoinRequest,
    User,
    get_session,
)
from time_utils import utc_now

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ADMIN / OWNER
# ---------------------------------------------------------------------------

def _parse_ids(*env_names: str) -> set[int]:
    """
    Читает Telegram ID из нескольких переменных окружения.

    Поддерживается:
        ADMIN_IDS=123,456
        OWNER_IDS=123,456
        OWNER_ID=123

    Значения объединяются.
    """

    result: set[int] = set()

    for env_name in env_names:
        raw = os.getenv(env_name, "")

        for item in raw.replace(";", ",").split(","):
            item = item.strip()

            if not item:
                continue

            try:
                result.add(int(item))
            except ValueError:
                logger.warning(
                    "Invalid Telegram ID in %s: %r",
                    env_name,
                    item,
                )

    return result


def get_admin_ids() -> set[int]:
    return _parse_ids(
        "ADMIN_IDS",
        "OWNER_IDS",
        "OWNER_ID",
    )


def get_owner_ids() -> set[int]:
    return _parse_ids(
        "OWNER_IDS",
        "OWNER_ID",
    )


def is_admin_user(telegram_id: int) -> bool:
    return int(telegram_id) in get_admin_ids()


def is_owner_user(telegram_id: int) -> bool:
    return int(telegram_id) in get_owner_ids()


# ---------------------------------------------------------------------------
# USER
# ---------------------------------------------------------------------------

async def get_user(
    telegram_id: int,
) -> User | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == int(telegram_id)
            )
        )

        return result.scalar_one_or_none()


async def get_user_access_status(
    telegram_id: int,
) -> str | None:
    """
    Возвращает статус пользователя.

    Для администратора/владельца доступ всегда считается approved.
    Это дополнительно защищает от старого pending/rejected состояния
    в базе данных.
    """

    telegram_id = int(telegram_id)

    if is_admin_user(telegram_id):
        return ACCESS_APPROVED

    user = await get_user(telegram_id)

    if user is None:
        return None

    return user.status


# ---------------------------------------------------------------------------
# ENSURE PRIVILEGED USER
# ---------------------------------------------------------------------------

async def ensure_privileged_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User | None:
    """
    Гарантирует, что владелец/администратор имеет approved-доступ.

    Важно:
    - существующий pending превращается в approved;
    - rejected превращается в approved;
    - автоматически включаются сигналы;
    - pending JoinRequest закрываются;
    - обычные пользователи этой функцией не проходят.
    """

    telegram_id = int(telegram_id)

    if not is_admin_user(telegram_id):
        return None

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()
        now = utc_now()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                status=ACCESS_APPROVED,
                is_auto_signals_enabled=True,
                created_at=now,
                updated_at=now,
            )

            session.add(user)

        else:
            user.username = username
            user.first_name = first_name
            user.status = ACCESS_APPROVED
            user.is_auto_signals_enabled = True
            user.blacklist_reason = None
            user.updated_at = now

        # Закрываем старые заявки администратора.
        requests_result = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == ACCESS_PENDING,
            )
        )

        for request in requests_result.scalars().all():
            request.status = ACCESS_APPROVED
            request.processed_at = now
            request.processed_by = telegram_id

        await session.commit()
        await session.refresh(user)

        logger.info(
            "Privileged user ensured: telegram_id=%s status=%s",
            telegram_id,
            user.status,
        )

        return user


# ---------------------------------------------------------------------------
# ACCESS REQUEST
# ---------------------------------------------------------------------------

async def request_access(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> JoinRequest:
    telegram_id = int(telegram_id)

    # -----------------------------------------------------------------------
    # ВАЖНО:
    # Если это admin/owner, вообще не создаём заявку.
    # -----------------------------------------------------------------------

    if is_admin_user(telegram_id):
        user = await ensure_privileged_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

        async with get_session() as session:
            result = await session.execute(
                select(JoinRequest)
                .where(
                    JoinRequest.telegram_id == telegram_id
                )
                .order_by(
                    JoinRequest.created_at.desc()
                )
            )

            request = result.scalars().first()

            if request is None:
                now = utc_now()

                request = JoinRequest(
                    telegram_id=telegram_id,
                    status=ACCESS_APPROVED,
                    created_at=now,
                    processed_at=now,
                    processed_by=telegram_id,
                )

                session.add(request)
                await session.commit()
                await session.refresh(request)

            return request

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()
        now = utc_now()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                status=ACCESS_PENDING,
                is_auto_signals_enabled=False,
                created_at=now,
                updated_at=now,
            )

            session.add(user)

        else:
            user.username = username
            user.first_name = first_name
            user.updated_at = now

            if user.status == ACCESS_BLACKLISTED:
                existing = await _latest_join_request(
                    session,
                    telegram_id,
                )

                if existing is not None:
                    await session.commit()
                    return existing

            if user.status == ACCESS_APPROVED:
                existing = await _latest_join_request(
                    session,
                    telegram_id,
                )

                if existing is not None:
                    await session.commit()
                    return existing

            user.status = ACCESS_PENDING

        existing = await session.execute(
            select(JoinRequest)
            .where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == ACCESS_PENDING,
            )
            .order_by(
                JoinRequest.created_at.desc()
            )
        )

        request = existing.scalars().first()

        if request is None:
            request = JoinRequest(
                telegram_id=telegram_id,
                status=ACCESS_PENDING,
                created_at=now,
                processed_at=None,
                processed_by=None,
            )

            session.add(request)

        await session.commit()
        await session.refresh(request)

        return request


# ---------------------------------------------------------------------------
# APPROVE
# ---------------------------------------------------------------------------

async def approve_user(
    telegram_id: int,
    processed_by: int,
) -> User | None:
    telegram_id = int(telegram_id)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        if user.status == ACCESS_BLACKLISTED:
            return user

        now = utc_now()

        user.status = ACCESS_APPROVED
        user.blacklist_reason = None
        user.updated_at = now

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == ACCESS_PENDING,
            )
        )

        for request in requests.scalars().all():
            request.status = ACCESS_APPROVED
            request.processed_at = now
            request.processed_by = int(processed_by)

        await session.commit()
        await session.refresh(user)

        return user


# ---------------------------------------------------------------------------
# REJECT
# ---------------------------------------------------------------------------

async def reject_user(
    telegram_id: int,
    processed_by: int,
) -> User | None:
    telegram_id = int(telegram_id)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        if user.status == ACCESS_BLACKLISTED:
            return user

        now = utc_now()

        user.status = ACCESS_REJECTED
        user.is_auto_signals_enabled = False
        user.updated_at = now

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == ACCESS_PENDING,
            )
        )

        for request in requests.scalars().all():
            request.status = ACCESS_REJECTED
            request.processed_at = now
            request.processed_by = int(processed_by)

        await session.commit()
        await session.refresh(user)

        return user


# ---------------------------------------------------------------------------
# BLACKLIST
# ---------------------------------------------------------------------------

async def blacklist_user(
    telegram_id: int,
    reason: str,
    processed_by: int,
) -> User | None:
    telegram_id = int(telegram_id)

    reason = (
        reason.strip()
        if reason
        else "Причина не указана"
    )

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        now = utc_now()

        user.status = ACCESS_BLACKLISTED
        user.blacklist_reason = reason
        user.is_auto_signals_enabled = False
        user.updated_at = now

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == ACCESS_PENDING,
            )
        )

        for request in requests.scalars().all():
            request.status = ACCESS_BLACKLISTED
            request.processed_at = now
            request.processed_by = int(processed_by)

        await session.commit()
        await session.refresh(user)

        return user


# ---------------------------------------------------------------------------
# UNBLACKLIST
# ---------------------------------------------------------------------------

async def unblacklist_user(
    telegram_id: int,
    processed_by: int,
) -> User | None:
    telegram_id = int(telegram_id)

    # Админ/owner после снятия блокировки всё равно должен оставаться
    # привилегированным.
    if is_admin_user(telegram_id):
        user = await get_user(telegram_id)

        if user is not None:
            return await ensure_privileged_user(
                telegram_id=telegram_id,
                username=user.username,
                first_name=user.first_name,
            )

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return None

        now = utc_now()

        user.status = ACCESS_PENDING
        user.blacklist_reason = None
        user.is_auto_signals_enabled = False
        user.updated_at = now

        requests = await session.execute(
            select(JoinRequest).where(
                JoinRequest.telegram_id == telegram_id,
                JoinRequest.status == ACCESS_PENDING,
            )
        )

        existing_pending = requests.scalars().first()

        if existing_pending is None:
            session.add(
                JoinRequest(
                    telegram_id=telegram_id,
                    status=ACCESS_PENDING,
                    created_at=now,
                    processed_at=None,
                    processed_by=None,
                )
            )

        await session.commit()
        await session.refresh(user)

        return user


# ---------------------------------------------------------------------------
# AUTO SIGNALS
# ---------------------------------------------------------------------------

async def set_auto_signals(
    telegram_id: int,
    enabled: bool,
) -> bool:
    telegram_id = int(telegram_id)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            return False

        # Админ/owner всегда имеет approved-доступ.
        if is_admin_user(telegram_id):
            user.status = ACCESS_APPROVED

        if user.status != ACCESS_APPROVED:
            user.is_auto_signals_enabled = False
            await session.commit()
            return False

        user.is_auto_signals_enabled = bool(enabled)
        user.updated_at = utc_now()

        await session.commit()

        return bool(
            user.is_auto_signals_enabled
        )


# ---------------------------------------------------------------------------
# PENDING
# ---------------------------------------------------------------------------

async def get_pending_requests() -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .where(
                User.status == ACCESS_PENDING
            )
            .order_by(
                User.created_at.asc()
            )
        )

        return list(
            result.scalars().all()
        )


# ---------------------------------------------------------------------------
# APPROVED AUTO USERS
# ---------------------------------------------------------------------------

async def get_approved_auto_users() -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .where(
                User.status == ACCESS_APPROVED,
                User.is_auto_signals_enabled.is_(True),
            )
            .order_by(
                User.id.asc()
            )
        )

        return list(
            result.scalars().all()
        )


# ---------------------------------------------------------------------------
# APPROVED USERS
# ---------------------------------------------------------------------------

async def get_approved_users() -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .where(
                User.status == ACCESS_APPROVED
            )
            .order_by(
                User.id.asc()
            )
        )

        return list(
            result.scalars().all()
        )


# ---------------------------------------------------------------------------
# LATEST JOIN REQUEST
# ---------------------------------------------------------------------------

async def _latest_join_request(
    session,
    telegram_id: int,
) -> JoinRequest | None:
    result = await session.execute(
        select(JoinRequest)
        .where(
            JoinRequest.telegram_id == int(
                telegram_id
            )
        )
        .order_by(
            JoinRequest.created_at.desc()
        )
    )

    return result.scalars().first()
