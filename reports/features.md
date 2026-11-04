# Pre-game feature table for NFL games, 1999–2026

*Built 2026-10-07 with `scripts/build_features.py`. Output: `data/processed/features/games_features.parquet` (also `data/csv/games_features.csv`), 7,548 games × 805 columns, one row per game in home-team orientation. Column-level definitions: [`feature_dictionary.md`](feature_dictionary.md).*

## What is in it

| group | columns | source | from |
|---|---|---|---|
| identifiers | 20 | nflverse schedules | 1999 |
| targets | 5 | schedules: `home_score`, `away_score`, `margin`, `total_pts`, `home_win` | 1999 |
| market | 10 | schedules: closing spread, total, moneylines and odds; de-vigged `market_p_home` | spread/total 1999, moneylines 2007 |
| situational | 31 | schedules: rest, bye, short week, primetime, weekday, dome, grass, temperature and wind (filled for domes), neutral site, divisional, playoff | 1999 |
| ratings | 68 | computed from results: Elo (pre-game, K=20, margin multiplier, 1/3 season regression; `elo_diff`, `elo_p_home`, `elo_spread`), EWM scoring margin, opponent-adjusted margin, EWM points for/against | 1999 |
| team form | 604 | play-by-play aggregated to team-game, then rolled: 20 offensive and 20 defensive efficiency stats (EPA/play, pass and rush EPA, success rates, pass rate, explosive rate, yards/play, CPOE, aDOT, turnovers, sacks, third-down rate, drives, points per drive, neutral-script EPA, penalty yards) × 5 windows (last 4, last 8, EWM half-life 6, season-to-date, previous season) × home/away/diff | 1999; CPOE, aDOT and pass-rate-over-expected 2006 |
| quarterback | 23 | play-by-play passer rows for the scheduled starter: EWM EPA/dropback, CPOE, success, sack and interception rates; career dropbacks and games; starter change flag; starts with team | 1999 |
| injuries | 44 | injury reports: Out/Doubtful and Questionable counts by position group (QB, RB, WR, TE, OL, DL, LB, DB, ST); snap-weighted Out/Doubtful share of previous game's offensive and defensive snaps | counts 2009, snap-weighted 2013 |

Franchise codes follow relocations (STL→LA, SD→LAC, OAK→LV) so ratings and windows are continuous. The 208 unplayed 2026 games are included with features and null targets, so the table can be used directly for forecasting the current season.

## Design choices, and why

* **Everything pre-game by construction.** Rolling stats are computed on the team's series shifted by one game; Elo is the value before the update; injuries are from the report filed before the game. `scripts/test_leakage.py` perturbs one game at a time (multiplies its play-level stats by 10 and adds 30 points to its score) and checks that its own 233 team features and pre-game Elo are unchanged while later games move. Six random 2018 games: all pass.
* **Difference-and-average encoding.** Following Glickman & Stern (2017), every rolling and rating feature is emitted as `home_*`, `away_*` and `diff_* = home − away`, so a linear model sees matchup contrasts directly.
* **Multiple windows rather than one.** Last-4 captures form, last-8 and EWM capture strength, season-to-date (falling back to previous season in week 1) matches the literature's "season-to-date averages with last-season fill". Models can pick.
* **Market columns kept separate.** Lines are stored but never used in any feature, so models can be run with and without them to measure what the features add beyond the market.
* **Missing means not-yet-available, not zero.** Pre-2006 CPOE, pre-2009 injuries and pre-2013 snap weights are null; tree models handle this natively, linear models should add an indicator or restrict seasons.

## Coverage

| | 1999 | 2000 | 2006 | 2009 | 2013 | 2016–2026 |
|---|---|---|---|---|---|---|
| team form (EWM) | 87% | 100% | 100% | 100% | 100% | 100% |
| previous-season form | 0% | 100% | 100% | 100% | 100% | 100% |
| CPOE / aDOT | – | – | 88% | 100% | 100% | 100% |
| starting-QB rating | 92% | 99% | 100% | 100% | 99% | 93–99% |
| injury counts | – | – | – | 100% | 100% | 100% |
| snap-weighted injuries | – | – | – | – | 100% | 100% |
| de-vigged moneyline | – | – | 82% | 95% | 100% | 100% |

QB rating is null when the scheduled starter has no prior dropbacks (debuts), which is informative in itself (`qb_career_dropbacks` = 0).

## Sanity checks

* Elo (results only): Brier 0.2209 on 7,340 games; on the 5,359 games with moneylines, Elo 0.2204 vs market 0.2116. Elo-implied spread vs actual margin MAE 10.54; closing spread 10.27; correlation of Elo spread with the closing spread 0.85.
* Strongest single correlates of the margin (|ρ| with `diff_*`): EWM opponent-adjusted margin 0.38, EWM margin 0.38, EWM points per drive 0.33, EWM EPA/play 0.32, EWM pass EPA/play 0.31. Nothing above 0.4, which is the right order of magnitude for pre-game information in the NFL.
* 2024 averages per team-game: 2.1 players Out/Doubtful, 2.7 Questionable; Out players account for 39% of one offensive starter's snap share and 34% of one defensive starter's.

## Baseline: walk-forward, train on seasons < t, test on t, 2010–2025

Mean absolute error of the predicted home margin and total (lower is better):

| model | margin | total |
|---|---|---|
| league average | 11.18 | 11.03 |
| **closing line** | **10.06** | **10.48** |
| Elo spread | 10.39 | – |
| ridge, features only (no market) | 10.33 | 10.64 |
| ridge, features + closing line | 10.26 | 10.53 |
| gradient boosting, features only | 10.59 | 10.83 |
| gradient boosting, features + line | 10.37 | 10.64 |

Per season, ridge without market data beat the closing line on margin in 0 of 16 seasons and on total in 3 of 16; with the line as a feature, 0 of 16 and 5 of 16 (`data/processed/baseline_walkforward.csv`).

Reading: the table carries real signal (a quarter-point better than Elo, a point better than league average), ridge beats boosting at this sample size, and no model beats the closing line on average, which is exactly where Harville (1980) and Glickman & Stern (1998) landed. Adding the line to the features does not beat the line either. Point accuracy is capped near the market; the project's room to add value is in the full distribution (dispersion, key numbers, both scores jointly), as argued in `eda.md` §3.

## Known gaps and next additions

1. **Travel distance / time zones**: nflverse has no stadium coordinates; needs a small lookup table.
2. **Offence–defence ratings à la Glickman & Stern**: Elo is a single strength; a two-sided state-space rating would feed a two-score model directly.
3. **Coach and referee tenure/tendencies**: identifiers are present, features are not.
4. **Depth-chart-based QB detection for unplayed games**: the schedule's starter id is null for future weeks; a projected starter from the depth chart would fill `qb_*` for forecasting.
5. **Weather**: temperature and wind are present; precipitation is not.
