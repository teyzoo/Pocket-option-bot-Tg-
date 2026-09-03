from __future__ import annotations

from sqlalchemy import func, select

from database import Signal, get_session


async def get_signal_stats() -> dict:
    async with get_session() as session:
        result = await session.execute(
            select(
                func.count(
                    Signal.id
                ),
                func.sum(
                    Signal.result == "win"
                ),
                func.sum(
                    Signal.result == "loss"
                ),
                func.sum(
                    Signal.result == "draw"
                ),
            )
        )

        total, wins, losses, draws = (
            result.one()
        )

    total = int(total or 0)
    wins = int(wins or 0)
    losses = int(losses or 0)
    draws = int(draws or 0)

    finished = (
        wins
        + losses
        + draws
    )

    winrate = (
        wins / finished * 100
        if finished
        else 0
    )

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "winrate": winrate,
    }
