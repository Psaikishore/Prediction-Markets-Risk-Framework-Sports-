# Data sources used in the NFL prediction literature, and what is available to us

*Compiled 2026-10-05. "Read" means the data section of the paper's full text was read; "abstract only" means the paper is paywalled and the description comes from its abstract and from how later papers cite it.*

## 1. What each paper used

### Score and margin models

| Paper | Data | Source | Fields actually used | Access |
|---|---|---|---|---|
| Harville (1980) | 1,320 games, 1971–1977 | not stated in abstract | final score difference, home/away, season | abstract only |
| Glickman & Stern (1998) | 6 seasons, 1988–1993; test set = last 110 games of 1993 | not a named provider; scores plus the Las Vegas point spread for comparison | **score difference, which team was home, week and season index. Nothing else.** | read |
| Glickman & Stern (2017), handbook chapter | illustrative seasons | n/a (methods chapter) | Core models use scores and home field only. Lists covariates worth adding: *endogenous* (season-to-date offensive and defensive passing yards, rushing yards, fumble and interception rates, player-level factors) and *exogenous* (home/away, weather, time of day, bye week). Recommends entering each stat as the **difference and the average** of the two teams, and using last season's averages early in a season. | read |
| Baker & McHale (2013) | NFL seasons with pre-game covariates | abstract does not name the provider | both teams' exact scores as the target; pre-game covariates on team form | abstract only |
| Boulier & Stekler (2003) | 1994–2000 | *New York Times* power scores (Sagarin-style) and the paper's sports editor picks; betting line | power score difference, home field, betting line | abstract only |
| Song, Boulier & Stekler (2007) | two seasons, 74 forecasters | archived expert picks and statistical systems, plus the betting line | winner picks only | abstract only |

### Ratings

| Paper / source | Data | Source | Fields |
|---|---|---|---|
| FiveThirtyEight NFL Elo | every game back to 1920 | published as `nfl_elo.csv` (site now retired; the URL redirects) | date, teams, neutral-site flag, playoff flag, scores; pre- and post-game Elo for each team; **starting quarterback name, QB value before/after, QB adjustment**; win probabilities with and without the QB adjustment |
| Yurko, Ventura & Horowitz (2019), nflWAR | play-by-play, 2009–2017 | NFL.com JSON API via their `nflscrapR` package (the direct ancestor of nflverse) | per play: possession team, down, yards to go, yard line, seconds remaining, score differential, play type, penalties, air yards, yards after catch. Outputs: expected points, win probability, EPA, WPA |

### Betting-market papers

| Paper | Data | Source | Fields |
|---|---|---|---|
| Stern (1991) | 1981, 1983, 1984 seasons | abstract only | point spread and final margin |
| Levitt (2004) | ~20,000 wagers by 285 bettors, one NFL season | a high-stakes handicapping contest at an online sportsbook (proprietary) | posted spread, **number of bets on each side**, outcomes; game traits: home/away, favourite/underdog |
| Paul & Weinbach (2011) | 2006–2007 seasons | Sportsbook.com betting percentages (proprietary) | share of dollars on each side, spread, total |
| arXiv:1211.4000 (2012) | 2,560 regular-season games, 2002–2011 | lines mostly from *The GoldSheet*; box scores scraped from the web | **opening and closing spread**, over/under, margin, 30+ box-score stats per game (PCA applied to these) |
| Lopez, Matthews & Baumer (2018) | 2006–2016, four leagues | **Sports Insights** (paid) | closing moneylines converted to probabilities (average vig 1.93%), game results |

### Machine-learning studies

| Paper | Data | Source | Features | Note |
|---|---|---|---|---|
| Stanford CS229 (2016) | ~4,000 games from 2002; trained on 2010+ | Pro Football Reference (scraped); ESPN preseason power rankings | Vegas line, previous-season rank, ESPN power rank, win streak, start time, weather, surface | Authors report an initial 75% "beat Vegas" rate that was a bug; weather, surface and day did not help; Vegas line was the most important feature |
| Patel (2023), via the 2024 review | 2016–2021 | game stats, ESPN power ranks, FiveThirtyEight Elo, historical spreads | **4-week rolling averages** of team stats, Elo, power rank | XGBoost best; 53.7% against the spread out of sample |
| Other NFL studies in the 2024 review | various | NFL play-by-play, nflfastR, NFLsavant.com, Madden player ratings, NFL Next Gen Stats / Big Data Bowl tracking | box-score totals, passer rating, turnovers | Several report 85–95% accuracy using same-game statistics, i.e. leakage |

### What the literature's data has in common

