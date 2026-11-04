"""Pre-game team ratings computed from results only (no look-ahead).

Elo follows the FiveThirtyEight recipe: K = 20, home-field 48 Elo points (~1.9 points of spread),
margin-of-victory multiplier ln(|margin|+1) * 2.2 / (0.001*|elo_diff| + 2.2), and one-third
regression to 1505 between seasons. Elo difference / 25 is the implied spread.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import franchise

K, HFA, INIT, MEAN, REGRESS = 20.0, 48.0, 1500.0, 1505.0, 1 / 3


def elo_ratings(games: pd.DataFrame) -> pd.DataFrame:
    """games: one row per game sorted by kickoff with home_team, away_team, home_score, away_score,
    season, location. Returns pre-game Elo for both teams and derived fields, indexed like games."""
    g = games.sort_values("kickoff")
    elo: dict[str, float] = {}
    last_season: dict[str, int] = {}
    rows = []
    for r in g.itertuples():
        h, a = franchise(r.home_team), franchise(r.away_team)
        for t in (h, a):
            elo.setdefault(t, INIT)
            if last_season.get(t) is not None and r.season > last_season[t]:
                elo[t] = elo[t] + REGRESS * (MEAN - elo[t])
            last_season[t] = r.season
        hfa = 0.0 if getattr(r, "location", "Home") == "Neutral" else HFA
        eh, ea = elo[h], elo[a]
        diff = eh + hfa - ea
        p_home = 1 / (1 + 10 ** (-diff / 400))
        rows.append((r.Index, eh, ea, diff, p_home, diff / 25))
        if pd.notna(r.home_score) and pd.notna(r.away_score):
            margin = r.home_score - r.away_score
            result = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
            winner_diff = diff if margin >= 0 else -diff
            mult = math.log(abs(margin) + 1) * 2.2 / (0.001 * winner_diff + 2.2)
            shift = K * mult * (result - p_home)
            elo[h], elo[a] = eh + shift, ea - shift
    out = pd.DataFrame(rows, columns=["idx", "home_elo", "away_elo", "elo_diff", "elo_p_home", "elo_spread"]).set_index("idx")
    return out.reindex(games.index)


def margin_ratings(tg: pd.DataFrame) -> pd.DataFrame:
    """Opponent-adjusted scoring margin per team-game, from the team-game long table.

    adj_margin = margin + opponent's prior EWM margin (so beating a strong team counts for more).
    Returned columns are pre-game (shifted) EWM means of margin and adjusted margin.
    """
    tg = tg.sort_values(["team", "kickoff"]).copy()
    tg["margin"] = tg.points_for - tg.points_against
    ewm_margin = tg.groupby("team").margin.transform(lambda x: x.shift(1).ewm(halflife=6, min_periods=2).mean())
    tg["ewm_margin"] = ewm_margin
    opp = tg[["game_id", "team", "ewm_margin"]].rename(columns={"team": "opponent", "ewm_margin": "opp_ewm_margin"})
    tg = tg.merge(opp, on=["game_id", "opponent"], how="left")
    tg["adj_margin"] = tg.margin + tg.opp_ewm_margin.fillna(0)
    tg = tg.sort_values(["team", "kickoff"])
    tg["ewm_adj_margin"] = tg.groupby("team").adj_margin.transform(lambda x: x.shift(1).ewm(halflife=6, min_periods=2).mean())
    return tg[["game_id", "team", "ewm_margin", "ewm_adj_margin"]]
