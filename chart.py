from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


logger = logging.getLogger(
    "chart"
)


CHART_DIR = Path("charts")
CHART_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def create_signal_chart(
    df: pd.DataFrame,
    pair: str,
    direction: str,
    expiry_minutes: int,
    entry_price: Optional[float] = None,
    output_path: Optional[str] = None,
) -> Optional[str]:

    if df is None or df.empty:
        return None

    data = df.copy()

    if "datetime" in data.columns:

        data["datetime"] = pd.to_datetime(
            data["datetime"],
            utc=True,
            errors="coerce",
        )

        data = data.dropna(
            subset=["datetime"]
        )

    if len(data) < 30:
        return None

    data = data.tail(120).reset_index(
        drop=True
    )

    if output_path is None:

        safe_pair = (
            pair.replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )

        timestamp = pd.Timestamp.utcnow().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_path = str(
            CHART_DIR
            / (
                f"{safe_pair}_"
                f"{direction}_"
                f"{expiry_minutes}m_"
                f"{timestamp}.png"
            )
        )

    try:

        fig, ax = plt.subplots(
            figsize=(13, 7),
            dpi=130,
        )

        x = range(len(data))

        ax.plot(
            x,
            data["close"],
            linewidth=2,
            label="Price",
        )

        if "ema_fast" in data.columns:

            ax.plot(
                x,
                data["ema_fast"],
                linewidth=1.2,
                label="EMA Fast",
            )

        if "ema_slow" in data.columns:

            ax.plot(
                x,
                data["ema_slow"],
                linewidth=1.2,
                label="EMA Slow",
            )

        if "bollinger_upper" in data.columns:

            ax.plot(
                x,
                data["bollinger_upper"],
                linewidth=0.9,
                linestyle="--",
                label="BB Upper",
            )

        if "bollinger_lower" in data.columns:

            ax.plot(
                x,
                data["bollinger_lower"],
                linewidth=0.9,
                linestyle="--",
                label="BB Lower",
            )

        if entry_price is None:

            entry_price = float(
                data.iloc[-1]["close"]
            )

        last_x = len(data) - 1

        ax.scatter(
            [last_x],
            [entry_price],
            s=120,
            marker="^"
            if direction.upper() == "UP"
            else "v",
            zorder=10,
            label=(
                f"Signal {direction.upper()}"
            ),
        )

        ax.axhline(
            entry_price,
            linestyle=":",
            linewidth=1,
            label=(
                f"Entry {entry_price:.5f}"
            ),
        )

        ax.set_title(
            (
                f"{pair} | "
                f"{direction.upper()} | "
                f"Expiry {expiry_minutes} min"
            )
        )

        ax.set_xlabel(
            "Candles"
        )

        ax.set_ylabel(
            "Price"
        )

        ax.grid(
            alpha=0.25
        )

        ax.legend(
            loc="best"
        )

        fig.tight_layout()

        fig.savefig(
            output_path,
            bbox_inches="tight",
        )

        plt.close(fig)

        logger.info(
            "Signal chart created: %s",
            output_path,
        )

        return output_path

    except Exception:

        logger.exception(
            "Failed to create signal chart"
        )

        try:
            plt.close("all")
        except Exception:
            pass

        return None
