"""Leak-safe rolling summaries of a team-game table.

Input: one row per (team, game) with a kickoff timestamp and numeric stat columns.
Output: the same rows with, for every stat, values computed from the team's PRIOR games only:
  l4_<stat>   mean of the previous 4 games (any season)
  l8_<stat>   mean of the previous 8 games
  ewm_<stat>  exponentially weighted mean, half-life 6 games, across seasons
  std_<stat>  season-to-date mean (previous games this season; NaN in week 1)
  prev_<stat> previous season's full-season mean
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HALFLIFE = 6


def rolling_features(tg: pd.DataFrame, stats: list[str], team_col: str = "team", time_col: str = "kickoff",
                     season_col: str = "season") -> pd.DataFrame:
    tg = tg.sort_values([team_col, time_col]).reset_index(drop=True)
    g = tg.groupby(team_col, sort=False)
    out = {}
    for s in stats:
        shifted = g[s].shift(1)  # exclude the current game
        sg = shifted.groupby(tg[team_col], sort=False)
        out[f"l4_{s}"] = sg.transform(lambda x: x.rolling(4, min_periods=2).mean())
        out[f"l8_{s}"] = sg.transform(lambda x: x.rolling(8, min_periods=3).mean())
        out[f"ewm_{s}"] = sg.transform(lambda x: x.ewm(halflife=HALFLIFE, min_periods=2, ignore_na=True).mean())
        out[f"std_{s}"] = shifted.groupby([tg[team_col], tg[season_col]], sort=False).transform(lambda x: x.expanding(min_periods=1).mean())
        season_mean = tg.groupby([team_col, season_col])[s].mean().rename(f"prev_{s}").reset_index()
        season_mean[season_col] = season_mean[season_col] + 1
        out[f"prev_{s}"] = tg[[team_col, season_col]].merge(season_mean, on=[team_col, season_col], how="left")[f"prev_{s}"].to_numpy()
    feats = pd.DataFrame(out, index=tg.index)
    # Season-to-date is undefined in week 1; fall back to last season's mean so the column is usable.
    for s in stats:
        feats[f"std_{s}"] = feats[f"std_{s}"].fillna(feats[f"prev_{s}"])
    feats["games_played_season"] = tg.groupby([team_col, season_col], sort=False).cumcount()
    return pd.concat([tg, feats], axis=1)
