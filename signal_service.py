from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select

from config import (
    SIGNAL_RESULT_CANCELLED,
    SIGNAL_RESULT_DRAW,
    SIGNAL_RESULT_LOSS,
    SIGNAL_RESULT_PENDING,
    SIGNAL_RESULT_WIN,
)
from database import (
    Signal,
    SignalRecipient,
    User,
    get_session,
)
from messages import render_message
from models import SignalCandidate
from utils import (
    direction_text,
    format_confidence,
    format_datetime,
    format_pair,
    format_price,
)


def _safe_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return "{}"


def _remove_file(
    path: str | None,
) -> None:
    if not path:
        return

    try:
        file_path = Path(path)

        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    except Exception:
        pass


def format_signal_message(
    signal: Signal | SignalCandidate,
    *,
    include_status: bool = False,
) -> str:
    pair = format_pair(
        getattr(signal, "pair", "—")
    )

    direction = direction_text(
        getattr(signal, "direction", "—")
    )

    expiry_minutes = int(
        getattr(
            signal,
            "expiry_minutes",
            5,
        )
        or 5
    )

    confidence = float(
        getattr(
            signal,
            "confidence",
            0,
        )
        or 0
    )

    quality = float(
        getattr(
            signal,
            "quality",
            0,
        )
        or 0
    )

    winrate = float(
        getattr(
            signal,
            "winrate",
            0,
        )
        or 0
    )

    entry_price = getattr(
        signal,
        "entry_price",
        None,
    )

    expires_at = getattr(
        signal,
        "expires_at",
        None,
    )

    confirmations = int(
        getattr(
            signal,
            "confirmations",
            0,
        )
        or 0
    )

    reasons = getattr(
        signal,
        "reasons",
        None,
    ) or []

    if isinstance(reasons, str):
        try:
            decoded = json.loads(reasons)

            if isinstance(decoded, list):
                reasons = decoded
            else:
                reasons = [reasons]

        except Exception:
            reasons = [reasons]

    reason_lines = "\n".join(
        f"• {str(reason)}"
        for reason in reasons[:8]
        if str(reason).strip()
    )

    if not reason_lines:
        reason_lines = (
            "• Сигнал подтверждён "
            "техническими индикаторами."
        )

    status = getattr(
        signal,
        "result",
        SIGNAL_RESULT_PENDING,
    )

    if include_status:
        status_map = {
            SIGNAL_RESULT_PENDING:
                "⏳ Ожидает результата",
            SIGNAL_RESULT_WIN:
                "✅ WIN",
            SIGNAL_RESULT_LOSS:
                "❌ LOSS",
            SIGNAL_RESULT_DRAW:
                "➖ DRAW",
            SIGNAL_RESULT_CANCELLED:
                "⚪ Отменён",
        }

        status_text = status_map.get(
            status,
            "⏳ Ожидает результата",
        )
    else:
        status_text = ""

    market = getattr(
        signal,
        "market",
        "regular",
    )

    market_text = (
        "OTC"
        if market == "otc"
        else "FOREX"
    )

    source = getattr(
        signal,
        "source",
        "signal_engine",
    )

    return render_message(
        "signal",
        pair=pair,
        direction=direction,
        expiry_minutes=expiry_minutes,
        confidence=format_confidence(
            confidence
        ),
        quality=format_confidence(
            quality
        ),
        winrate=f"{winrate:.2f}%",
        entry_price=format_price(
            entry_price
        ),
        close_time=format_datetime(
            expires_at
        ),
        confirmations=confirmations,
        reasons=reason_lines,
        market=market_text,
        source=source,
        status=status_text,
    )


