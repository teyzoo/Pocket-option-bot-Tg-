from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import delete, select

from database import (
    BotMessage,
    OwnerSetting,
    get_session,
)
from messages import get_default_message
from time_utils import utc_now


async def get_setting(
    key: str,
    default: str | None = None,
) -> str | None:
    now = utc_now()

    async with get_session() as session:
        result = await session.execute(
            select(OwnerSetting).where(
                OwnerSetting.key == key
            )
        )

        setting = result.scalar_one_or_none()

        if setting is None:
            return default

        if (
            setting.expires_at is not None
            and setting.expires_at <= now
        ):
            await session.delete(
                setting
            )
            await session.commit()

            return default

        return setting.value


async def set_setting(
    key: str,
    value: str,
    updated_by: int | None = None,
    expires_at: datetime | None = None,
) -> OwnerSetting:
    async with get_session() as session:
        result = await session.execute(
            select(OwnerSetting).where(
                OwnerSetting.key == key
            )
        )

        setting = result.scalar_one_or_none()

        if setting is None:
            setting = OwnerSetting(
                key=key,
                value=value,
                expires_at=expires_at,
                updated_by=updated_by,
                updated_at=utc_now(),
            )

            session.add(setting)

        else:
            setting.value = value
            setting.expires_at = expires_at
            setting.updated_by = updated_by
            setting.updated_at = utc_now()

        await session.commit()
        await session.refresh(setting)

        return setting


async def delete_setting(
    key: str,
) -> None:
    async with get_session() as session:
        await session.execute(
            delete(OwnerSetting).where(
                OwnerSetting.key == key
            )
        )

        await session.commit()


async def get_bool_setting(
    key: str,
    default: bool = False,
) -> bool:
    value = await get_setting(
        key
    )

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
        "вкл",
    }


async def get_int_setting(
    key: str,
    default: int,
) -> int:
    value = await get_setting(
        key
    )

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


async def get_json_setting(
    key: str,
    default: object | None = None,
) -> object | None:
    value = await get_setting(
        key
    )

    if value is None:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


async def set_json_setting(
    key: str,
    value: object,
    updated_by: int | None = None,
    expires_at: datetime | None = None,
) -> OwnerSetting:
    return await set_setting(
        key=key,
        value=json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        ),
        updated_by=updated_by,
        expires_at=expires_at,
    )


async def get_message(
    key: str,
) -> str:
    async with get_session() as session:
        result = await session.execute(
            select(BotMessage).where(
                BotMessage.key == key
            )
        )

        message = result.scalar_one_or_none()

        if message is None:
            return get_default_message(key)

        return message.text


async def set_message(
    key: str,
    text: str,
    updated_by: int | None = None,
) -> BotMessage:
    async with get_session() as session:
        result = await session.execute(
            select(BotMessage).where(
                BotMessage.key == key
            )
        )

        message = result.scalar_one_or_none()

        now = utc_now()

        if message is None:
            message = BotMessage(
                key=key,
                text=text,
                created_at=now,
                updated_at=now,
            )

            session.add(message)

        else:
            message.text = text
            message.updated_at = now

        await session.commit()
        await session.refresh(message)

        return message


async def reset_message(
    key: str,
) -> None:
    async with get_session() as session:
        await session.execute(
            delete(BotMessage).where(
                BotMessage.key == key
            )
        )

        await session.commit()


async def get_all_message_overrides() -> dict[str, str]:
    async with get_session() as session:
        result = await session.execute(
            select(BotMessage)
        )

        rows = result.scalars().all()

        return {
            row.key: row.text
            for row in rows
        }
