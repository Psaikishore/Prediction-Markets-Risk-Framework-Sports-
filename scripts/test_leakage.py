"""Leakage test for the feature table.

Pick random games, multiply every play-level statistic of THOSE games by 10 (and change their scores),
rebuild the rolling, rating and QB features, and check that the features of the perturbed games are
unchanged while the features of the teams' later games do change.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED
from pmrisk.features.build import long_schedule, load_schedule
from pmrisk.features.qb import qb_features
from pmrisk.features.ratings import elo_ratings, margin_ratings
from pmrisk.features.rolling import rolling_features
from pmrisk.features.team_game import STAT_DOC

INTERIM = DATA_PROCESSED / "features"


def team_features(ls, tg_stats, qb_stats, s):
    stats = list(STAT_DOC) + [f"def_{k}" for k in STAT_DOC]
    tg = ls.merge(tg_stats.drop(columns=["season", "week", "game_date", "home_team", "away_team"]), on=["game_id", "team"], how="left")
    tg["points_per_drive"] = tg.points_for / tg.drives
    tg["def_points_per_drive"] = tg.points_against / tg.def_drives
    stats += ["points_per_drive", "def_points_per_drive", "points_for", "points_against"]
    tg = rolling_features(tg, stats)
    tg = tg.merge(margin_ratings(ls), on=["game_id", "team"], how="left")
    qb = qb_features(qb_stats, ls[["game_id", "team", "qb_id", "kickoff"]])
    tg = tg.merge(qb.drop(columns=["qb_id"]), on=["game_id", "team"], how="left")
    feat_cols = [c for c in tg.columns if c.startswith(("l4_", "l8_", "ewm_", "std_", "prev_", "qb_")) or c in ("games_played_season",)]
    elo = elo_ratings(s)
    return tg.set_index(["game_id", "team"])[feat_cols].sort_index(), elo


def main(seasons=(2018, 2019), n_games=6, seed=0):
    """Perturb ONE game at a time so no chain through opponents can explain a change."""
    s = load_schedule()
    s = s[s.season.isin(seasons) & s.home_score.notna()].reset_index(drop=True)
    tg_stats = pd.concat([pd.read_parquet(INTERIM / f"team_game_{y}.parquet") for y in seasons])
    qb_stats = pd.concat([pd.read_parquet(INTERIM / f"qb_game_{y}.parquet") for y in seasons])
    ls = long_schedule(s)
    base, elo_base = team_features(ls, tg_stats, qb_stats, s)
    num = [c for c in tg_stats.columns if tg_stats[c].dtype.kind == "f" and c not in ("season", "week")]
    qnum = ["dropbacks", "qb_epa_db", "qb_cpoe", "qb_success"]

    cand = s[(s.season == seasons[0]) & (s.week <= 12)].sample(n_games, random_state=seed)
    ok = True
    for r in cand.itertuples():
        gid = r.game_id
        tg2, qb2, s2, ls2 = tg_stats.copy(), qb_stats.copy(), s.copy(), ls.copy()
        tg2.loc[tg2.game_id == gid, num] *= 10
        qb2.loc[qb2.game_id == gid, qnum] *= 10
        s2.loc[s2.game_id == gid, "home_score"] += 30
        ls2.loc[(ls2.game_id == gid) & (ls2.is_home == 1), "points_for"] += 30
        ls2.loc[(ls2.game_id == gid) & (ls2.is_home == 0), "points_against"] += 30
        pert, elo_pert = team_features(ls2, tg2, qb2, s2)

        rows = [(gid, r.home_team), (gid, r.away_team)]
        same = base.loc[rows].fillna(-999).eq(pert.loc[rows].fillna(-999))
        leaked = [c for c in same.columns if not same[c].all()]
        elo_same = elo_base.loc[s.game_id == gid].fillna(-999).eq(elo_pert.loc[s2.game_id == gid].fillna(-999)).all().all()
        later = ls[ls.team.isin([r.home_team, r.away_team]) & (ls.kickoff > r.kickoff)].set_index(["game_id", "team"]).index
        changed = (base.loc[later].fillna(-999) != pert.loc[later].fillna(-999)).any(axis=None)
        later_elo_changed = (elo_base.loc[s.kickoff > r.kickoff] != elo_pert.loc[s2.kickoff > r.kickoff]).any(axis=None)
        status = "PASS" if (not leaked and elo_same and changed and later_elo_changed) else "FAIL"
        ok &= status == "PASS"
        print(f"{gid}: own features unchanged={'yes' if not leaked else leaked[:5]}  own Elo unchanged={elo_same}  later games change={changed and later_elo_changed}  -> {status}")
    print(f"\nchecked {len(same.columns)} team features + Elo on {n_games} single-game perturbations:", "ALL PASS" if ok else "FAILURES")
    return ok


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
