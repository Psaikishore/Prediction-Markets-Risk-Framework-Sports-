"""Parlays priced on the score grid.

A parlay pays $1 only if every leg settles yes. Legs on the same game are events on one joint distribution
p(h, a), so their joint probability is the mass of the grid on the intersection of their payoff regions; legs on
different games are treated as independent and their probabilities multiply. The difference between the joint
price and the product of the legs' own probabilities is the correlation premium, which is zero across games and
whatever the grid says within a game.

Tie convention: a winner contract pays 0.5 on a tie, but a parlay settles no unless every leg is yes, so a leg
"hits" only where its payoff exceeds 0.5; a tie is a miss for a winner leg.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .risk import Contract, contract_from_market
from .score_model import ScoreGrid


@dataclass(frozen=True)
class ParlayLeg:
    game_id: str
    contract: Contract
    side: str = "yes"  # "yes" or "no"

    def mask(self, grid: ScoreGrid) -> np.ndarray:
        hit = self.contract.payoff(grid) > 0.5
        return ~hit if self.side == "no" else hit


def leg_probability(leg: ParlayLeg, grid: ScoreGrid) -> float:
    return float(grid.p[leg.mask(grid)].sum())


def parlay_fair_value(legs: list[ParlayLeg], grids: dict[str, ScoreGrid]) -> float:
    """Joint probability that every leg hits: grid mass on the AND of same-game legs, product across games."""
    by_game: dict[str, list[ParlayLeg]] = defaultdict(list)
    for leg in legs:
        by_game[leg.game_id].append(leg)
    value = 1.0
    for game_id, game_legs in by_game.items():
        grid = grids[game_id]
        mask = np.logical_and.reduce([l.mask(grid) for l in game_legs])
        value *= float(grid.p[mask].sum())
    return value


def product_of_marginals(legs: list[ParlayLeg], grids: dict[str, ScoreGrid]) -> float:
    """Price under independence of every leg, including legs on the same game."""
    return float(np.prod([leg_probability(l, grids[l.game_id]) for l in legs]))


def correlation_premium(legs: list[ParlayLeg], grids: dict[str, ScoreGrid]) -> float:
    return parlay_fair_value(legs, grids) - product_of_marginals(legs, grids)


def legs_from_market(mve_selected_legs: list[dict], markets: pd.DataFrame, home_team_by_game: dict[str, str],
                     game_by_event: dict[str, str]) -> list[ParlayLeg]:
    """Kalshi `mve_selected_legs` (event_ticker, market_ticker, side) -> ParlayLegs.

    `markets` needs columns ticker, kind, floor_strike (indexed or not); unknown tickers or events raise KeyError.
    """
    mk = markets if markets.index.name == "ticker" else markets.set_index("ticker")
    legs = []
    for l in mve_selected_legs:
        ticker, event = l["market_ticker"], l["event_ticker"]
        if ticker not in mk.index:
            raise KeyError(ticker)
        if event not in game_by_event:
            raise KeyError(event)
        game_id = game_by_event[event]
        row = mk.loc[ticker]
        contract = contract_from_market(ticker, row.kind, row.floor_strike, home_team_by_game[game_id])
        legs.append(ParlayLeg(game_id, contract, l.get("side", "yes")))
    return legs
