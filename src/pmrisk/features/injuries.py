"""Injury-report features (2009+), optionally snap-weighted (2013+).

For each (season, week, team): counts of players listed Out/Doubtful and Questionable by position
group, and the summed share of the team's offensive / defensive snaps in its previous game taken by
players now listed Out or Doubtful.
"""

from __future__ import annotations

import pandas as pd

POS_GROUP = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "T": "OL", "G": "OL", "C": "OL",
             "DE": "DL", "DT": "DL", "NT": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
             "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB", "DB": "DB", "K": "ST", "P": "ST", "LS": "ST"}
GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "ST"]


def injury_features(inj: pd.DataFrame, snaps: pd.DataFrame | None, schedule_tg: pd.DataFrame) -> pd.DataFrame:
    """inj: nflreadpy injuries; snaps: nflreadpy snap_counts (may be None); schedule_tg: team-game rows with
    season, week, team, game_id, kickoff. Returns one row per (game_id, team)."""
    inj = inj.copy()
    inj["grp"] = inj.position.str.strip().map(POS_GROUP).fillna("OTHER")
    inj["out"] = inj.report_status.isin(["Out", "Doubtful"]).astype(int)
    inj["quest"] = (inj.report_status == "Questionable").astype(int)
    key = ["season", "week", "team"]
    counts = inj.groupby(key + ["grp"])[["out", "quest"]].sum().unstack("grp").fillna(0)
    counts.columns = [f"inj_{a}_{b}" for a, b in counts.columns]
    for g in GROUPS:
        for a in ("out", "quest"):
            if f"inj_{a}_{g}" not in counts.columns:
                counts[f"inj_{a}_{g}"] = 0.0
    counts["inj_out_total"] = counts[[c for c in counts if c.startswith("inj_out_")]].sum(axis=1)
    counts["inj_quest_total"] = counts[[c for c in counts if c.startswith("inj_quest_")]].sum(axis=1)
    counts = counts.drop(columns=[c for c in counts.columns if c.endswith("_OTHER")]).reset_index()

    out = schedule_tg[["game_id", "season", "week", "team"]].merge(counts, on=key, how="left")

    if snaps is not None and len(snaps):
        # Previous-game snap share for players now Out/Doubtful, matched by name within team-season.
        sn = snaps[["season", "week", "team", "player", "offense_pct", "defense_pct", "game_id"]].copy()
        outs = inj[inj.out == 1][["season", "week", "team", "full_name"]].rename(columns={"full_name": "player"})
        # last game before this week for the same player/team/season
        sn = sn.sort_values(["season", "team", "player", "week"])
        merged = outs.merge(sn, on=["season", "team", "player"], how="inner", suffixes=("", "_snap"))
        merged = merged[merged.week_snap < merged.week]
        last = merged.sort_values("week_snap").groupby(["season", "week", "team", "player"]).tail(1)
        wt = last.groupby(key)[["offense_pct", "defense_pct"]].sum().rename(
            columns={"offense_pct": "inj_snapwt_off", "defense_pct": "inj_snapwt_def"}).reset_index()
        out = out.merge(wt, on=key, how="left")
        has_snaps = out.season >= int(snaps.season.min())
        for c in ("inj_snapwt_off", "inj_snapwt_def"):
            out.loc[has_snaps, c] = out.loc[has_snaps, c].fillna(0.0)
    has_inj = out.season >= int(inj.season.min())
    inj_cols = [c for c in out.columns if c.startswith("inj_") and not c.startswith("inj_snapwt")]
    out.loc[has_inj, inj_cols] = out.loc[has_inj, inj_cols].fillna(0.0)
    return out.drop(columns=["season", "week"])
