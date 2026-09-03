from __future__ import annotations

from config import NORMAL_PAIRS, OTC_PAIRS
from models import PairInfo


class PairSelector:
    def __init__(self) -> None:
        self.normal_pairs = tuple(
            NORMAL_PAIRS
        )

        self.otc_pairs = tuple(
            OTC_PAIRS
        )

    @staticmethod
    def normalize(
        pair: str,
    ) -> str:
        return pair.strip().upper()

    def available_pairs(
        self,
        market: str,
    ) -> list[str]:
        market = market.lower().strip()

        if market == "regular":
            return list(
                self.normal_pairs
            )

        if market == "otc":
            return list(
                self.otc_pairs
            )

        if market == "any":
            return list(
                dict.fromkeys(
                    [
                        *self.normal_pairs,
                        *self.otc_pairs,
                    ]
                )
            )

        return []

    def pair_infos(
        self,
        market: str,
    ) -> list[PairInfo]:
        return [
            PairInfo(
                symbol=pair,
                market=market,
            )
            for pair in self.available_pairs(
                market
            )
        ]

    def is_allowed(
        self,
        pair: str,
        market: str,
    ) -> bool:
        return (
            self.normalize(pair)
            in self.available_pairs(market)
        )

    def otc_available(self) -> bool:
        return bool(self.otc_pairs)


pair_selector = PairSelector()
