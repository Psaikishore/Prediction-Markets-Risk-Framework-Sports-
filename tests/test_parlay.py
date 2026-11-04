import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk.nfl import completed_games, load_schedules
from pmrisk.parlay import ParlayLeg, correlation_premium, legs_from_market, parlay_fair_value, product_of_marginals
from pmrisk.risk import Contract
from pmrisk.score_model import empirical_grid, tilt


@pytest.fixture(scope="module")
def grid():
    hist = completed_games(load_schedules())
    prior = empirical_grid(hist[hist.season.between(2015, 2025)], smooth=0.02)
    return tilt(prior, -3.0, 44.5)[0]


def test_same_leg_twice_is_the_leg(grid):
    legs = [ParlayLeg("g", Contract("winner", "home")), ParlayLeg("g", Contract("winner", "home"))]
    assert parlay_fair_value(legs, {"g": grid}) == pytest.approx(float(grid.p[grid.margin > 0].sum()))


def test_home_and_away_win_is_impossible(grid):
    legs = [ParlayLeg("g", Contract("winner", "home")), ParlayLeg("g", Contract("winner", "away"))]
    assert parlay_fair_value(legs, {"g": grid}) == 0.0


def test_cross_game_legs_multiply(grid):
    legs = [ParlayLeg("a", Contract("winner", "home")), ParlayLeg("b", Contract("winner", "home"))]
    grids = {"a": grid, "b": grid}
    p = float(grid.p[grid.margin > 0].sum())
    assert parlay_fair_value(legs, grids) == pytest.approx(p ** 2)
    assert parlay_fair_value(legs, grids) == pytest.approx(product_of_marginals(legs, grids))
    assert correlation_premium(legs, grids) == pytest.approx(0.0)


def test_no_leg_is_complement(grid):
    yes = [ParlayLeg("g", Contract("spread", "home", 2.5), "yes")]
    no = [ParlayLeg("g", Contract("spread", "home", 2.5), "no")]
    assert parlay_fair_value(yes, {"g": grid}) + parlay_fair_value(no, {"g": grid}) == pytest.approx(1.0)


def test_same_game_joint_differs_from_product(grid):
    legs = [ParlayLeg("g", Contract("winner", "home")), ParlayLeg("g", Contract("total", "over", 44.5))]
    direct = float(grid.p[(grid.margin > 0) & (grid.total > 44.5)].sum())
    assert parlay_fair_value(legs, {"g": grid}) == pytest.approx(direct)
    assert abs(correlation_premium(legs, {"g": grid})) > 1e-4


def test_legs_from_market_builds_away_spread():
    markets = pd.DataFrame({"ticker": ["KXNFLSPREAD-26SEP28PHICHI-PHI3", "KXNFLGAME-26SEP28PHICHI-CHI"],
                            "kind": ["spread", "winner"], "floor_strike": [2.5, np.nan]})
    legs = legs_from_market(
        [{"event_ticker": "KXNFLSPREAD-26SEP28PHICHI", "market_ticker": "KXNFLSPREAD-26SEP28PHICHI-PHI3", "side": "yes"},
         {"event_ticker": "KXNFLGAME-26SEP28PHICHI", "market_ticker": "KXNFLGAME-26SEP28PHICHI-CHI", "side": "no"}],
        markets, {"2026_04_PHI_CHI": "CHI"},
        {"KXNFLSPREAD-26SEP28PHICHI": "2026_04_PHI_CHI", "KXNFLGAME-26SEP28PHICHI": "2026_04_PHI_CHI"})
    assert legs[0].contract == Contract("spread", "away", 2.5, 1.0)
    assert legs[1].contract == Contract("winner", "home", 0.0, 1.0) and legs[1].side == "no"
    with pytest.raises(KeyError):
        legs_from_market([{"event_ticker": "KXNFLGAME-26SEP28PHICHI", "market_ticker": "KXNFLGAME-X-Y", "side": "yes"}],
                         markets, {}, {"KXNFLGAME-26SEP28PHICHI": "2026_04_PHI_CHI"})
