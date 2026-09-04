from __future__ import annotations

from dataclasses import dataclass

from config import (
    MARKET_OTC,
    MARKET_REGULAR,
    NORMAL_PAIRS,
    OTC_PAIRS,
)
from models import PairInfo


@dataclass(frozen=True, slots=True)
class MarketDefinition:
    name: str
    pairs: tuple[str, ...]


REGULAR_MARKET = MarketDefinition(
    name=MARKET_REGULAR,
    pairs=tuple(NORMAL_PAIRS),
)

OTC_MARKET = MarketDefinition(
    name=MARKET_OTC,
    pairs=tuple(OTC_PAIRS),
)


class PairSelector:
    def available_pairs(
        self,
        market: str = MARKET_REGULAR,
    ) -> tuple[str, ...]:
        market = str(market).strip().lower()

        if market == MARKET_OTC:
            return OTC_MARKET.pairs

        return REGULAR_MARKET.pairs

    def pair_infos(
        self,
        market: str = MARKET_REGULAR,
    ) -> tuple[PairInfo, ...]:
        return tuple(
            PairInfo(
                symbol=pair,
                market=market,
                enabled=True,
            )
            for pair in self.available_pairs(market)
        )

    def is_allowed(
        self,
        pair: str,
        market: str = MARKET_REGULAR,
    ) -> bool:
        normalized = pair.strip().upper()

        return normalized in {
            item.upper()
            for item in self.available_pairs(market)
        }

    def market_available(
        self,
        market: str,
    ) -> bool:
        return bool(
            self.available_pairs(market)
        )

    def markets(self) -> tuple[str, ...]:
        return (
            MARKET_REGULAR,
            MARKET_OTC,
        )

    def best_candidates(
        self,
        market: str = MARKET_REGULAR,
    ) -> tuple[str, ...]:
        return self.available_pairs(market)


pair_selector = PairSelector()
