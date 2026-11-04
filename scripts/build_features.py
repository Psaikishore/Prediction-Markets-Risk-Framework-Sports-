"""Build the pre-game feature table for all NFL games 1999-2026 and write it with a data dictionary."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, REPORTS, ROOT
from pmrisk.features.build import FEATURE_GROUPS, build
from pmrisk.features.injuries import GROUPS
from pmrisk.features.team_game import STAT_DOC

OUT = DATA_PROCESSED / "features"


def describe(col: str) -> str:
    side = ""
    base = col
    for p in ("home_", "away_", "diff_"):
        if col.startswith(p):
            side = {"home_": "home team: ", "away_": "away team: ", "diff_": "home minus away: "}[p]
            base = col[len(p):]
            break
    win = ""
    for p, d in (("l4_", "mean of previous 4 games, "), ("l8_", "mean of previous 8 games, "), ("ewm_", "EWM (half-life 6 games), "),
                 ("std_", "season-to-date mean (prev season in week 1), "), ("prev_", "previous season mean, ")):
        if base.startswith(p):
            win = d; base = base[len(p):]; break
    if base.startswith("def_"):
        stat = STAT_DOC.get(base[4:], base[4:]); return f"{side}{win}defence allowed: {stat}"
    if base in STAT_DOC:
        return f"{side}{win}offence: {STAT_DOC[base]}"
    special = {
        "points_per_drive": "points scored per offensive drive", "def_points_per_drive": "points allowed per defensive drive",
        "points_for": "points scored", "points_against": "points allowed",
        "margin": "scoring margin", "adj_margin": "margin plus opponent's prior EWM margin (opponent-adjusted)",
        "qb_ewm_epa_db": "scheduled starting QB: EWM (half-life 8 games) of EPA per dropback before this game",
        "qb_ewm_cpoe": "starting QB: EWM of completion % over expected (2006+)", "qb_ewm_success": "starting QB: EWM success rate per dropback",
        "qb_ewm_sack_rate": "starting QB: EWM sack rate per dropback", "qb_ewm_int_rate": "starting QB: EWM interception rate per dropback",
        "qb_career_dropbacks": "starting QB: dropbacks in all prior games", "qb_career_games": "starting QB: prior games with a dropback",
        "qb_changed": "1 if the starter differs from the team's previous game", "qb_starts_with_team": "starter's prior starts for this team",
        "games_played_season": "team's games already played this season",
        "elo": "pre-game Elo rating (K=20, MOV multiplier, 1/3 season regression)", "elo_diff": "home Elo + 48 home-field minus away Elo",
        "elo_p_home": "Elo win probability for home team", "elo_spread": "Elo-implied home margin (elo_diff / 25)",
        "inj_out_total": "players listed Out or Doubtful on the final injury report (2009+)", "inj_quest_total": "players listed Questionable (2009+)",
        "inj_snapwt_off": "sum of previous-game offensive snap share of players now Out/Doubtful (2013+)",
        "inj_snapwt_def": "sum of previous-game defensive snap share of players now Out/Doubtful (2013+)",
        "neutral_site": "1 if played at a neutral site", "dome": "1 if roof is dome or closed", "grass": "1 if natural grass",
        "temp_filled": "temperature F (70 for domes)", "wind_filled": "wind mph (0 for domes)", "primetime": "1 if kickoff 19:00 ET or later",
        "weekday_num": "0=Monday ... 6=Sunday", "short_week_home": "home team on 5 or fewer days rest", "short_week_away": "away team on 5 or fewer days rest",
        "bye_home": "home team off a bye (13+ days rest)", "bye_away": "away team off a bye", "rest_diff": "home rest days minus away rest days",
        "playoff": "1 if not a regular-season game", "market_p_home": "de-vigged closing moneyline P(home win)", "market_overround": "sum of implied probabilities minus 1",
        "div_game": "1 if divisional game", "home_rest": "home team days since last game", "away_rest": "away team days since last game",
    }
    if base.startswith("ewm_") and base[4:] in special:
        return f"{side}EWM (half-life 6) of {special[base[4:]]}, pre-game"
    for grp in GROUPS:
        if base == f"inj_out_{grp}": return f"{side}players Out/Doubtful at {grp} (2009+)"
        if base == f"inj_quest_{grp}": return f"{side}players Questionable at {grp} (2009+)"
    if base in special:
        return f"{side}{win}{special[base]}"
    return f"{side}{win}{base}"


def main():
    g = build()
    OUT.mkdir(parents=True, exist_ok=True)
    g.to_parquet(OUT / "games_features.parquet", index=False)
    g.to_csv(ROOT / "data" / "csv" / "games_features.csv", index=False) if (ROOT / "data" / "csv").exists() else None

    # Data dictionary
    rows = []
    for c in g.columns:
        grp = next((k for k, v in FEATURE_GROUPS.items() if c in v), None)
        if grp is None:
            grp = "situational" if not c.startswith(("home_", "away_", "diff_")) else ("injuries" if "inj_" in c else "quarterback" if "qb_" in c else "ratings" if "elo" in c or "margin" in c or "points_" in c else "team form")
        nn = g[c].notna().mean()
        first = g.loc[g[c].notna(), "season"].min() if nn > 0 else None
        rows.append({"column": c, "group": grp, "dtype": str(g[c].dtype), "non_null": f"{nn:.0%}", "first_season": first, "description": describe(c)})
    dd = pd.DataFrame(rows)
    dd.to_csv(OUT / "feature_dictionary.csv", index=False)
    md = ["# Feature dictionary: `data/processed/features/games_features.parquet`", "",
          f"{len(g):,} games, {g.season.min()}–{g.season.max()}, {len(g.columns)} columns. One row per game, home-team orientation. "
          "All `home_*`, `away_*`, `diff_*` features are computed from information available before kickoff.", ""]
    for grp in ["identifiers", "targets", "market", "situational", "ratings", "team form", "quarterback", "injuries"]:
        d = dd[dd.group == grp]
        if not len(d): continue
        md += [f"## {grp} ({len(d)} columns)", "", "| column | non-null | from | description |", "|---|---|---|---|"]
        md += [f"| `{r.column}` | {r.non_null} | {int(r.first_season) if pd.notna(r.first_season) else ''} | {r.description} |" for r in d.itertuples()]
        md.append("")
    (REPORTS / "feature_dictionary.md").write_text("\n".join(md))
    print(f"\n{len(g):,} games x {len(g.columns)} columns -> {OUT / 'games_features.parquet'}")
    print(dd.group.value_counts().to_string())


if __name__ == "__main__":
    main()
