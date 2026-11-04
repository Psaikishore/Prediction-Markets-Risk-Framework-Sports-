"""Starting-quarterback features from play-by-play passer rows.

For the starter named in the schedule: pre-game EWM of EPA per dropback and CPOE over his
previous games, career dropbacks before this game, and whether the team changed starter.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl


def qb_game_stats(pbp: pl.DataFrame) -> pd.DataFrame:
    p = pbp.filter((pl.col("qb_dropback") == 1) & pl.col("passer_player_id").is_not_null() & pl.col("epa").is_not_null())
    out = p.group_by(["game_id", "posteam", "passer_player_id"]).agg([
        pl.len().alias("dropbacks"),
        pl.col("qb_epa").mean().alias("qb_epa_db"),
        pl.col("cpoe").mean().alias("qb_cpoe"),
        pl.col("success").mean().alias("qb_success"),
        pl.col("sack").mean().alias("qb_sack_rate"),
        pl.col("interception").mean().alias("qb_int_rate"),
    ]).rename({"posteam": "team", "passer_player_id": "qb_id"})
    return out.to_pandas()


def qb_features(qb_games: pd.DataFrame, starters: pd.DataFrame) -> pd.DataFrame:
    """starters: one row per (game_id, team) with qb_id (from schedules) and kickoff.
    Returns pre-game QB features for the named starter."""
    q = qb_games.merge(starters[["game_id", "team", "kickoff"]], on=["game_id", "team"], how="inner")
    q = q.sort_values(["qb_id", "kickoff"])
    g = q.groupby("qb_id", sort=False)
    feats = pd.DataFrame(index=q.index)
    for s in ["qb_epa_db", "qb_cpoe", "qb_success", "qb_sack_rate", "qb_int_rate"]:
        feats[f"qb_ewm_{s[3:]}"] = g[s].transform(lambda x: x.shift(1).ewm(halflife=8, min_periods=1, ignore_na=True).mean())
    feats["qb_career_dropbacks"] = g.dropbacks.transform(lambda x: x.shift(1).fillna(0).cumsum())
    feats["qb_career_games"] = g.cumcount()
    q = pd.concat([q[["game_id", "team", "qb_id"]], feats], axis=1)
    # Attach to the scheduled starter; a starter with no prior dropbacks gets NaN rating and 0 experience.
    st = starters.merge(q, on=["game_id", "team", "qb_id"], how="left")
    # If the starter did not record dropbacks in this game (rare), still fill his history from prior games.
    hist = qb_games.merge(starters[["game_id", "team", "kickoff"]], on=["game_id", "team"]).sort_values("kickoff")
    st = st.sort_values(["team", "kickoff"])
    st["qb_changed"] = (st.groupby("team").qb_id.shift(1) != st.qb_id).astype(float)
    st.loc[st.groupby("team").qb_id.shift(1).isna(), "qb_changed"] = np.nan
    st["qb_starts_with_team"] = st.groupby(["team", "qb_id"]).cumcount()
    st["qb_career_dropbacks"] = st.qb_career_dropbacks.fillna(0)
    st["qb_career_games"] = st.qb_career_games.fillna(0)
    return st.drop(columns=["kickoff"])
