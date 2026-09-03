from __future__ import annotations

import os
import tempfile
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from config import (
    CHART_CANDLES,
    CHART_DPI,
)
from indicators import calculate_indicators
from models import SignalCandidate


class ChartGenerator:
    def __init__(self) -> None:
        self.output_directory = os.path.join(
            tempfile.gettempdir(),
            "teyzoo_charts",
        )

        os.makedirs(
            self.output_directory,
            exist_ok=True,
        )

    def generate(
        self,
        df: pd.DataFrame,
        candidate: SignalCandidate,
    ) -> str:
        calculated = calculate_indicators(df)

        calculated = calculated.tail(
            CHART_CANDLES
        ).reset_index(drop=True)

        if calculated.empty:
            raise ValueError(
                "No candles available for chart"
            )

        figure = plt.figure(
            figsize=(14, 9),
            dpi=CHART_DPI,
        )

        grid = figure.add_gridspec(
            4,
            1,
            height_ratios=[
                4,
                1,
                1,
                1,
            ],
            hspace=0.15,
        )

        ax_price = figure.add_subplot(
            grid[0]
        )

        ax_rsi = figure.add_subplot(
            grid[1],
            sharex=ax_price,
        )

        ax_macd = figure.add_subplot(
            grid[2],
            sharex=ax_price,
        )

        ax_stoch = figure.add_subplot(
            grid[3],
            sharex=ax_price,
        )

        self._draw_candles(
            ax_price,
            calculated,
        )

        ax_price.plot(
            calculated.index,
            calculated["ema_fast"],
            label="EMA 9",
            linewidth=1.2,
        )

        ax_price.plot(
            calculated.index,
            calculated["ema_slow"],
            label="EMA 21",
            linewidth=1.2,
        )

        ax_price.plot(
            calculated.index,
            calculated["ema_trend"],
            label="EMA 50",
            linewidth=1.2,
        )

        ax_price.plot(
            calculated.index,
            calculated["bb_upper"],
            label="BB Upper",
            linewidth=0.8,
        )

        ax_price.plot(
            calculated.index,
            calculated["bb_middle"],
            label="BB Middle",
            linewidth=0.8,
        )

        ax_price.plot(
            calculated.index,
            calculated["bb_lower"],
            label="BB Lower",
            linewidth=0.8,
        )

        ax_price.axhline(
            candidate.entry_price,
            linestyle="--",
            linewidth=1.2,
            label="ENTRY",
        )

        ax_price.set_title(
            (
                f"{candidate.pair} | "
                f"{candidate.direction} | "
                f"WINRATE {candidate.winrate:.1f}% | "
                f"CONFIDENCE {candidate.confidence:.1f}%"
            )
        )

        ax_price.legend(
            loc="upper left",
            fontsize=7,
            ncol=3,
        )

        ax_price.grid(
            alpha=0.2
        )

        ax_rsi.plot(
            calculated.index,
            calculated["rsi"],
            label="RSI",
            linewidth=1.0,
        )

        ax_rsi.axhline(
            70,
            linestyle="--",
            linewidth=0.8,
        )

        ax_rsi.axhline(
            30,
            linestyle="--",
            linewidth=0.8,
        )

        ax_rsi.set_ylim(
            0,
            100,
        )

        ax_rsi.set_ylabel(
            "RSI"
        )

        ax_rsi.grid(
            alpha=0.2
        )

        ax_macd.plot(
            calculated.index,
            calculated["macd"],
            label="MACD",
            linewidth=1.0,
        )

        ax_macd.plot(
            calculated.index,
            calculated["macd_signal"],
            label="Signal",
            linewidth=1.0,
        )

        ax_macd.bar(
            calculated.index,
            calculated["macd_histogram"],
            alpha=0.35,
            label="Histogram",
        )

        ax_macd.legend(
            loc="upper left",
            fontsize=7,
        )

        ax_macd.grid(
            alpha=0.2
        )

        ax_stoch.plot(
            calculated.index,
            calculated["stochastic_k"],
            label="%K",
            linewidth=1.0,
        )

        ax_stoch.plot(
            calculated.index,
            calculated["stochastic_d"],
            label="%D",
            linewidth=1.0,
        )

        ax_stoch.axhline(
            80,
            linestyle="--",
            linewidth=0.8,
        )

        ax_stoch.axhline(
            20,
            linestyle="--",
            linewidth=0.8,
        )

        ax_stoch.set_ylim(
            0,
            100,
        )

        ax_stoch.legend(
            loc="upper left",
            fontsize=7,
        )

        ax_stoch.grid(
            alpha=0.2
        )

        ax_stoch.set_xlabel(
            "Candles"
        )

        created = datetime.utcnow().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        safe_pair = (
            candidate.pair
            .replace("/", "_")
            .replace(" ", "_")
        )

        filename = (
            f"{safe_pair}_"
            f"{candidate.direction}_"
            f"{created}.png"
        )

        path = os.path.join(
            self.output_directory,
            filename,
        )

        figure.savefig(
            path,
            bbox_inches="tight",
        )

        plt.close(
            figure
        )

        return path

    @staticmethod
    def _draw_candles(
        ax,
        df: pd.DataFrame,
    ) -> None:
        width = 0.6

        for index, row in df.iterrows():
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])

            ax.vlines(
                index,
                low_price,
                high_price,
                linewidth=0.8,
            )

            bottom = min(
                open_price,
                close_price,
            )

            height = abs(
                close_price - open_price
            )

            if height == 0:
                height = max(
                    abs(high_price - low_price)
                    * 0.01,
                    1e-10,
                )

            ax.bar(
                index,
                height,
                bottom=bottom,
                width=width,
                alpha=0.65,
            )

        ax.grid(
            alpha=0.2
        )


chart_generator = ChartGenerator()
