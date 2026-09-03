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
        self.directory = os.path.join(
            tempfile.gettempdir(),
            "teyzoo_signal_charts",
        )

        os.makedirs(
            self.directory,
            exist_ok=True,
        )

    def generate(
        self,
        df: pd.DataFrame,
        candidate: SignalCandidate,
    ) -> str:
        calculated = calculate_indicators(
            df
        ).tail(
            CHART_CANDLES
        ).reset_index(
            drop=True
        )

        if calculated.empty:
            raise ValueError(
                "No data for chart"
            )

        figure, axes = plt.subplots(
            4,
            1,
            figsize=(14, 11),
            dpi=CHART_DPI,
            sharex=True,
            gridspec_kw={
                "height_ratios": [
                    4,
                    1,
                    1,
                    1,
                ]
            },
        )

        price_ax = axes[0]
        rsi_ax = axes[1]
        macd_ax = axes[2]
        stochastic_ax = axes[3]

        self._draw_candles(
            price_ax,
            calculated,
        )

        price_ax.plot(
            calculated.index,
            calculated["ema_fast"],
            label="EMA 9",
        )

        price_ax.plot(
            calculated.index,
            calculated["ema_slow"],
            label="EMA 21",
        )

        price_ax.plot(
            calculated.index,
            calculated["ema_trend"],
            label="EMA 50",
        )

        price_ax.plot(
            calculated.index,
            calculated["bb_upper"],
            label="BB Upper",
            linewidth=0.8,
        )

        price_ax.plot(
            calculated.index,
            calculated["bb_middle"],
            label="BB Middle",
            linewidth=0.8,
        )

        price_ax.plot(
            calculated.index,
            calculated["bb_lower"],
            label="BB Lower",
            linewidth=0.8,
        )

        price_ax.axhline(
            candidate.entry_price,
            linestyle="--",
            linewidth=1.2,
            label="ENTRY",
        )

        price_ax.set_title(
            (
                f"{candidate.pair} | "
                f"{candidate.direction} | "
                f"WINRATE "
                f"{candidate.winrate:.1f}% | "
                f"CONFIDENCE "
                f"{candidate.confidence:.1f}%"
            )
        )

        price_ax.legend(
            fontsize=7,
            ncol=4,
            loc="upper left",
        )

        price_ax.grid(
            alpha=0.2
        )

        rsi_ax.plot(
            calculated.index,
            calculated["rsi"],
            label="RSI",
        )

        rsi_ax.axhline(
            70,
            linestyle="--",
        )

        rsi_ax.axhline(
            30,
            linestyle="--",
        )

        rsi_ax.set_ylim(
            0,
            100,
        )

        rsi_ax.legend(
            fontsize=7
        )

        rsi_ax.grid(
            alpha=0.2
        )

        macd_ax.plot(
            calculated.index,
            calculated["macd"],
            label="MACD",
        )

        macd_ax.plot(
            calculated.index,
            calculated["macd_signal"],
            label="Signal",
        )

        macd_ax.bar(
            calculated.index,
            calculated["macd_histogram"],
            alpha=0.35,
            label="Histogram",
        )

        macd_ax.legend(
            fontsize=7
        )

        macd_ax.grid(
            alpha=0.2
        )

        stochastic_ax.plot(
            calculated.index,
            calculated["stochastic_k"],
            label="%K",
        )

        stochastic_ax.plot(
            calculated.index,
            calculated["stochastic_d"],
            label="%D",
        )

        stochastic_ax.axhline(
            80,
            linestyle="--",
        )

        stochastic_ax.axhline(
            20,
            linestyle="--",
        )

        stochastic_ax.set_ylim(
            0,
            100,
        )

        stochastic_ax.legend(
            fontsize=7
        )

        stochastic_ax.grid(
            alpha=0.2
        )

        filename = (
            candidate.pair.replace(
                "/",
                "_",
            )
            + "_"
            + candidate.direction
            + "_"
            + datetime.utcnow().strftime(
                "%Y%m%d_%H%M%S_%f"
            )
            + ".png"
        )

        path = os.path.join(
            self.directory,
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
        axis,
        df: pd.DataFrame,
    ) -> None:
        for index, row in df.iterrows():
            open_price = float(
                row["open"]
            )

            close_price = float(
                row["close"]
            )

            high_price = float(
                row["high"]
            )

            low_price = float(
                row["low"]
            )

            axis.vlines(
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
                close_price
                - open_price
            )

            if height == 0:
                height = max(
                    (
                        high_price
                        - low_price
                    )
                    * 0.01,
                    1e-10,
                )

            axis.bar(
                index,
                height,
                bottom=bottom,
                width=0.6,
                alpha=0.65,
            )


chart_generator = ChartGenerator()
