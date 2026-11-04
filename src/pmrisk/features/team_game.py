"""One row per (game, team) of offensive and defensive efficiency from play-by-play."""

from __future__ import annotations

import pandas as pd
import polars as pl

PBP_COLS = [
    "game_id", "season", "week", "game_date", "home_team", "away_team", "posteam", "defteam",
    "play_type", "pass", "rush", "qb_dropback", "down", "ydstogo", "yardline_100", "yards_gained",
    "epa", "qb_epa", "success", "cpoe", "pass_oe", "air_yards", "interception", "fumble_lost", "sack",
    "third_down_converted", "third_down_failed", "touchdown", "fixed_drive", "fixed_drive_result",
    "score_differential", "qtr", "passer_player_id", "complete_pass", "pass_attempt",
    "penalty", "penalty_team", "penalty_yards",
]

# Base per-game statistics and their meaning (offence; defence is the same from the defteam side).
STAT_DOC = {
    "plays": "scrimmage plays (pass or rush, EPA defined)",
    "epa_play": "EPA per scrimmage play",
    "pass_epa_play": "EPA per dropback",
    "rush_epa_play": "EPA per rush",
    "success_rate": "share of plays with positive EPA",
    "pass_success": "success rate on dropbacks",
    "rush_success": "success rate on rushes",
    "pass_rate": "share of plays that are dropbacks",
    "early_down_pass_rate": "dropback share on 1st/2nd down",
    "pass_oe": "pass rate over expected (mean of pass_oe, 2006+)",
    "explosive_rate": "share of plays gaining 20+ (pass) or 10+ (rush) yards",
    "yards_play": "yards per scrimmage play",
    "cpoe": "completion percentage over expected (2006+)",
    "adot": "average depth of target, air yards per attempt (2006+)",
    "turnovers": "interceptions + lost fumbles",
    "sacks": "sacks taken",
    "third_down_conv": "third-down conversion rate",
    "drives": "offensive drives",
    "neutral_epa_play": "EPA per play while score within 8 points, quarters 1-3",
    "penalty_yards": "penalty yards committed",
}


def load_pbp(season: int) -> pl.DataFrame:
    import nflreadpy as nfl

    df = nfl.load_pbp([season])
    cols = [c for c in PBP_COLS if c in df.columns]
    return df.select(cols)


def _side_stats(p: pl.DataFrame, team_col: str) -> pl.DataFrame:
    """Aggregate scrimmage plays by (game_id, team_col)."""
    is_pass = pl.col("pass") == 1
    is_rush = pl.col("rush") == 1
    explosive = (is_pass & (pl.col("yards_gained") >= 20)) | (is_rush & (pl.col("yards_gained") >= 10))
    neutral = (pl.col("score_differential").abs() <= 8) & (pl.col("qtr") <= 3)
    third = pl.col("third_down_converted") + pl.col("third_down_failed")
    return p.group_by(["game_id", team_col]).agg([
        pl.len().alias("plays"),
        pl.col("epa").mean().alias("epa_play"),
        pl.col("epa").filter(is_pass).mean().alias("pass_epa_play"),
        pl.col("epa").filter(is_rush).mean().alias("rush_epa_play"),
        pl.col("success").mean().alias("success_rate"),
        pl.col("success").filter(is_pass).mean().alias("pass_success"),
        pl.col("success").filter(is_rush).mean().alias("rush_success"),
        is_pass.mean().alias("pass_rate"),
        is_pass.filter(pl.col("down") <= 2).mean().alias("early_down_pass_rate"),
        pl.col("pass_oe").mean().alias("pass_oe"),
        explosive.mean().alias("explosive_rate"),
        pl.col("yards_gained").mean().alias("yards_play"),
        pl.col("cpoe").mean().alias("cpoe"),
        pl.col("air_yards").filter(pl.col("pass_attempt") == 1).mean().alias("adot"),
        (pl.col("interception").sum() + pl.col("fumble_lost").sum()).alias("turnovers"),
        pl.col("sack").sum().alias("sacks"),
        (pl.col("third_down_converted").sum() / pl.when(third.sum() > 0).then(third.sum()).otherwise(None)).alias("third_down_conv"),
        pl.col("fixed_drive").n_unique().alias("drives"),
        pl.col("epa").filter(neutral).mean().alias("neutral_epa_play"),
        pl.col("penalty_yards").filter(pl.col("penalty_team") == pl.col(team_col)).sum().alias("penalty_yards"),
    ]).rename({team_col: "team"})


def team_game_stats(pbp: pl.DataFrame) -> pd.DataFrame:
    p = pbp.filter(((pl.col("pass") == 1) | (pl.col("rush") == 1)) & pl.col("epa").is_not_null() & pl.col("posteam").is_not_null())
    # Penalty yards need the penalty on any play; compute on the scrimmage subset for simplicity.
    off = _side_stats(p, "posteam")
    de = _side_stats(p, "defteam").rename({c: f"def_{c}" for c in STAT_DOC})
    meta = pbp.group_by("game_id").agg([pl.col("season").first(), pl.col("week").first(), pl.col("game_date").first(),
                                        pl.col("home_team").first(), pl.col("away_team").first()])
    out = off.join(de, on=["game_id", "team"], how="full", coalesce=True).join(meta, on="game_id", how="left")
    return out.to_pandas()
