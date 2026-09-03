from __future__ import annotations

from dataclasses import dataclass

from config import NORMAL_PAIRS, OTC_PAIRS
from models import PairInfo


@dataclass(frozen=True, slots=True)
class MarketDefinition:
    key: str
    title: str
    pairs: tuple[str, ...]
    real_data_required: bool = True


class PairSelector:
    def __init__(self) -> None:
        self.markets = {
            "regular": MarketDefinition(
                key="regular",
                title="💱 Обычный рынок",
                pairs=NORMAL_PAIRS,
                real_data_required=True,
            ),
            "otc": MarketDefinition(
                key="otc",
                title="🌙 OTC",
                pairs=OTC_PAIRS,
                real_data_required=True,
            ),
        }

    def normalize(self, pair: str) -> str:
        return pair.strip().upper()

    def get_market(
        self,
        market: str,
    ) -> MarketDefinition | None:
        return self.markets.get(
            market.strip().lower()
        )

    def available_pairs(
        self,
        market: str,
    ) -> list[str]:
        definition = self.get_market(market)

        if definition is None:
            return []

        return list(definition.pairs)

    def pair_infos(
        self,
        market: str,
    ) -> list[PairInfo]:
        definition = self.get_market(market)

        if definition is None:
            return []

        return [
            PairInfo(
                symbol=pair,
                market=market,
                enabled=True,
            )
            for pair in definition.pairs
        ]

    def is_allowed(
        self,
        pair: str,
        market: str,
    ) -> bool:
        normalized = self.normalize(pair)

        return normalized in self.available_pairs(
            market
        )

    def is_otc_available(self) -> bool:
        return bool(OTC_PAIRS)

    def is_regular_available(self) -> bool:
        return bool(NORMAL_PAIRS)

    def all_regular_pairs(self) -> list[str]:
        return list(NORMAL_PAIRS)

    def all_otc_pairs(self) -> list[str]:
        return list(OTC_PAIRS)


pair_selector = PairSelector()
