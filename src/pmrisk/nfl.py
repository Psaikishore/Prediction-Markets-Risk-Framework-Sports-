"""nflverse schedule and score data via nflreadpy."""

from __future__ import annotations

import pandas as pd

from . import DATA_RAW

SEASONS = list(range(2015, 2027))
# Kalshi uses a few abbreviations that differ from nflverse.
KALSHI_TO_NFLVERSE = {"WSH": "WAS", "JAC": "JAX", "LAR": "LA"}


def nfelo_game_id(game_id: str) -> str:
    """nfelo writes the Raiders as OAK and the Rams as LAR in every season, and the Chargers as LAC throughout;
    nflverse uses the code of the season (OAK/LV, STL/LA, SD/LAC)."""
    season, week, away, home = game_id.split("_")
    y = int(season)
    fix = {"OAK": "LV" if y >= 2020 else "OAK", "LAR": "LA" if y >= 2016 else "STL", "LAC": "LAC" if y >= 2017 else "SD"}
    return "_".join([season, week, fix.get(away, away), fix.get(home, home)])


def pull_schedules(seasons=SEASONS, cache: bool = True) -> pd.DataFrame:
    import nflreadpy as nfl

    df = nfl.load_schedules(list(seasons)).to_pandas()
    if cache:
        DATA_RAW.mkdir(parents=True, exist_ok=True)
        df.to_parquet(DATA_RAW / "nflverse_schedules.parquet", index=False)
    return df


def load_schedules() -> pd.DataFrame:
    df = pd.read_parquet(DATA_RAW / "nflverse_schedules.parquet")
    df["gameday"] = pd.to_datetime(df["gameday"])
    return df


def completed_games(df: pd.DataFrame) -> pd.DataFrame:
    """Games with a final score. `result` is home minus away; `total` is the sum."""
    out = df.dropna(subset=["home_score", "away_score"]).copy()
    out["margin"] = out["home_score"] - out["away_score"]
    out["total_pts"] = out["home_score"] + out["away_score"]
    # spread_line is the home team's expected margin (positive = home favoured).
    out["ats_error"] = out["margin"] - out["spread_line"]
    out["total_error"] = out["total_pts"] - out["total_line"]
    return out