async def save_signal(
    candidate: SignalCandidate,
) -> Signal:
    metadata = getattr(
        candidate,
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    async with get_session() as session:
        signal = Signal(
            pair=candidate.pair,
            market=getattr(
                candidate,
                "market",
                "regular",
            ),
            direction=candidate.direction,
            expiry_minutes=int(
                candidate.expiry_minutes
            ),
            confidence=float(
                candidate.confidence
            ),
            quality=float(
                candidate.quality
            ),
            winrate=float(
                candidate.winrate
            ),
            winrate_trades=int(
                metadata.get(
                    "winrate_trades",
                    getattr(
                        candidate,
                        "winrate_trades",
                        0,
                    ),
                )
            ),
            winrate_wins=int(
                metadata.get(
                    "winrate_wins",
                    getattr(
                        candidate,
                        "winrate_wins",
                        0,
                    ),
                )
            ),
            winrate_losses=int(
                metadata.get(
                    "winrate_losses",
                    getattr(
                        candidate,
                        "winrate_losses",
                        0,
                    ),
                )
            ),
            winrate_draws=int(
                metadata.get(
                    "winrate_draws",
                    getattr(
                        candidate,
                        "winrate_draws",
                        0,
                    ),
                )
            ),
            confirmations=int(
                candidate.confirmations
            ),
            entry_price=float(
                candidate.entry_price
            ),
            close_price=None,
            result=SIGNAL_RESULT_PENDING,
            source=candidate.source,
            reasons=list(
                candidate.reasons
            ),
            # ВАЖНО:
            # ORM-атрибут называется metadata_json.
            metadata_json=metadata,
            created_at=candidate.created_at,
            expires_at=candidate.expires_at,
        )

        session.add(signal)

        await session.commit()
        await session.refresh(signal)

        return signal


async def get_approved_users(
    *,
    auto_only: bool = False,
) -> list[User]:
    async with get_session() as session:
        conditions = [
            User.status == "approved",
        ]

        if auto_only:
            conditions.append(
                User.is_auto_signals_enabled.is_(True)
            )

        query = select(User).where(
            *conditions
        )

        result = await session.execute(
            query
        )

        return list(
            result.scalars().all()
        )


async def add_recipient(
    signal_id: int,
    telegram_id: int,
    message_id: int,
) -> SignalRecipient:
    async with get_session() as session:
        recipient = SignalRecipient(
            signal_id=signal_id,
            telegram_id=telegram_id,
            message_id=message_id,
        )

        session.add(recipient)

        await session.commit()
        await session.refresh(recipient)

        return recipient


async def send_signal_to_user(
    bot: Bot,
    signal: Signal | SignalCandidate,
    telegram_id: int,
    *,
    chart_path: str | None = None,
) -> bool:
    text = format_signal_message(signal)

    sent_message = None

    try:
        if (
            chart_path
            and os.path.exists(chart_path)
        ):
            sent_message = await bot.send_photo(
                chat_id=telegram_id,
                photo=FSInputFile(chart_path),
                caption=text,
            )
        else:
            sent_message = await bot.send_message(
                chat_id=telegram_id,
                text=text,
            )

        if isinstance(signal, Signal):
            await add_recipient(
                signal_id=signal.id,
                telegram_id=telegram_id,
                message_id=sent_message.message_id,
            )

        return True

    except Exception:
        return False


async def broadcast_signal(
    bot: Bot,
    signal: Signal,
    *,
    telegram_ids: Iterable[int] | None = None,
    chart_path: str | None = None,
) -> int:
    if telegram_ids is None:
        users = await get_approved_users(
            auto_only=True
        )

        telegram_ids = [
            int(user.telegram_id)
            for user in users
        ]

    sent_count = 0

    try:
        for telegram_id in telegram_ids:
            if await send_signal_to_user(
                bot=bot,
                signal=signal,
                telegram_id=int(
                    telegram_id
                ),
                chart_path=chart_path,
            ):
                sent_count += 1

    finally:
        _remove_file(chart_path)

    return sent_count


async def send_manual_signal(
    bot: Bot,
    signal: Signal,
    telegram_id: int,
    *,
    chart_path: str | None = None,
) -> bool:
    try:
        return await send_signal_to_user(
            bot=bot,
            signal=signal,
            telegram_id=telegram_id,
            chart_path=chart_path,
        )

    finally:
        _remove_file(chart_path)


async def get_signal_by_id(
    signal_id: int,
) -> Signal | None:
    async with get_session() as session:
        return await session.get(
            Signal,
            signal_id,
        )


async def mark_signal_result(
    signal_id: int,
    result: str,
    close_price: float | None,
) -> Signal | None:
    allowed_results = {
        SIGNAL_RESULT_PENDING,
        SIGNAL_RESULT_WIN,
        SIGNAL_RESULT_LOSS,
        SIGNAL_RESULT_DRAW,
        SIGNAL_RESULT_CANCELLED,
    }

    if result not in allowed_results:
        raise ValueError(
            f"Unknown signal result: {result}"
        )

    async with get_session() as session:
        signal = await session.get(
            Signal,
            signal_id,
        )

        if signal is None:
            return None

        signal.result = result

        signal.close_price = (
            float(close_price)
            if close_price is not None
            else None
        )

        from time_utils import utc_now

        signal.checked_at = utc_now()

        await session.commit()
        await session.refresh(signal)

        return signal


async def get_user_signal_history(
    telegram_id: int,
    limit: int = 20,
) -> list[Signal]:
    limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    async with get_session() as session:
        query = (
            select(Signal)
            .join(
                SignalRecipient,
                SignalRecipient.signal_id
                == Signal.id,
            )
            .where(
                SignalRecipient.telegram_id
                == int(telegram_id)
            )
            .order_by(
                Signal.created_at.desc()
            )
            .limit(limit)
        )

        result = await session.execute(
            query
        )

        return list(
            result.scalars().all()
        )
