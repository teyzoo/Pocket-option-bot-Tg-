from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, List, Optional

import pandas as pd

from market import market
from models import SignalCandidate
from signal_engine import SignalEngine


logger = logging.getLogger(
    "signal_scanner"
)


ANALYSIS_CONCURRENCY = 4
CANDLE_OUTPUTSIZE = 500


class SignalScanner:

    def __init__(
        self,
        engine: Optional[
            SignalEngine
        ] = None,
    ) -> None:

        self.engine = (
            engine
            or SignalEngine()
        )

        self._semaphore = (
            asyncio.Semaphore(
                ANALYSIS_CONCURRENCY
            )
        )

    async def _analyze(
        self,
        pair: str,
        market_type: str,
        dataframe: pd.DataFrame,
        expiry: int,
        source: str,
    ) -> Optional[
        SignalCandidate
    ]:

        async with self._semaphore:

            try:
                return await asyncio.to_thread(
                    self.engine.analyze,
                    pair,
                    market_type,
                    dataframe,
                    expiry,
                    source,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "%s | analysis failed",
                    pair,
                )

                return None

    async def _analyze_any(
        self,
        pair: str,
        market_type: str,
        dataframe: pd.DataFrame,
        source: str,
    ) -> Optional[
        SignalCandidate
    ]:

        async with self._semaphore:

            try:
                return await asyncio.to_thread(
                    self.engine.analyze_any_time,
                    pair,
                    market_type,
                    dataframe,
                    source,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "%s | any-time analysis failed",
                    pair,
                )

                return None

    @staticmethod
    def _best(
        candidates: Iterable[
            Optional[SignalCandidate]
        ],
    ) -> Optional[SignalCandidate]:

        valid = [
            item
            for item in candidates
            if item is not None
        ]

        if not valid:
            return None

        valid.sort(
            key=lambda item: (
                float(item.quality),
                float(item.winrate),
                float(item.confidence),
                int(item.confirmations),
                int(item.winrate_trades),
            ),
            reverse=True,
        )

        return valid[0]

    async def _load_data(
        self,
        pairs: List[str],
    ) -> Dict[
        str,
        pd.DataFrame,
    ]:

        logger.info(
            "Loading market data for %s pairs",
            len(pairs),
        )

        data = await market.get_candles_many(
            pairs,
            interval="1min",
            outputsize=CANDLE_OUTPUTSIZE,
            force_refresh=True,
        )

        logger.info(
            "Market data loaded: %s/%s",
            len(data),
            len(pairs),
        )

        return data

    async def scan(
        self,
        pairs: Iterable[str],
        market_type: str = "regular",
        expiry_minutes: Optional[int] = None,
        source: str = "manual",
    ) -> Optional[SignalCandidate]:

        pair_list = list(
            dict.fromkeys(
                str(pair).upper()
                for pair in pairs
            )
        )

        if not pair_list:
            return None

        logger.info(
            "Starting scan: market=%s pairs=%s "
            "expiry=%s source=%s",
            market_type,
            len(pair_list),
            expiry_minutes or "any",
            source,
        )

        data = await self._load_data(
            pair_list
        )

        if not data:
            logger.warning(
                "No market data available"
            )
            return None

        tasks = []

        for pair in pair_list:

            dataframe = data.get(pair)

            if dataframe is None:
                continue

            if expiry_minutes is None:

                tasks.append(
                    self._analyze_any(
                        pair,
                        market_type,
                        dataframe,
                        source,
                    )
                )

            else:

                tasks.append(
                    self._analyze(
                        pair,
                        market_type,
                        dataframe,
                        int(expiry_minutes),
                        source,
                    )
                )

        if not tasks:
            return None

        results = await asyncio.gather(
            *tasks
        )

        candidate = self._best(
            results
        )

        if candidate is None:

            logger.info(
                "ANY scan produced no candidate: "
                "market=%s pairs=%s",
                market_type,
                len(pair_list),
            )

            return None

        logger.info(
            "BEST SIGNAL: %s | %s | %sm | "
            "quality=%.2f | winrate=%.2f",
            candidate.pair,
            candidate.direction,
            candidate.expiry_minutes,
            candidate.quality,
            candidate.winrate,
        )

        return candidate
