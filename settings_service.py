from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from database import (
    BotSetting,
    get_session,
)


async def get_setting(
    key: str,
    default: str | None = None,
) -> str | None:
    async with get_session() as session:
        result = await session.execute(
            select(BotSetting).where(
                BotSetting.key == key
            )
        )

        item = result.scalar_one_or_none()

        if item:
            return item.value

    return default


async def set_setting(
    key: str,
    value: str,
) -> None:
    async with get_session() as session:
        result = await session.execute(
            select(BotSetting).where(
                BotSetting.key == key
            )
        )

        item = result.scalar_one_or_none()

        if item is None:
            item = BotSetting(
                key=key,
                value=value,
                updated_at=datetime.utcnow(),
            )

            session.add(item)

        else:
            item.value = value
            item.updated_at = datetime.utcnow()

        await session.commit()


async def get_bool_setting(
    key: str,
    default: bool,
) -> bool:
    value = await get_setting(
        key,
        str(default),
    )

    if value is None:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def get_int_setting(
    key: str,
    default: int,
) -> int:
    value = await get_setting(
        key,
        str(default),
    )

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default
