"""Assemble the game-level feature table."""

from __future__ import annotations

import pandas as pd

from .. import DATA_PROCESSED, DATA_RAW
from . import franchise
from .injuries import injury_features
from .qb import qb_features, qb_game_stats
from .ratings import elo_ratings, margin_ratings
from .rolling import rolling_features
from .team_game import STAT_DOC, load_pbp, team_game_stats

SEASONS = list(range(1999, 2027))
INTERIM = DATA_PROCESSED / "features"

# Columns whose home-minus-away difference is also emitted (Glickman & Stern 2017's recommendation).
DIFF_PREFIXES = ("ewm_", "l4_", "l8_", "std_", "prev_", "qb_ewm_", "ewm_margin", "ewm_adj_margin")


def kickoff_utc(s: pd.DataFrame) -> pd.Series:
    local = pd.to_datetime(s.gameday.astype(str) + " " + s.gametime.fillna("13:00"))
    return local.dt.tz_localize("US/Eastern", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")


def load_schedule() -> pd.DataFrame:
    import nflreadpy as nfl

    s = nfl.load_schedules(SEASONS).to_pandas()
    s["gameday"] = pd.to_datetime(s.gameday)
    s["kickoff"] = kickoff_utc(s)
    for c in ("home_team", "away_team"):
        s[c] = s[c].map(franchise)
    return s.sort_values("kickoff").reset_index(drop=True)


def build_team_game(seasons=SEASONS, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-season play-by-play aggregation, cached. Returns (team_game_stats, qb_game_stats)."""
    INTERIM.mkdir(parents=True, exist_ok=True)
    tgs, qbs = [], []
    for y in seasons:
        f_tg, f_qb = INTERIM / f"team_game_{y}.parquet", INTERIM / f"qb_game_{y}.parquet"
        if f_tg.exists() and f_qb.exists() and not refresh and y < 2026:
            tgs.append(pd.read_parquet(f_tg)); qbs.append(pd.read_parquet(f_qb)); continue
        pbp = load_pbp(y)
        tg, qb = team_game_stats(pbp), qb_game_stats(pbp)
        tg["team"] = tg.team.map(franchise); qb["team"] = qb.team.map(franchise)
        tg.to_parquet(f_tg, index=False); qb.to_parquet(f_qb, index=False)
        tgs.append(tg); qbs.append(qb)
        print(f"  pbp {y}: {len(tg)} team-games")
    return pd.concat(tgs, ignore_index=True), pd.concat(qbs, ignore_index=True)


def long_schedule(s: pd.DataFrame) -> pd.DataFrame:
    """Two rows per game: one per team, with points for/against and the scheduled starter."""
    home = s[["game_id", "season", "week", "game_type", "kickoff", "home_team", "away_team", "home_score", "away_score", "home_qb_id", "home_rest"]].rename(
        columns={"home_team": "team", "away_team": "opponent", "home_score": "points_for", "away_score": "points_against", "home_qb_id": "qb_id", "home_rest": "rest"})
    home["is_home"] = 1
    away = s[["game_id", "season", "week", "game_type", "kickoff", "away_team", "home_team", "away_score", "home_score", "away_qb_id", "away_rest"]].rename(
        columns={"away_team": "team", "home_team": "opponent", "away_score": "points_for", "home_score": "points_against", "away_qb_id": "qb_id", "away_rest": "rest"})
    away["is_home"] = 0
    return pd.concat([home, away], ignore_index=True).sort_values(["team", "kickoff"]).reset_index(drop=True)


def build(refresh_pbp: bool = False) -> pd.DataFrame:
    import nflreadpy as nfl

    print("schedule"); s = load_schedule()
    print("play-by-play"); tg_stats, qb_stats = build_team_game(refresh=refresh_pbp)
    ls = long_schedule(s)

    # --- team form: rolling efficiency, pre-game ----------------------------------------------------
    stats = list(STAT_DOC) + [f"def_{k}" for k in STAT_DOC]
    tg = ls.merge(tg_stats.drop(columns=["season", "week", "game_date", "home_team", "away_team"]), on=["game_id", "team"], how="left")
    tg["points_per_drive"] = tg.points_for / tg.drives
    tg["def_points_per_drive"] = tg.points_against / tg.def_drives
    stats += ["points_per_drive", "def_points_per_drive", "points_for", "points_against"]
    print("rolling"); tg = rolling_features(tg, stats)
    tg = tg.merge(margin_ratings(ls), on=["game_id", "team"], how="left")

    # --- quarterbacks -----------------------------------------------------------------------------------
    print("quarterbacks"); qb = qb_features(qb_stats, ls[["game_id", "team", "qb_id", "kickoff"]])
    tg = tg.merge(qb.drop(columns=["qb_id"]), on=["game_id", "team"], how="left")

    # --- injuries -------------------------------------------------------------------------------------------
    print("injuries")
    inj = nfl.load_injuries([y for y in SEASONS if y >= 2009]).to_pandas(); inj["team"] = inj.team.map(franchise)
    snaps = nfl.load_snap_counts([y for y in SEASONS if y >= 2013]).to_pandas(); snaps["team"] = snaps.team.map(franchise)
    tg = tg.merge(injury_features(inj, snaps, ls), on=["game_id", "team"], how="left")

    # --- ratings ----------------------------------------------------------------------------------------------
    print("elo"); elo = elo_ratings(s)
    s = pd.concat([s, elo], axis=1)

    # --- assemble wide game table -----------------------------------------------------------------------------
    team_feat_cols = [c for c in tg.columns if c not in {"game_id", "season", "week", "game_type", "kickoff", "team", "opponent", "points_for", "points_against", "qb_id", "rest", "is_home"} and c not in stats]
    th = tg[["game_id", "team"] + team_feat_cols].rename(columns={c: f"home_{c}" for c in team_feat_cols}).rename(columns={"team": "home_team"})
    ta = tg[["game_id", "team"] + team_feat_cols].rename(columns={c: f"away_{c}" for c in team_feat_cols}).rename(columns={"team": "away_team"})
    g = s.merge(th, on=["game_id", "home_team"], how="left").merge(ta, on=["game_id", "away_team"], how="left")

    for c in team_feat_cols:
        if c.startswith(DIFF_PREFIXES) and pd.api.types.is_numeric_dtype(g[f"home_{c}"]):
            g[f"diff_{c}"] = g[f"home_{c}"] - g[f"away_{c}"]

    # --- situational ---------------------------------------------------------------------------------------------
    # Post-game schedule fields that duplicate the targets must not survive as features.
    g = g.drop(columns=[c for c in ("result", "total", "overtime") if c in g.columns])
    g["margin"] = g.home_score - g.away_score
    g["total_pts"] = g.home_score + g.away_score
    g["home_win"] = (g.margin > 0).astype(float).where(g.margin.notna())
    g["neutral_site"] = (g.location == "Neutral").astype(int)
    g["dome"] = g.roof.isin(["dome", "closed"]).astype(int)
    g["grass"] = g.surface.fillna("").str.contains("grass").astype(int)
    g["temp_filled"] = g.temp.where(g.dome == 0, 70)
    g["wind_filled"] = g.wind.where(g.dome == 0, 0)
    g["primetime"] = (pd.to_datetime(g.gametime, format="%H:%M", errors="coerce").dt.hour >= 19).astype(int)
    g["weekday_num"] = g.gameday.dt.weekday
    g["short_week_home"] = (g.home_rest <= 5).astype(int); g["short_week_away"] = (g.away_rest <= 5).astype(int)
    g["bye_home"] = (g.home_rest >= 13).astype(int); g["bye_away"] = (g.away_rest >= 13).astype(int)
    g["rest_diff"] = g.home_rest - g.away_rest
    g["playoff"] = (g.game_type != "REG").astype(int)
    # Market-implied probabilities (de-vigged) when moneylines exist.
    def implied(m):
        m = pd.to_numeric(m, errors="coerce")
        return pd.Series(((-m / (-m + 100)).where(m < 0, 100 / (m + 100))), index=m.index)
    ph, pa = implied(g.home_moneyline), implied(g.away_moneyline)
    g["market_p_home"] = ph / (ph + pa)
    g["market_overround"] = ph + pa - 1
    return g


FEATURE_GROUPS = {
    "targets": ["home_score", "away_score", "margin", "total_pts", "home_win"],
    "market": ["spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds", "market_p_home", "market_overround"],
    "identifiers": ["game_id", "season", "week", "game_type", "gameday", "gametime", "kickoff", "home_team", "away_team", "home_qb_id", "away_qb_id", "home_qb_name", "away_qb_name", "home_coach", "away_coach", "referee", "stadium", "roof", "surface", "location"],
}