1. The serious score models (Harville, Glickman–Stern) use **only scores, dates and home field**. Their gains come from how team strength is modelled over time, not from extra data.
2. Richer inputs appear in three families: **play-by-play efficiency** (nflWAR), **quarterback identity** (FiveThirtyEight), and **betting lines** (everything else).
3. Bet-volume data (Levitt, Paul–Weinbach) is proprietary. Kalshi's public trade tape is the closest free equivalent, and we already have it.
4. No paper reviewed uses injuries, snap counts or depth charts in a score model, although Glickman & Stern name player-level factors as the obvious gap.

## 2. What is available to us (verified by loading each dataset)

All from nflverse via `nflreadpy`, free, no key.

| Dataset | Loader | Seasons | Grain | What it gives for features |
|---|---|---|---|---|
| Schedules and results | `load_schedules` | 1999–2026 | game | scores, kickoff, rest days, roof, surface, temperature, wind, stadium, coaches, referee, starting QB ids, division flag; **closing spread, total, moneylines** |
| Play-by-play | `load_pbp` | 1999–2026 | play (372 columns) | EPA, WPA, success, air yards, down/distance/field position, drive results, pre-game spread and total on every row. Source for all efficiency features |
| Team stats | `load_team_stats` | 1999–2026 | team-week (138 columns) | passing/rushing/receiving yards, turnovers, sacks, penalties, EPA totals |
| Player stats | `load_player_stats` | 1999–2026 | player-week (150 columns) | QB and skill-player production; basis for a QB rating |
| Weekly rosters | `load_rosters_weekly` | 2002–2026 | player-week | who was on the team, position, status, experience |
| Depth charts | `load_depth_charts` | 2002–2026 | player-week | starter vs backup by position |
| Injuries | `load_injuries` | 2009–2026 | player-week | report status (out, doubtful, questionable), practice status |
| Snap counts | `load_snap_counts` | 2013–2026 | player-game | share of offensive/defensive snaps (to weight injuries by importance) |
| Officials | `load_officials` | 2015–2026 | game | referee crew |
| Next Gen Stats | `load_nextgen_stats` | 2016–2026 | player-week | time to throw, completion over expected, separation, rush yards over expected |
| Pro Football Reference advanced | `load_pfr_advstats` | 2018–2026 | player-week | pressures, drops, blitzes, missed tackles |
| Participation | `load_participation` | 2016–2025 | play | personnel groupings, players on field |
| FTN charting | `load_ftn_charting` | 2022–2026 | play | play-action, motion, blitz flags |
| Draft, combine, contracts, trades | `load_draft_picks`, `load_combine`, `load_contracts`, `load_trades` | long history | player | roster-quality proxies (draft capital, cap spend) |

Also already in the repo: the Kalshi trade tape and hourly bid/ask candles for the 2026 season.

### Not available from nflverse

| Data | Used by | Where it lives | Worth getting? |
|---|---|---|---|
| Opening lines and line movement | arXiv:1211.4000 | paid odds archives; some free scrapes | Later. Closing lines are in hand and are the stronger predictor |
| Bet counts / dollar splits | Levitt; Paul & Weinbach | proprietary sportsbooks | No. Kalshi volume by side is our substitute |
| FiveThirtyEight Elo file | CS229, Patel | retired with the site | No need: Elo is a few lines of code on scores we have, and building it avoids look-ahead in someone else's ratings |
| ESPN power rankings, Madden ratings | CS229, play-call studies | scraped | Low priority; subjective and partly redundant with the line |
| Player-tracking coordinates | Big Data Bowl papers | Kaggle, a few seasons only | No; play-level, not game-level |
| Detailed weather (precipitation) | none of the score papers | weather archives | Maybe for totals; schedules already have temperature and wind |

## 3. Coverage determines the feature tiers

| Tier | Seasons | Games | Features possible |
|---|---|---|---|
| A | 1999–2026 | ~7,300 | score-based ratings (Elo, offence/defence strength), EPA and success-rate rolling averages, QB production, situational and environment, closing lines |
| B | 2009–2026 | ~4,700 | Tier A plus injury-report counts by position group |
| C | 2013–2026 | ~3,600 | Tier B plus snap-weighted injuries (share of last week's snaps unavailable) |
| D | 2016–2026 | ~2,800 | Tier C plus Next Gen Stats |

Recommendation: build Tier A first as the main table, add B and C columns that are missing before their start year (tree models handle missing values; linear models get a "not available" indicator). Tier D adds little for game-level score prediction relative to the sample it costs.

## 4. Leakage rule

Every paper reporting implausible accuracy used same-game statistics. Every feature for game *g* must be computable from information dated before *g*'s kickoff: rolling stats use prior games only, injuries use the final report before the game, and the closing line is kept as a separate feature set so models can be run with and without it.
