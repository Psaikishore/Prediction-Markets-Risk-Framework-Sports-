# Feature dictionary: `data/processed/features/games_features.parquet`

7,548 games, 1999–2026, 802 columns. One row per game, home-team orientation. All `home_*`, `away_*`, `diff_*` features are computed from information available before kickoff.

## identifiers (20 columns)

| column | non-null | from | description |
|---|---|---|---|
| `game_id` | 100% | 1999 | game_id |
| `season` | 100% | 1999 | season |
| `game_type` | 100% | 1999 | game_type |
| `week` | 100% | 1999 | week |
| `gameday` | 100% | 1999 | gameday |
| `gametime` | 97% | 2000 | gametime |
| `away_team` | 100% | 1999 | away team: team |
| `home_team` | 100% | 1999 | home team: team |
| `location` | 100% | 1999 | location |
| `roof` | 100% | 1999 | roof |
| `surface` | 100% | 1999 | surface |
| `away_qb_id` | 98% | 1999 | away team: qb_id |
| `home_qb_id` | 98% | 1999 | home team: qb_id |
| `away_qb_name` | 98% | 1999 | away team: qb_name |
| `home_qb_name` | 98% | 1999 | home team: qb_name |
| `away_coach` | 100% | 1999 | away team: coach |
| `home_coach` | 100% | 1999 | home team: coach |
| `referee` | 97% | 1999 | referee |
| `stadium` | 100% | 1999 | stadium |
| `kickoff` | 100% | 1999 | kickoff |

## targets (5 columns)

| column | non-null | from | description |
|---|---|---|---|
| `away_score` | 98% | 1999 | away team: score |
| `home_score` | 98% | 1999 | home team: score |
| `margin` | 98% | 1999 | scoring margin |
| `total_pts` | 98% | 1999 | total_pts |
| `home_win` | 98% | 1999 | home team: win |

## market (10 columns)

| column | non-null | from | description |
|---|---|---|---|
| `away_moneyline` | 72% | 2006 | away team: moneyline |
| `home_moneyline` | 72% | 2006 | home team: moneyline |
| `spread_line` | 98% | 1999 | spread_line |
| `away_spread_odds` | 72% | 2006 | away team: spread_odds |
| `home_spread_odds` | 72% | 2006 | home team: spread_odds |
| `total_line` | 98% | 1999 | total_line |
| `under_odds` | 72% | 2006 | under_odds |
| `over_odds` | 72% | 2006 | over_odds |
| `market_p_home` | 72% | 2006 | de-vigged closing moneyline P(home win) |
| `market_overround` | 72% | 2006 | sum of implied probabilities minus 1 |

## situational (28 columns)

| column | non-null | from | description |
|---|---|---|---|
| `weekday` | 100% | 1999 | weekday |
| `old_game_id` | 100% | 1999 | old_game_id |
| `gsis` | 98% | 1999 | gsis |
| `nfl_detail_id` | 4% | 2021 | nfl_detail_id |
| `pfr` | 100% | 1999 | pfr |
| `pff` | 62% | 2006 | pff |
| `espn` | 100% | 1999 | espn |
| `ftn` | 26% | 2019 | ftn |
| `div_game` | 100% | 1999 | 1 if divisional game |
| `temp` | 70% | 1999 | temp |
| `wind` | 70% | 1999 | wind |
| `stadium_id` | 100% | 1999 | stadium_id |
| `elo_diff` | 100% | 1999 | home Elo + 48 home-field minus away Elo |
| `elo_p_home` | 100% | 1999 | Elo win probability for home team |
| `elo_spread` | 100% | 1999 | Elo-implied home margin (elo_diff / 25) |
| `neutral_site` | 100% | 1999 | 1 if played at a neutral site |
| `dome` | 100% | 1999 | 1 if roof is dome or closed |
| `grass` | 100% | 1999 | 1 if natural grass |
| `temp_filled` | 94% | 1999 | temperature F (70 for domes) |
| `wind_filled` | 94% | 1999 | wind mph (0 for domes) |
| `primetime` | 100% | 1999 | 1 if kickoff 19:00 ET or later |
| `weekday_num` | 100% | 1999 | 0=Monday ... 6=Sunday |
| `short_week_home` | 100% | 1999 | home team on 5 or fewer days rest |
| `short_week_away` | 100% | 1999 | away team on 5 or fewer days rest |
| `bye_home` | 100% | 1999 | home team off a bye (13+ days rest) |
| `bye_away` | 100% | 1999 | away team off a bye |
| `rest_diff` | 100% | 1999 | home rest days minus away rest days |
| `playoff` | 100% | 1999 | 1 if not a regular-season game |

## ratings (68 columns)

| column | non-null | from | description |
|---|---|---|---|
| `home_elo` | 100% | 1999 | home team: pre-game Elo rating (K=20, MOV multiplier, 1/3 season regression) |
| `away_elo` | 100% | 1999 | away team: pre-game Elo rating (K=20, MOV multiplier, 1/3 season regression) |
| `home_l4_points_per_drive` | 98% | 1999 | home team: mean of previous 4 games, points scored per offensive drive |
| `home_l8_points_per_drive` | 98% | 1999 | home team: mean of previous 8 games, points scored per offensive drive |
| `home_ewm_points_per_drive` | 100% | 1999 | home team: EWM (half-life 6 games), points scored per offensive drive |
| `home_std_points_per_drive` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), points scored per offensive drive |
| `home_prev_points_per_drive` | 96% | 2000 | home team: previous season mean, points scored per offensive drive |
| `home_l4_def_points_per_drive` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: points_per_drive |
| `home_l8_def_points_per_drive` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: points_per_drive |
| `home_ewm_def_points_per_drive` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: points_per_drive |
| `home_std_def_points_per_drive` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: points_per_drive |
| `home_prev_def_points_per_drive` | 96% | 2000 | home team: previous season mean, defence allowed: points_per_drive |
| `home_l4_points_for` | 98% | 1999 | home team: mean of previous 4 games, points scored |
| `home_l8_points_for` | 98% | 1999 | home team: mean of previous 8 games, points scored |
| `home_ewm_points_for` | 100% | 1999 | home team: EWM (half-life 6 games), points scored |
| `home_std_points_for` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), points scored |
| `home_prev_points_for` | 96% | 2000 | home team: previous season mean, points scored |
| `home_l4_points_against` | 98% | 1999 | home team: mean of previous 4 games, points allowed |
| `home_l8_points_against` | 98% | 1999 | home team: mean of previous 8 games, points allowed |
| `home_ewm_points_against` | 100% | 1999 | home team: EWM (half-life 6 games), points allowed |
| `home_std_points_against` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), points allowed |
| `home_prev_points_against` | 96% | 2000 | home team: previous season mean, points allowed |
| `home_ewm_margin` | 100% | 1999 | home team: EWM (half-life 6 games), scoring margin |
| `home_ewm_adj_margin` | 100% | 1999 | home team: EWM (half-life 6 games), margin plus opponent's prior EWM margin (opponent-adjusted) |
| `away_l4_points_per_drive` | 98% | 1999 | away team: mean of previous 4 games, points scored per offensive drive |
| `away_l8_points_per_drive` | 98% | 1999 | away team: mean of previous 8 games, points scored per offensive drive |
| `away_ewm_points_per_drive` | 100% | 1999 | away team: EWM (half-life 6 games), points scored per offensive drive |
| `away_std_points_per_drive` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), points scored per offensive drive |
| `away_prev_points_per_drive` | 96% | 2000 | away team: previous season mean, points scored per offensive drive |
| `away_l4_def_points_per_drive` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: points_per_drive |
| `away_l8_def_points_per_drive` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: points_per_drive |
| `away_ewm_def_points_per_drive` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: points_per_drive |
| `away_std_def_points_per_drive` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: points_per_drive |
| `away_prev_def_points_per_drive` | 96% | 2000 | away team: previous season mean, defence allowed: points_per_drive |
| `away_l4_points_for` | 98% | 1999 | away team: mean of previous 4 games, points scored |
| `away_l8_points_for` | 98% | 1999 | away team: mean of previous 8 games, points scored |
| `away_ewm_points_for` | 100% | 1999 | away team: EWM (half-life 6 games), points scored |
| `away_std_points_for` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), points scored |
| `away_prev_points_for` | 96% | 2000 | away team: previous season mean, points scored |
| `away_l4_points_against` | 98% | 1999 | away team: mean of previous 4 games, points allowed |
| `away_l8_points_against` | 98% | 1999 | away team: mean of previous 8 games, points allowed |
| `away_ewm_points_against` | 100% | 1999 | away team: EWM (half-life 6 games), points allowed |
| `away_std_points_against` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), points allowed |
| `away_prev_points_against` | 96% | 2000 | away team: previous season mean, points allowed |
| `away_ewm_margin` | 100% | 1999 | away team: EWM (half-life 6 games), scoring margin |
| `away_ewm_adj_margin` | 100% | 1999 | away team: EWM (half-life 6 games), margin plus opponent's prior EWM margin (opponent-adjusted) |
| `diff_l4_points_per_drive` | 98% | 1999 | home minus away: mean of previous 4 games, points scored per offensive drive |
| `diff_l8_points_per_drive` | 98% | 1999 | home minus away: mean of previous 8 games, points scored per offensive drive |
| `diff_ewm_points_per_drive` | 100% | 1999 | home minus away: EWM (half-life 6 games), points scored per offensive drive |
| `diff_std_points_per_drive` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), points scored per offensive drive |
| `diff_prev_points_per_drive` | 96% | 2000 | home minus away: previous season mean, points scored per offensive drive |
| `diff_l4_def_points_per_drive` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: points_per_drive |
| `diff_l8_def_points_per_drive` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: points_per_drive |
| `diff_ewm_def_points_per_drive` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: points_per_drive |
| `diff_std_def_points_per_drive` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: points_per_drive |
| `diff_prev_def_points_per_drive` | 96% | 2000 | home minus away: previous season mean, defence allowed: points_per_drive |
| `diff_l4_points_for` | 98% | 1999 | home minus away: mean of previous 4 games, points scored |
| `diff_l8_points_for` | 98% | 1999 | home minus away: mean of previous 8 games, points scored |
| `diff_ewm_points_for` | 100% | 1999 | home minus away: EWM (half-life 6 games), points scored |
| `diff_std_points_for` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), points scored |
| `diff_prev_points_for` | 96% | 2000 | home minus away: previous season mean, points scored |
| `diff_l4_points_against` | 98% | 1999 | home minus away: mean of previous 4 games, points allowed |
| `diff_l8_points_against` | 98% | 1999 | home minus away: mean of previous 8 games, points allowed |
| `diff_ewm_points_against` | 100% | 1999 | home minus away: EWM (half-life 6 games), points allowed |
| `diff_std_points_against` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), points allowed |
| `diff_prev_points_against` | 96% | 2000 | home minus away: previous season mean, points allowed |
| `diff_ewm_margin` | 100% | 1999 | home minus away: EWM (half-life 6 games), scoring margin |
| `diff_ewm_adj_margin` | 100% | 1999 | home minus away: EWM (half-life 6 games), margin plus opponent's prior EWM margin (opponent-adjusted) |

## team form (604 columns)

| column | non-null | from | description |
|---|---|---|---|
| `away_rest` | 100% | 1999 | away team: rest |
| `home_rest` | 100% | 1999 | home team: rest |
| `home_l4_plays` | 98% | 1999 | home team: mean of previous 4 games, offence: scrimmage plays (pass or rush, EPA defined) |
| `home_l8_plays` | 98% | 1999 | home team: mean of previous 8 games, offence: scrimmage plays (pass or rush, EPA defined) |
| `home_ewm_plays` | 100% | 1999 | home team: EWM (half-life 6 games), offence: scrimmage plays (pass or rush, EPA defined) |
| `home_std_plays` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: scrimmage plays (pass or rush, EPA defined) |
| `home_prev_plays` | 96% | 2000 | home team: previous season mean, offence: scrimmage plays (pass or rush, EPA defined) |
| `home_l4_epa_play` | 98% | 1999 | home team: mean of previous 4 games, offence: EPA per scrimmage play |
| `home_l8_epa_play` | 98% | 1999 | home team: mean of previous 8 games, offence: EPA per scrimmage play |
| `home_ewm_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), offence: EPA per scrimmage play |
| `home_std_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: EPA per scrimmage play |
| `home_prev_epa_play` | 96% | 2000 | home team: previous season mean, offence: EPA per scrimmage play |
| `home_l4_pass_epa_play` | 98% | 1999 | home team: mean of previous 4 games, offence: EPA per dropback |
| `home_l8_pass_epa_play` | 98% | 1999 | home team: mean of previous 8 games, offence: EPA per dropback |
| `home_ewm_pass_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), offence: EPA per dropback |
| `home_std_pass_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: EPA per dropback |
| `home_prev_pass_epa_play` | 96% | 2000 | home team: previous season mean, offence: EPA per dropback |
| `home_l4_rush_epa_play` | 98% | 1999 | home team: mean of previous 4 games, offence: EPA per rush |
| `home_l8_rush_epa_play` | 98% | 1999 | home team: mean of previous 8 games, offence: EPA per rush |
| `home_ewm_rush_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), offence: EPA per rush |
| `home_std_rush_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: EPA per rush |
| `home_prev_rush_epa_play` | 96% | 2000 | home team: previous season mean, offence: EPA per rush |
| `home_l4_success_rate` | 98% | 1999 | home team: mean of previous 4 games, offence: share of plays with positive EPA |
| `home_l8_success_rate` | 98% | 1999 | home team: mean of previous 8 games, offence: share of plays with positive EPA |
| `home_ewm_success_rate` | 100% | 1999 | home team: EWM (half-life 6 games), offence: share of plays with positive EPA |
| `home_std_success_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: share of plays with positive EPA |
| `home_prev_success_rate` | 96% | 2000 | home team: previous season mean, offence: share of plays with positive EPA |
| `home_l4_pass_success` | 98% | 1999 | home team: mean of previous 4 games, offence: success rate on dropbacks |
| `home_l8_pass_success` | 98% | 1999 | home team: mean of previous 8 games, offence: success rate on dropbacks |
| `home_ewm_pass_success` | 100% | 1999 | home team: EWM (half-life 6 games), offence: success rate on dropbacks |
| `home_std_pass_success` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: success rate on dropbacks |
| `home_prev_pass_success` | 96% | 2000 | home team: previous season mean, offence: success rate on dropbacks |
| `home_l4_rush_success` | 98% | 1999 | home team: mean of previous 4 games, offence: success rate on rushes |
| `home_l8_rush_success` | 98% | 1999 | home team: mean of previous 8 games, offence: success rate on rushes |
| `home_ewm_rush_success` | 100% | 1999 | home team: EWM (half-life 6 games), offence: success rate on rushes |
| `home_std_rush_success` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: success rate on rushes |
| `home_prev_rush_success` | 96% | 2000 | home team: previous season mean, offence: success rate on rushes |
| `home_l4_pass_rate` | 98% | 1999 | home team: mean of previous 4 games, offence: share of plays that are dropbacks |
| `home_l8_pass_rate` | 98% | 1999 | home team: mean of previous 8 games, offence: share of plays that are dropbacks |
| `home_ewm_pass_rate` | 100% | 1999 | home team: EWM (half-life 6 games), offence: share of plays that are dropbacks |
| `home_std_pass_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: share of plays that are dropbacks |
| `home_prev_pass_rate` | 96% | 2000 | home team: previous season mean, offence: share of plays that are dropbacks |
| `home_l4_early_down_pass_rate` | 98% | 1999 | home team: mean of previous 4 games, offence: dropback share on 1st/2nd down |
| `home_l8_early_down_pass_rate` | 98% | 1999 | home team: mean of previous 8 games, offence: dropback share on 1st/2nd down |
| `home_ewm_early_down_pass_rate` | 100% | 1999 | home team: EWM (half-life 6 games), offence: dropback share on 1st/2nd down |
| `home_std_early_down_pass_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: dropback share on 1st/2nd down |
| `home_prev_early_down_pass_rate` | 96% | 2000 | home team: previous season mean, offence: dropback share on 1st/2nd down |
| `home_l4_pass_oe` | 74% | 2006 | home team: mean of previous 4 games, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `home_l8_pass_oe` | 74% | 2006 | home team: mean of previous 8 games, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `home_ewm_pass_oe` | 75% | 2006 | home team: EWM (half-life 6 games), offence: pass rate over expected (mean of pass_oe, 2006+) |
| `home_std_pass_oe` | 75% | 2006 | home team: season-to-date mean (prev season in week 1), offence: pass rate over expected (mean of pass_oe, 2006+) |
| `home_prev_pass_oe` | 72% | 2007 | home team: previous season mean, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `home_l4_explosive_rate` | 98% | 1999 | home team: mean of previous 4 games, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_l8_explosive_rate` | 98% | 1999 | home team: mean of previous 8 games, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_ewm_explosive_rate` | 100% | 1999 | home team: EWM (half-life 6 games), offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_std_explosive_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_prev_explosive_rate` | 96% | 2000 | home team: previous season mean, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_l4_yards_play` | 98% | 1999 | home team: mean of previous 4 games, offence: yards per scrimmage play |
| `home_l8_yards_play` | 98% | 1999 | home team: mean of previous 8 games, offence: yards per scrimmage play |
| `home_ewm_yards_play` | 100% | 1999 | home team: EWM (half-life 6 games), offence: yards per scrimmage play |
| `home_std_yards_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: yards per scrimmage play |
| `home_prev_yards_play` | 96% | 2000 | home team: previous season mean, offence: yards per scrimmage play |
| `home_l4_cpoe` | 74% | 2006 | home team: mean of previous 4 games, offence: completion percentage over expected (2006+) |
| `home_l8_cpoe` | 74% | 2006 | home team: mean of previous 8 games, offence: completion percentage over expected (2006+) |
| `home_ewm_cpoe` | 75% | 2006 | home team: EWM (half-life 6 games), offence: completion percentage over expected (2006+) |
| `home_std_cpoe` | 75% | 2006 | home team: season-to-date mean (prev season in week 1), offence: completion percentage over expected (2006+) |
| `home_prev_cpoe` | 72% | 2007 | home team: previous season mean, offence: completion percentage over expected (2006+) |
| `home_l4_adot` | 74% | 2006 | home team: mean of previous 4 games, offence: average depth of target, air yards per attempt (2006+) |
| `home_l8_adot` | 74% | 2006 | home team: mean of previous 8 games, offence: average depth of target, air yards per attempt (2006+) |
| `home_ewm_adot` | 75% | 2006 | home team: EWM (half-life 6 games), offence: average depth of target, air yards per attempt (2006+) |
| `home_std_adot` | 75% | 2006 | home team: season-to-date mean (prev season in week 1), offence: average depth of target, air yards per attempt (2006+) |
| `home_prev_adot` | 72% | 2007 | home team: previous season mean, offence: average depth of target, air yards per attempt (2006+) |
| `home_l4_turnovers` | 98% | 1999 | home team: mean of previous 4 games, offence: interceptions + lost fumbles |
| `home_l8_turnovers` | 98% | 1999 | home team: mean of previous 8 games, offence: interceptions + lost fumbles |
| `home_ewm_turnovers` | 100% | 1999 | home team: EWM (half-life 6 games), offence: interceptions + lost fumbles |
| `home_std_turnovers` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: interceptions + lost fumbles |
| `home_prev_turnovers` | 96% | 2000 | home team: previous season mean, offence: interceptions + lost fumbles |
| `home_l4_sacks` | 98% | 1999 | home team: mean of previous 4 games, offence: sacks taken |
| `home_l8_sacks` | 98% | 1999 | home team: mean of previous 8 games, offence: sacks taken |
| `home_ewm_sacks` | 100% | 1999 | home team: EWM (half-life 6 games), offence: sacks taken |
| `home_std_sacks` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: sacks taken |
| `home_prev_sacks` | 96% | 2000 | home team: previous season mean, offence: sacks taken |
| `home_l4_third_down_conv` | 98% | 1999 | home team: mean of previous 4 games, offence: third-down conversion rate |
| `home_l8_third_down_conv` | 98% | 1999 | home team: mean of previous 8 games, offence: third-down conversion rate |
| `home_ewm_third_down_conv` | 100% | 1999 | home team: EWM (half-life 6 games), offence: third-down conversion rate |
| `home_std_third_down_conv` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: third-down conversion rate |
| `home_prev_third_down_conv` | 96% | 2000 | home team: previous season mean, offence: third-down conversion rate |
| `home_l4_drives` | 98% | 1999 | home team: mean of previous 4 games, offence: offensive drives |
| `home_l8_drives` | 98% | 1999 | home team: mean of previous 8 games, offence: offensive drives |
| `home_ewm_drives` | 100% | 1999 | home team: EWM (half-life 6 games), offence: offensive drives |
| `home_std_drives` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: offensive drives |
| `home_prev_drives` | 96% | 2000 | home team: previous season mean, offence: offensive drives |
| `home_l4_neutral_epa_play` | 98% | 1999 | home team: mean of previous 4 games, offence: EPA per play while score within 8 points, quarters 1-3 |
| `home_l8_neutral_epa_play` | 98% | 1999 | home team: mean of previous 8 games, offence: EPA per play while score within 8 points, quarters 1-3 |
| `home_ewm_neutral_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), offence: EPA per play while score within 8 points, quarters 1-3 |
| `home_std_neutral_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: EPA per play while score within 8 points, quarters 1-3 |
| `home_prev_neutral_epa_play` | 96% | 2000 | home team: previous season mean, offence: EPA per play while score within 8 points, quarters 1-3 |
| `home_l4_penalty_yards` | 98% | 1999 | home team: mean of previous 4 games, offence: penalty yards committed |
| `home_l8_penalty_yards` | 98% | 1999 | home team: mean of previous 8 games, offence: penalty yards committed |
| `home_ewm_penalty_yards` | 100% | 1999 | home team: EWM (half-life 6 games), offence: penalty yards committed |
| `home_std_penalty_yards` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), offence: penalty yards committed |
| `home_prev_penalty_yards` | 96% | 2000 | home team: previous season mean, offence: penalty yards committed |
| `home_l4_def_plays` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `home_l8_def_plays` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `home_ewm_def_plays` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `home_std_def_plays` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `home_prev_def_plays` | 96% | 2000 | home team: previous season mean, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `home_l4_def_epa_play` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: EPA per scrimmage play |
| `home_l8_def_epa_play` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: EPA per scrimmage play |
| `home_ewm_def_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: EPA per scrimmage play |
| `home_std_def_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: EPA per scrimmage play |
| `home_prev_def_epa_play` | 96% | 2000 | home team: previous season mean, defence allowed: EPA per scrimmage play |
| `home_l4_def_pass_epa_play` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: EPA per dropback |
| `home_l8_def_pass_epa_play` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: EPA per dropback |
| `home_ewm_def_pass_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: EPA per dropback |
| `home_std_def_pass_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: EPA per dropback |
| `home_prev_def_pass_epa_play` | 96% | 2000 | home team: previous season mean, defence allowed: EPA per dropback |
| `home_l4_def_rush_epa_play` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: EPA per rush |
| `home_l8_def_rush_epa_play` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: EPA per rush |
| `home_ewm_def_rush_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: EPA per rush |
| `home_std_def_rush_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: EPA per rush |
| `home_prev_def_rush_epa_play` | 96% | 2000 | home team: previous season mean, defence allowed: EPA per rush |
| `home_l4_def_success_rate` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: share of plays with positive EPA |
| `home_l8_def_success_rate` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: share of plays with positive EPA |
| `home_ewm_def_success_rate` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: share of plays with positive EPA |
| `home_std_def_success_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: share of plays with positive EPA |
| `home_prev_def_success_rate` | 96% | 2000 | home team: previous season mean, defence allowed: share of plays with positive EPA |
| `home_l4_def_pass_success` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: success rate on dropbacks |
| `home_l8_def_pass_success` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: success rate on dropbacks |
| `home_ewm_def_pass_success` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: success rate on dropbacks |
| `home_std_def_pass_success` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: success rate on dropbacks |
| `home_prev_def_pass_success` | 96% | 2000 | home team: previous season mean, defence allowed: success rate on dropbacks |
| `home_l4_def_rush_success` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: success rate on rushes |
| `home_l8_def_rush_success` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: success rate on rushes |
| `home_ewm_def_rush_success` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: success rate on rushes |
| `home_std_def_rush_success` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: success rate on rushes |
| `home_prev_def_rush_success` | 96% | 2000 | home team: previous season mean, defence allowed: success rate on rushes |
| `home_l4_def_pass_rate` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: share of plays that are dropbacks |
| `home_l8_def_pass_rate` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: share of plays that are dropbacks |
| `home_ewm_def_pass_rate` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: share of plays that are dropbacks |
| `home_std_def_pass_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: share of plays that are dropbacks |
| `home_prev_def_pass_rate` | 96% | 2000 | home team: previous season mean, defence allowed: share of plays that are dropbacks |
| `home_l4_def_early_down_pass_rate` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: dropback share on 1st/2nd down |
| `home_l8_def_early_down_pass_rate` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: dropback share on 1st/2nd down |
| `home_ewm_def_early_down_pass_rate` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: dropback share on 1st/2nd down |
| `home_std_def_early_down_pass_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: dropback share on 1st/2nd down |
| `home_prev_def_early_down_pass_rate` | 96% | 2000 | home team: previous season mean, defence allowed: dropback share on 1st/2nd down |
| `home_l4_def_pass_oe` | 74% | 2006 | home team: mean of previous 4 games, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `home_l8_def_pass_oe` | 74% | 2006 | home team: mean of previous 8 games, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `home_ewm_def_pass_oe` | 75% | 2006 | home team: EWM (half-life 6 games), defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `home_std_def_pass_oe` | 75% | 2006 | home team: season-to-date mean (prev season in week 1), defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `home_prev_def_pass_oe` | 72% | 2007 | home team: previous season mean, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `home_l4_def_explosive_rate` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_l8_def_explosive_rate` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_ewm_def_explosive_rate` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_std_def_explosive_rate` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_prev_def_explosive_rate` | 96% | 2000 | home team: previous season mean, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `home_l4_def_yards_play` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: yards per scrimmage play |
| `home_l8_def_yards_play` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: yards per scrimmage play |
| `home_ewm_def_yards_play` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: yards per scrimmage play |
| `home_std_def_yards_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: yards per scrimmage play |
| `home_prev_def_yards_play` | 96% | 2000 | home team: previous season mean, defence allowed: yards per scrimmage play |
| `home_l4_def_cpoe` | 74% | 2006 | home team: mean of previous 4 games, defence allowed: completion percentage over expected (2006+) |
| `home_l8_def_cpoe` | 74% | 2006 | home team: mean of previous 8 games, defence allowed: completion percentage over expected (2006+) |
| `home_ewm_def_cpoe` | 75% | 2006 | home team: EWM (half-life 6 games), defence allowed: completion percentage over expected (2006+) |
| `home_std_def_cpoe` | 75% | 2006 | home team: season-to-date mean (prev season in week 1), defence allowed: completion percentage over expected (2006+) |
| `home_prev_def_cpoe` | 72% | 2007 | home team: previous season mean, defence allowed: completion percentage over expected (2006+) |
| `home_l4_def_adot` | 74% | 2006 | home team: mean of previous 4 games, defence allowed: average depth of target, air yards per attempt (2006+) |
| `home_l8_def_adot` | 74% | 2006 | home team: mean of previous 8 games, defence allowed: average depth of target, air yards per attempt (2006+) |
| `home_ewm_def_adot` | 75% | 2006 | home team: EWM (half-life 6 games), defence allowed: average depth of target, air yards per attempt (2006+) |
| `home_std_def_adot` | 75% | 2006 | home team: season-to-date mean (prev season in week 1), defence allowed: average depth of target, air yards per attempt (2006+) |
| `home_prev_def_adot` | 72% | 2007 | home team: previous season mean, defence allowed: average depth of target, air yards per attempt (2006+) |
| `home_l4_def_turnovers` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: interceptions + lost fumbles |
| `home_l8_def_turnovers` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: interceptions + lost fumbles |
| `home_ewm_def_turnovers` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: interceptions + lost fumbles |
| `home_std_def_turnovers` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: interceptions + lost fumbles |
| `home_prev_def_turnovers` | 96% | 2000 | home team: previous season mean, defence allowed: interceptions + lost fumbles |
| `home_l4_def_sacks` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: sacks taken |
| `home_l8_def_sacks` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: sacks taken |
| `home_ewm_def_sacks` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: sacks taken |
| `home_std_def_sacks` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: sacks taken |
| `home_prev_def_sacks` | 96% | 2000 | home team: previous season mean, defence allowed: sacks taken |
| `home_l4_def_third_down_conv` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: third-down conversion rate |
| `home_l8_def_third_down_conv` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: third-down conversion rate |
| `home_ewm_def_third_down_conv` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: third-down conversion rate |
| `home_std_def_third_down_conv` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: third-down conversion rate |
| `home_prev_def_third_down_conv` | 96% | 2000 | home team: previous season mean, defence allowed: third-down conversion rate |
| `home_l4_def_drives` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: offensive drives |
| `home_l8_def_drives` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: offensive drives |
| `home_ewm_def_drives` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: offensive drives |
| `home_std_def_drives` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: offensive drives |
| `home_prev_def_drives` | 96% | 2000 | home team: previous season mean, defence allowed: offensive drives |
| `home_l4_def_neutral_epa_play` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `home_l8_def_neutral_epa_play` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `home_ewm_def_neutral_epa_play` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `home_std_def_neutral_epa_play` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `home_prev_def_neutral_epa_play` | 96% | 2000 | home team: previous season mean, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `home_l4_def_penalty_yards` | 98% | 1999 | home team: mean of previous 4 games, defence allowed: penalty yards committed |
| `home_l8_def_penalty_yards` | 98% | 1999 | home team: mean of previous 8 games, defence allowed: penalty yards committed |
| `home_ewm_def_penalty_yards` | 100% | 1999 | home team: EWM (half-life 6 games), defence allowed: penalty yards committed |
| `home_std_def_penalty_yards` | 100% | 1999 | home team: season-to-date mean (prev season in week 1), defence allowed: penalty yards committed |
| `home_prev_def_penalty_yards` | 96% | 2000 | home team: previous season mean, defence allowed: penalty yards committed |
| `home_games_played_season` | 100% | 1999 | home team: team's games already played this season |
| `away_l4_plays` | 98% | 1999 | away team: mean of previous 4 games, offence: scrimmage plays (pass or rush, EPA defined) |
| `away_l8_plays` | 98% | 1999 | away team: mean of previous 8 games, offence: scrimmage plays (pass or rush, EPA defined) |
| `away_ewm_plays` | 100% | 1999 | away team: EWM (half-life 6 games), offence: scrimmage plays (pass or rush, EPA defined) |
| `away_std_plays` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: scrimmage plays (pass or rush, EPA defined) |
| `away_prev_plays` | 96% | 2000 | away team: previous season mean, offence: scrimmage plays (pass or rush, EPA defined) |
| `away_l4_epa_play` | 98% | 1999 | away team: mean of previous 4 games, offence: EPA per scrimmage play |
| `away_l8_epa_play` | 98% | 1999 | away team: mean of previous 8 games, offence: EPA per scrimmage play |
| `away_ewm_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), offence: EPA per scrimmage play |
| `away_std_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: EPA per scrimmage play |
| `away_prev_epa_play` | 96% | 2000 | away team: previous season mean, offence: EPA per scrimmage play |
| `away_l4_pass_epa_play` | 98% | 1999 | away team: mean of previous 4 games, offence: EPA per dropback |
| `away_l8_pass_epa_play` | 98% | 1999 | away team: mean of previous 8 games, offence: EPA per dropback |
| `away_ewm_pass_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), offence: EPA per dropback |
| `away_std_pass_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: EPA per dropback |
| `away_prev_pass_epa_play` | 96% | 2000 | away team: previous season mean, offence: EPA per dropback |
| `away_l4_rush_epa_play` | 98% | 1999 | away team: mean of previous 4 games, offence: EPA per rush |
| `away_l8_rush_epa_play` | 98% | 1999 | away team: mean of previous 8 games, offence: EPA per rush |
| `away_ewm_rush_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), offence: EPA per rush |
| `away_std_rush_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: EPA per rush |
| `away_prev_rush_epa_play` | 96% | 2000 | away team: previous season mean, offence: EPA per rush |
| `away_l4_success_rate` | 98% | 1999 | away team: mean of previous 4 games, offence: share of plays with positive EPA |
| `away_l8_success_rate` | 98% | 1999 | away team: mean of previous 8 games, offence: share of plays with positive EPA |
| `away_ewm_success_rate` | 100% | 1999 | away team: EWM (half-life 6 games), offence: share of plays with positive EPA |
| `away_std_success_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: share of plays with positive EPA |
| `away_prev_success_rate` | 96% | 2000 | away team: previous season mean, offence: share of plays with positive EPA |
| `away_l4_pass_success` | 98% | 1999 | away team: mean of previous 4 games, offence: success rate on dropbacks |
| `away_l8_pass_success` | 98% | 1999 | away team: mean of previous 8 games, offence: success rate on dropbacks |
| `away_ewm_pass_success` | 100% | 1999 | away team: EWM (half-life 6 games), offence: success rate on dropbacks |
| `away_std_pass_success` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: success rate on dropbacks |
| `away_prev_pass_success` | 96% | 2000 | away team: previous season mean, offence: success rate on dropbacks |
| `away_l4_rush_success` | 98% | 1999 | away team: mean of previous 4 games, offence: success rate on rushes |
| `away_l8_rush_success` | 98% | 1999 | away team: mean of previous 8 games, offence: success rate on rushes |
| `away_ewm_rush_success` | 100% | 1999 | away team: EWM (half-life 6 games), offence: success rate on rushes |
| `away_std_rush_success` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: success rate on rushes |
| `away_prev_rush_success` | 96% | 2000 | away team: previous season mean, offence: success rate on rushes |
| `away_l4_pass_rate` | 98% | 1999 | away team: mean of previous 4 games, offence: share of plays that are dropbacks |
| `away_l8_pass_rate` | 98% | 1999 | away team: mean of previous 8 games, offence: share of plays that are dropbacks |
| `away_ewm_pass_rate` | 100% | 1999 | away team: EWM (half-life 6 games), offence: share of plays that are dropbacks |
| `away_std_pass_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: share of plays that are dropbacks |
| `away_prev_pass_rate` | 96% | 2000 | away team: previous season mean, offence: share of plays that are dropbacks |
| `away_l4_early_down_pass_rate` | 98% | 1999 | away team: mean of previous 4 games, offence: dropback share on 1st/2nd down |
| `away_l8_early_down_pass_rate` | 98% | 1999 | away team: mean of previous 8 games, offence: dropback share on 1st/2nd down |
| `away_ewm_early_down_pass_rate` | 100% | 1999 | away team: EWM (half-life 6 games), offence: dropback share on 1st/2nd down |
| `away_std_early_down_pass_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: dropback share on 1st/2nd down |
| `away_prev_early_down_pass_rate` | 96% | 2000 | away team: previous season mean, offence: dropback share on 1st/2nd down |
| `away_l4_pass_oe` | 74% | 2006 | away team: mean of previous 4 games, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `away_l8_pass_oe` | 74% | 2006 | away team: mean of previous 8 games, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `away_ewm_pass_oe` | 75% | 2006 | away team: EWM (half-life 6 games), offence: pass rate over expected (mean of pass_oe, 2006+) |
| `away_std_pass_oe` | 75% | 2006 | away team: season-to-date mean (prev season in week 1), offence: pass rate over expected (mean of pass_oe, 2006+) |
| `away_prev_pass_oe` | 72% | 2007 | away team: previous season mean, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `away_l4_explosive_rate` | 98% | 1999 | away team: mean of previous 4 games, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_l8_explosive_rate` | 98% | 1999 | away team: mean of previous 8 games, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_ewm_explosive_rate` | 100% | 1999 | away team: EWM (half-life 6 games), offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_std_explosive_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_prev_explosive_rate` | 96% | 2000 | away team: previous season mean, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_l4_yards_play` | 98% | 1999 | away team: mean of previous 4 games, offence: yards per scrimmage play |
| `away_l8_yards_play` | 98% | 1999 | away team: mean of previous 8 games, offence: yards per scrimmage play |
| `away_ewm_yards_play` | 100% | 1999 | away team: EWM (half-life 6 games), offence: yards per scrimmage play |
| `away_std_yards_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: yards per scrimmage play |
| `away_prev_yards_play` | 96% | 2000 | away team: previous season mean, offence: yards per scrimmage play |
| `away_l4_cpoe` | 74% | 2006 | away team: mean of previous 4 games, offence: completion percentage over expected (2006+) |
| `away_l8_cpoe` | 74% | 2006 | away team: mean of previous 8 games, offence: completion percentage over expected (2006+) |
| `away_ewm_cpoe` | 75% | 2006 | away team: EWM (half-life 6 games), offence: completion percentage over expected (2006+) |
| `away_std_cpoe` | 75% | 2006 | away team: season-to-date mean (prev season in week 1), offence: completion percentage over expected (2006+) |
| `away_prev_cpoe` | 72% | 2007 | away team: previous season mean, offence: completion percentage over expected (2006+) |
| `away_l4_adot` | 74% | 2006 | away team: mean of previous 4 games, offence: average depth of target, air yards per attempt (2006+) |
| `away_l8_adot` | 74% | 2006 | away team: mean of previous 8 games, offence: average depth of target, air yards per attempt (2006+) |
| `away_ewm_adot` | 75% | 2006 | away team: EWM (half-life 6 games), offence: average depth of target, air yards per attempt (2006+) |
| `away_std_adot` | 75% | 2006 | away team: season-to-date mean (prev season in week 1), offence: average depth of target, air yards per attempt (2006+) |
| `away_prev_adot` | 72% | 2007 | away team: previous season mean, offence: average depth of target, air yards per attempt (2006+) |
| `away_l4_turnovers` | 98% | 1999 | away team: mean of previous 4 games, offence: interceptions + lost fumbles |
| `away_l8_turnovers` | 98% | 1999 | away team: mean of previous 8 games, offence: interceptions + lost fumbles |
| `away_ewm_turnovers` | 100% | 1999 | away team: EWM (half-life 6 games), offence: interceptions + lost fumbles |
| `away_std_turnovers` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: interceptions + lost fumbles |
| `away_prev_turnovers` | 96% | 2000 | away team: previous season mean, offence: interceptions + lost fumbles |
| `away_l4_sacks` | 98% | 1999 | away team: mean of previous 4 games, offence: sacks taken |
| `away_l8_sacks` | 98% | 1999 | away team: mean of previous 8 games, offence: sacks taken |
| `away_ewm_sacks` | 100% | 1999 | away team: EWM (half-life 6 games), offence: sacks taken |
| `away_std_sacks` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: sacks taken |
| `away_prev_sacks` | 96% | 2000 | away team: previous season mean, offence: sacks taken |
| `away_l4_third_down_conv` | 98% | 1999 | away team: mean of previous 4 games, offence: third-down conversion rate |
| `away_l8_third_down_conv` | 98% | 1999 | away team: mean of previous 8 games, offence: third-down conversion rate |
| `away_ewm_third_down_conv` | 100% | 1999 | away team: EWM (half-life 6 games), offence: third-down conversion rate |
| `away_std_third_down_conv` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: third-down conversion rate |
| `away_prev_third_down_conv` | 96% | 2000 | away team: previous season mean, offence: third-down conversion rate |
| `away_l4_drives` | 98% | 1999 | away team: mean of previous 4 games, offence: offensive drives |
| `away_l8_drives` | 98% | 1999 | away team: mean of previous 8 games, offence: offensive drives |
| `away_ewm_drives` | 100% | 1999 | away team: EWM (half-life 6 games), offence: offensive drives |
| `away_std_drives` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: offensive drives |
| `away_prev_drives` | 96% | 2000 | away team: previous season mean, offence: offensive drives |
| `away_l4_neutral_epa_play` | 98% | 1999 | away team: mean of previous 4 games, offence: EPA per play while score within 8 points, quarters 1-3 |
| `away_l8_neutral_epa_play` | 98% | 1999 | away team: mean of previous 8 games, offence: EPA per play while score within 8 points, quarters 1-3 |
| `away_ewm_neutral_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), offence: EPA per play while score within 8 points, quarters 1-3 |
| `away_std_neutral_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: EPA per play while score within 8 points, quarters 1-3 |
| `away_prev_neutral_epa_play` | 96% | 2000 | away team: previous season mean, offence: EPA per play while score within 8 points, quarters 1-3 |
| `away_l4_penalty_yards` | 98% | 1999 | away team: mean of previous 4 games, offence: penalty yards committed |
| `away_l8_penalty_yards` | 98% | 1999 | away team: mean of previous 8 games, offence: penalty yards committed |
| `away_ewm_penalty_yards` | 100% | 1999 | away team: EWM (half-life 6 games), offence: penalty yards committed |
| `away_std_penalty_yards` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), offence: penalty yards committed |
| `away_prev_penalty_yards` | 96% | 2000 | away team: previous season mean, offence: penalty yards committed |
| `away_l4_def_plays` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `away_l8_def_plays` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `away_ewm_def_plays` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `away_std_def_plays` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `away_prev_def_plays` | 96% | 2000 | away team: previous season mean, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `away_l4_def_epa_play` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: EPA per scrimmage play |
| `away_l8_def_epa_play` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: EPA per scrimmage play |
| `away_ewm_def_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: EPA per scrimmage play |
| `away_std_def_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: EPA per scrimmage play |
| `away_prev_def_epa_play` | 96% | 2000 | away team: previous season mean, defence allowed: EPA per scrimmage play |
| `away_l4_def_pass_epa_play` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: EPA per dropback |
| `away_l8_def_pass_epa_play` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: EPA per dropback |
| `away_ewm_def_pass_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: EPA per dropback |
| `away_std_def_pass_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: EPA per dropback |
| `away_prev_def_pass_epa_play` | 96% | 2000 | away team: previous season mean, defence allowed: EPA per dropback |
| `away_l4_def_rush_epa_play` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: EPA per rush |
| `away_l8_def_rush_epa_play` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: EPA per rush |
| `away_ewm_def_rush_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: EPA per rush |
| `away_std_def_rush_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: EPA per rush |
| `away_prev_def_rush_epa_play` | 96% | 2000 | away team: previous season mean, defence allowed: EPA per rush |
| `away_l4_def_success_rate` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: share of plays with positive EPA |
| `away_l8_def_success_rate` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: share of plays with positive EPA |
| `away_ewm_def_success_rate` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: share of plays with positive EPA |
| `away_std_def_success_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: share of plays with positive EPA |
| `away_prev_def_success_rate` | 96% | 2000 | away team: previous season mean, defence allowed: share of plays with positive EPA |
| `away_l4_def_pass_success` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: success rate on dropbacks |
| `away_l8_def_pass_success` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: success rate on dropbacks |
| `away_ewm_def_pass_success` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: success rate on dropbacks |
| `away_std_def_pass_success` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: success rate on dropbacks |
| `away_prev_def_pass_success` | 96% | 2000 | away team: previous season mean, defence allowed: success rate on dropbacks |
| `away_l4_def_rush_success` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: success rate on rushes |
| `away_l8_def_rush_success` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: success rate on rushes |
| `away_ewm_def_rush_success` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: success rate on rushes |
| `away_std_def_rush_success` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: success rate on rushes |
| `away_prev_def_rush_success` | 96% | 2000 | away team: previous season mean, defence allowed: success rate on rushes |
| `away_l4_def_pass_rate` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: share of plays that are dropbacks |
| `away_l8_def_pass_rate` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: share of plays that are dropbacks |
| `away_ewm_def_pass_rate` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: share of plays that are dropbacks |
| `away_std_def_pass_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: share of plays that are dropbacks |
| `away_prev_def_pass_rate` | 96% | 2000 | away team: previous season mean, defence allowed: share of plays that are dropbacks |
| `away_l4_def_early_down_pass_rate` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: dropback share on 1st/2nd down |
| `away_l8_def_early_down_pass_rate` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: dropback share on 1st/2nd down |
| `away_ewm_def_early_down_pass_rate` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: dropback share on 1st/2nd down |
| `away_std_def_early_down_pass_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: dropback share on 1st/2nd down |
| `away_prev_def_early_down_pass_rate` | 96% | 2000 | away team: previous season mean, defence allowed: dropback share on 1st/2nd down |
| `away_l4_def_pass_oe` | 74% | 2006 | away team: mean of previous 4 games, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `away_l8_def_pass_oe` | 74% | 2006 | away team: mean of previous 8 games, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `away_ewm_def_pass_oe` | 75% | 2006 | away team: EWM (half-life 6 games), defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `away_std_def_pass_oe` | 75% | 2006 | away team: season-to-date mean (prev season in week 1), defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `away_prev_def_pass_oe` | 72% | 2007 | away team: previous season mean, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `away_l4_def_explosive_rate` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_l8_def_explosive_rate` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_ewm_def_explosive_rate` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_std_def_explosive_rate` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_prev_def_explosive_rate` | 96% | 2000 | away team: previous season mean, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `away_l4_def_yards_play` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: yards per scrimmage play |
| `away_l8_def_yards_play` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: yards per scrimmage play |
| `away_ewm_def_yards_play` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: yards per scrimmage play |
| `away_std_def_yards_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: yards per scrimmage play |
| `away_prev_def_yards_play` | 96% | 2000 | away team: previous season mean, defence allowed: yards per scrimmage play |
| `away_l4_def_cpoe` | 74% | 2006 | away team: mean of previous 4 games, defence allowed: completion percentage over expected (2006+) |
| `away_l8_def_cpoe` | 74% | 2006 | away team: mean of previous 8 games, defence allowed: completion percentage over expected (2006+) |
| `away_ewm_def_cpoe` | 75% | 2006 | away team: EWM (half-life 6 games), defence allowed: completion percentage over expected (2006+) |
| `away_std_def_cpoe` | 75% | 2006 | away team: season-to-date mean (prev season in week 1), defence allowed: completion percentage over expected (2006+) |
| `away_prev_def_cpoe` | 72% | 2007 | away team: previous season mean, defence allowed: completion percentage over expected (2006+) |
| `away_l4_def_adot` | 74% | 2006 | away team: mean of previous 4 games, defence allowed: average depth of target, air yards per attempt (2006+) |
| `away_l8_def_adot` | 74% | 2006 | away team: mean of previous 8 games, defence allowed: average depth of target, air yards per attempt (2006+) |
| `away_ewm_def_adot` | 75% | 2006 | away team: EWM (half-life 6 games), defence allowed: average depth of target, air yards per attempt (2006+) |
| `away_std_def_adot` | 75% | 2006 | away team: season-to-date mean (prev season in week 1), defence allowed: average depth of target, air yards per attempt (2006+) |
| `away_prev_def_adot` | 72% | 2007 | away team: previous season mean, defence allowed: average depth of target, air yards per attempt (2006+) |
| `away_l4_def_turnovers` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: interceptions + lost fumbles |
| `away_l8_def_turnovers` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: interceptions + lost fumbles |
| `away_ewm_def_turnovers` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: interceptions + lost fumbles |
| `away_std_def_turnovers` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: interceptions + lost fumbles |
| `away_prev_def_turnovers` | 96% | 2000 | away team: previous season mean, defence allowed: interceptions + lost fumbles |
| `away_l4_def_sacks` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: sacks taken |
| `away_l8_def_sacks` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: sacks taken |
| `away_ewm_def_sacks` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: sacks taken |
| `away_std_def_sacks` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: sacks taken |
| `away_prev_def_sacks` | 96% | 2000 | away team: previous season mean, defence allowed: sacks taken |
| `away_l4_def_third_down_conv` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: third-down conversion rate |
| `away_l8_def_third_down_conv` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: third-down conversion rate |
| `away_ewm_def_third_down_conv` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: third-down conversion rate |
| `away_std_def_third_down_conv` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: third-down conversion rate |
| `away_prev_def_third_down_conv` | 96% | 2000 | away team: previous season mean, defence allowed: third-down conversion rate |
| `away_l4_def_drives` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: offensive drives |
| `away_l8_def_drives` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: offensive drives |
| `away_ewm_def_drives` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: offensive drives |
| `away_std_def_drives` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: offensive drives |
| `away_prev_def_drives` | 96% | 2000 | away team: previous season mean, defence allowed: offensive drives |
| `away_l4_def_neutral_epa_play` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `away_l8_def_neutral_epa_play` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `away_ewm_def_neutral_epa_play` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `away_std_def_neutral_epa_play` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `away_prev_def_neutral_epa_play` | 96% | 2000 | away team: previous season mean, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `away_l4_def_penalty_yards` | 98% | 1999 | away team: mean of previous 4 games, defence allowed: penalty yards committed |
| `away_l8_def_penalty_yards` | 98% | 1999 | away team: mean of previous 8 games, defence allowed: penalty yards committed |
| `away_ewm_def_penalty_yards` | 100% | 1999 | away team: EWM (half-life 6 games), defence allowed: penalty yards committed |
| `away_std_def_penalty_yards` | 100% | 1999 | away team: season-to-date mean (prev season in week 1), defence allowed: penalty yards committed |
| `away_prev_def_penalty_yards` | 96% | 2000 | away team: previous season mean, defence allowed: penalty yards committed |
| `away_games_played_season` | 100% | 1999 | away team: team's games already played this season |
| `diff_l4_plays` | 98% | 1999 | home minus away: mean of previous 4 games, offence: scrimmage plays (pass or rush, EPA defined) |
| `diff_l8_plays` | 98% | 1999 | home minus away: mean of previous 8 games, offence: scrimmage plays (pass or rush, EPA defined) |
| `diff_ewm_plays` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: scrimmage plays (pass or rush, EPA defined) |
| `diff_std_plays` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: scrimmage plays (pass or rush, EPA defined) |
| `diff_prev_plays` | 96% | 2000 | home minus away: previous season mean, offence: scrimmage plays (pass or rush, EPA defined) |
| `diff_l4_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, offence: EPA per scrimmage play |
| `diff_l8_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, offence: EPA per scrimmage play |
| `diff_ewm_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: EPA per scrimmage play |
| `diff_std_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: EPA per scrimmage play |
| `diff_prev_epa_play` | 96% | 2000 | home minus away: previous season mean, offence: EPA per scrimmage play |
| `diff_l4_pass_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, offence: EPA per dropback |
| `diff_l8_pass_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, offence: EPA per dropback |
| `diff_ewm_pass_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: EPA per dropback |
| `diff_std_pass_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: EPA per dropback |
| `diff_prev_pass_epa_play` | 96% | 2000 | home minus away: previous season mean, offence: EPA per dropback |
| `diff_l4_rush_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, offence: EPA per rush |
| `diff_l8_rush_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, offence: EPA per rush |
| `diff_ewm_rush_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: EPA per rush |
| `diff_std_rush_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: EPA per rush |
| `diff_prev_rush_epa_play` | 96% | 2000 | home minus away: previous season mean, offence: EPA per rush |
| `diff_l4_success_rate` | 98% | 1999 | home minus away: mean of previous 4 games, offence: share of plays with positive EPA |
| `diff_l8_success_rate` | 98% | 1999 | home minus away: mean of previous 8 games, offence: share of plays with positive EPA |
| `diff_ewm_success_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: share of plays with positive EPA |
| `diff_std_success_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: share of plays with positive EPA |
| `diff_prev_success_rate` | 96% | 2000 | home minus away: previous season mean, offence: share of plays with positive EPA |
| `diff_l4_pass_success` | 98% | 1999 | home minus away: mean of previous 4 games, offence: success rate on dropbacks |
| `diff_l8_pass_success` | 98% | 1999 | home minus away: mean of previous 8 games, offence: success rate on dropbacks |
| `diff_ewm_pass_success` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: success rate on dropbacks |
| `diff_std_pass_success` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: success rate on dropbacks |
| `diff_prev_pass_success` | 96% | 2000 | home minus away: previous season mean, offence: success rate on dropbacks |
| `diff_l4_rush_success` | 98% | 1999 | home minus away: mean of previous 4 games, offence: success rate on rushes |
| `diff_l8_rush_success` | 98% | 1999 | home minus away: mean of previous 8 games, offence: success rate on rushes |
| `diff_ewm_rush_success` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: success rate on rushes |
| `diff_std_rush_success` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: success rate on rushes |
| `diff_prev_rush_success` | 96% | 2000 | home minus away: previous season mean, offence: success rate on rushes |
| `diff_l4_pass_rate` | 98% | 1999 | home minus away: mean of previous 4 games, offence: share of plays that are dropbacks |
| `diff_l8_pass_rate` | 98% | 1999 | home minus away: mean of previous 8 games, offence: share of plays that are dropbacks |
| `diff_ewm_pass_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: share of plays that are dropbacks |
| `diff_std_pass_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: share of plays that are dropbacks |
| `diff_prev_pass_rate` | 96% | 2000 | home minus away: previous season mean, offence: share of plays that are dropbacks |
| `diff_l4_early_down_pass_rate` | 98% | 1999 | home minus away: mean of previous 4 games, offence: dropback share on 1st/2nd down |
| `diff_l8_early_down_pass_rate` | 98% | 1999 | home minus away: mean of previous 8 games, offence: dropback share on 1st/2nd down |
| `diff_ewm_early_down_pass_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: dropback share on 1st/2nd down |
| `diff_std_early_down_pass_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: dropback share on 1st/2nd down |
| `diff_prev_early_down_pass_rate` | 96% | 2000 | home minus away: previous season mean, offence: dropback share on 1st/2nd down |
| `diff_l4_pass_oe` | 74% | 2006 | home minus away: mean of previous 4 games, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_l8_pass_oe` | 74% | 2006 | home minus away: mean of previous 8 games, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_ewm_pass_oe` | 75% | 2006 | home minus away: EWM (half-life 6 games), offence: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_std_pass_oe` | 75% | 2006 | home minus away: season-to-date mean (prev season in week 1), offence: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_prev_pass_oe` | 72% | 2007 | home minus away: previous season mean, offence: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_l4_explosive_rate` | 98% | 1999 | home minus away: mean of previous 4 games, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_l8_explosive_rate` | 98% | 1999 | home minus away: mean of previous 8 games, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_ewm_explosive_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_std_explosive_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_prev_explosive_rate` | 96% | 2000 | home minus away: previous season mean, offence: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_l4_yards_play` | 98% | 1999 | home minus away: mean of previous 4 games, offence: yards per scrimmage play |
| `diff_l8_yards_play` | 98% | 1999 | home minus away: mean of previous 8 games, offence: yards per scrimmage play |
| `diff_ewm_yards_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: yards per scrimmage play |
| `diff_std_yards_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: yards per scrimmage play |
| `diff_prev_yards_play` | 96% | 2000 | home minus away: previous season mean, offence: yards per scrimmage play |
| `diff_l4_cpoe` | 74% | 2006 | home minus away: mean of previous 4 games, offence: completion percentage over expected (2006+) |
| `diff_l8_cpoe` | 74% | 2006 | home minus away: mean of previous 8 games, offence: completion percentage over expected (2006+) |
| `diff_ewm_cpoe` | 75% | 2006 | home minus away: EWM (half-life 6 games), offence: completion percentage over expected (2006+) |
| `diff_std_cpoe` | 75% | 2006 | home minus away: season-to-date mean (prev season in week 1), offence: completion percentage over expected (2006+) |
| `diff_prev_cpoe` | 72% | 2007 | home minus away: previous season mean, offence: completion percentage over expected (2006+) |
| `diff_l4_adot` | 74% | 2006 | home minus away: mean of previous 4 games, offence: average depth of target, air yards per attempt (2006+) |
| `diff_l8_adot` | 74% | 2006 | home minus away: mean of previous 8 games, offence: average depth of target, air yards per attempt (2006+) |
| `diff_ewm_adot` | 75% | 2006 | home minus away: EWM (half-life 6 games), offence: average depth of target, air yards per attempt (2006+) |
| `diff_std_adot` | 75% | 2006 | home minus away: season-to-date mean (prev season in week 1), offence: average depth of target, air yards per attempt (2006+) |
| `diff_prev_adot` | 72% | 2007 | home minus away: previous season mean, offence: average depth of target, air yards per attempt (2006+) |
| `diff_l4_turnovers` | 98% | 1999 | home minus away: mean of previous 4 games, offence: interceptions + lost fumbles |
| `diff_l8_turnovers` | 98% | 1999 | home minus away: mean of previous 8 games, offence: interceptions + lost fumbles |
| `diff_ewm_turnovers` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: interceptions + lost fumbles |
| `diff_std_turnovers` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: interceptions + lost fumbles |
| `diff_prev_turnovers` | 96% | 2000 | home minus away: previous season mean, offence: interceptions + lost fumbles |
| `diff_l4_sacks` | 98% | 1999 | home minus away: mean of previous 4 games, offence: sacks taken |
| `diff_l8_sacks` | 98% | 1999 | home minus away: mean of previous 8 games, offence: sacks taken |
| `diff_ewm_sacks` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: sacks taken |
| `diff_std_sacks` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: sacks taken |
| `diff_prev_sacks` | 96% | 2000 | home minus away: previous season mean, offence: sacks taken |
| `diff_l4_third_down_conv` | 98% | 1999 | home minus away: mean of previous 4 games, offence: third-down conversion rate |
| `diff_l8_third_down_conv` | 98% | 1999 | home minus away: mean of previous 8 games, offence: third-down conversion rate |
| `diff_ewm_third_down_conv` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: third-down conversion rate |
| `diff_std_third_down_conv` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: third-down conversion rate |
| `diff_prev_third_down_conv` | 96% | 2000 | home minus away: previous season mean, offence: third-down conversion rate |
| `diff_l4_drives` | 98% | 1999 | home minus away: mean of previous 4 games, offence: offensive drives |
| `diff_l8_drives` | 98% | 1999 | home minus away: mean of previous 8 games, offence: offensive drives |
| `diff_ewm_drives` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: offensive drives |
| `diff_std_drives` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: offensive drives |
| `diff_prev_drives` | 96% | 2000 | home minus away: previous season mean, offence: offensive drives |
| `diff_l4_neutral_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, offence: EPA per play while score within 8 points, quarters 1-3 |
| `diff_l8_neutral_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, offence: EPA per play while score within 8 points, quarters 1-3 |
| `diff_ewm_neutral_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: EPA per play while score within 8 points, quarters 1-3 |
| `diff_std_neutral_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: EPA per play while score within 8 points, quarters 1-3 |
| `diff_prev_neutral_epa_play` | 96% | 2000 | home minus away: previous season mean, offence: EPA per play while score within 8 points, quarters 1-3 |
| `diff_l4_penalty_yards` | 98% | 1999 | home minus away: mean of previous 4 games, offence: penalty yards committed |
| `diff_l8_penalty_yards` | 98% | 1999 | home minus away: mean of previous 8 games, offence: penalty yards committed |
| `diff_ewm_penalty_yards` | 100% | 1999 | home minus away: EWM (half-life 6 games), offence: penalty yards committed |
| `diff_std_penalty_yards` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), offence: penalty yards committed |
| `diff_prev_penalty_yards` | 96% | 2000 | home minus away: previous season mean, offence: penalty yards committed |
| `diff_l4_def_plays` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `diff_l8_def_plays` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `diff_ewm_def_plays` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `diff_std_def_plays` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `diff_prev_def_plays` | 96% | 2000 | home minus away: previous season mean, defence allowed: scrimmage plays (pass or rush, EPA defined) |
| `diff_l4_def_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: EPA per scrimmage play |
| `diff_l8_def_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: EPA per scrimmage play |
| `diff_ewm_def_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: EPA per scrimmage play |
| `diff_std_def_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: EPA per scrimmage play |
| `diff_prev_def_epa_play` | 96% | 2000 | home minus away: previous season mean, defence allowed: EPA per scrimmage play |
| `diff_l4_def_pass_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: EPA per dropback |
| `diff_l8_def_pass_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: EPA per dropback |
| `diff_ewm_def_pass_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: EPA per dropback |
| `diff_std_def_pass_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: EPA per dropback |
| `diff_prev_def_pass_epa_play` | 96% | 2000 | home minus away: previous season mean, defence allowed: EPA per dropback |
| `diff_l4_def_rush_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: EPA per rush |
| `diff_l8_def_rush_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: EPA per rush |
| `diff_ewm_def_rush_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: EPA per rush |
| `diff_std_def_rush_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: EPA per rush |
| `diff_prev_def_rush_epa_play` | 96% | 2000 | home minus away: previous season mean, defence allowed: EPA per rush |
| `diff_l4_def_success_rate` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: share of plays with positive EPA |
| `diff_l8_def_success_rate` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: share of plays with positive EPA |
| `diff_ewm_def_success_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: share of plays with positive EPA |
| `diff_std_def_success_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: share of plays with positive EPA |
| `diff_prev_def_success_rate` | 96% | 2000 | home minus away: previous season mean, defence allowed: share of plays with positive EPA |
| `diff_l4_def_pass_success` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: success rate on dropbacks |
| `diff_l8_def_pass_success` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: success rate on dropbacks |
| `diff_ewm_def_pass_success` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: success rate on dropbacks |
| `diff_std_def_pass_success` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: success rate on dropbacks |
| `diff_prev_def_pass_success` | 96% | 2000 | home minus away: previous season mean, defence allowed: success rate on dropbacks |
| `diff_l4_def_rush_success` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: success rate on rushes |
| `diff_l8_def_rush_success` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: success rate on rushes |
| `diff_ewm_def_rush_success` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: success rate on rushes |
| `diff_std_def_rush_success` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: success rate on rushes |
| `diff_prev_def_rush_success` | 96% | 2000 | home minus away: previous season mean, defence allowed: success rate on rushes |
| `diff_l4_def_pass_rate` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: share of plays that are dropbacks |
| `diff_l8_def_pass_rate` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: share of plays that are dropbacks |
| `diff_ewm_def_pass_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: share of plays that are dropbacks |
| `diff_std_def_pass_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: share of plays that are dropbacks |
| `diff_prev_def_pass_rate` | 96% | 2000 | home minus away: previous season mean, defence allowed: share of plays that are dropbacks |
| `diff_l4_def_early_down_pass_rate` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: dropback share on 1st/2nd down |
| `diff_l8_def_early_down_pass_rate` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: dropback share on 1st/2nd down |
| `diff_ewm_def_early_down_pass_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: dropback share on 1st/2nd down |
| `diff_std_def_early_down_pass_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: dropback share on 1st/2nd down |
| `diff_prev_def_early_down_pass_rate` | 96% | 2000 | home minus away: previous season mean, defence allowed: dropback share on 1st/2nd down |
| `diff_l4_def_pass_oe` | 74% | 2006 | home minus away: mean of previous 4 games, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_l8_def_pass_oe` | 74% | 2006 | home minus away: mean of previous 8 games, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_ewm_def_pass_oe` | 75% | 2006 | home minus away: EWM (half-life 6 games), defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_std_def_pass_oe` | 75% | 2006 | home minus away: season-to-date mean (prev season in week 1), defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_prev_def_pass_oe` | 72% | 2007 | home minus away: previous season mean, defence allowed: pass rate over expected (mean of pass_oe, 2006+) |
| `diff_l4_def_explosive_rate` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_l8_def_explosive_rate` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_ewm_def_explosive_rate` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_std_def_explosive_rate` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_prev_def_explosive_rate` | 96% | 2000 | home minus away: previous season mean, defence allowed: share of plays gaining 20+ (pass) or 10+ (rush) yards |
| `diff_l4_def_yards_play` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: yards per scrimmage play |
| `diff_l8_def_yards_play` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: yards per scrimmage play |
| `diff_ewm_def_yards_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: yards per scrimmage play |
| `diff_std_def_yards_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: yards per scrimmage play |
| `diff_prev_def_yards_play` | 96% | 2000 | home minus away: previous season mean, defence allowed: yards per scrimmage play |
| `diff_l4_def_cpoe` | 74% | 2006 | home minus away: mean of previous 4 games, defence allowed: completion percentage over expected (2006+) |
| `diff_l8_def_cpoe` | 74% | 2006 | home minus away: mean of previous 8 games, defence allowed: completion percentage over expected (2006+) |
| `diff_ewm_def_cpoe` | 75% | 2006 | home minus away: EWM (half-life 6 games), defence allowed: completion percentage over expected (2006+) |
| `diff_std_def_cpoe` | 75% | 2006 | home minus away: season-to-date mean (prev season in week 1), defence allowed: completion percentage over expected (2006+) |
| `diff_prev_def_cpoe` | 72% | 2007 | home minus away: previous season mean, defence allowed: completion percentage over expected (2006+) |
| `diff_l4_def_adot` | 74% | 2006 | home minus away: mean of previous 4 games, defence allowed: average depth of target, air yards per attempt (2006+) |
| `diff_l8_def_adot` | 74% | 2006 | home minus away: mean of previous 8 games, defence allowed: average depth of target, air yards per attempt (2006+) |
| `diff_ewm_def_adot` | 75% | 2006 | home minus away: EWM (half-life 6 games), defence allowed: average depth of target, air yards per attempt (2006+) |
| `diff_std_def_adot` | 75% | 2006 | home minus away: season-to-date mean (prev season in week 1), defence allowed: average depth of target, air yards per attempt (2006+) |
| `diff_prev_def_adot` | 72% | 2007 | home minus away: previous season mean, defence allowed: average depth of target, air yards per attempt (2006+) |
| `diff_l4_def_turnovers` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: interceptions + lost fumbles |
| `diff_l8_def_turnovers` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: interceptions + lost fumbles |
| `diff_ewm_def_turnovers` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: interceptions + lost fumbles |
| `diff_std_def_turnovers` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: interceptions + lost fumbles |
| `diff_prev_def_turnovers` | 96% | 2000 | home minus away: previous season mean, defence allowed: interceptions + lost fumbles |
| `diff_l4_def_sacks` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: sacks taken |
| `diff_l8_def_sacks` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: sacks taken |
| `diff_ewm_def_sacks` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: sacks taken |
| `diff_std_def_sacks` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: sacks taken |
| `diff_prev_def_sacks` | 96% | 2000 | home minus away: previous season mean, defence allowed: sacks taken |
| `diff_l4_def_third_down_conv` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: third-down conversion rate |
| `diff_l8_def_third_down_conv` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: third-down conversion rate |
| `diff_ewm_def_third_down_conv` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: third-down conversion rate |
| `diff_std_def_third_down_conv` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: third-down conversion rate |
| `diff_prev_def_third_down_conv` | 96% | 2000 | home minus away: previous season mean, defence allowed: third-down conversion rate |
| `diff_l4_def_drives` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: offensive drives |
| `diff_l8_def_drives` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: offensive drives |
| `diff_ewm_def_drives` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: offensive drives |
| `diff_std_def_drives` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: offensive drives |
| `diff_prev_def_drives` | 96% | 2000 | home minus away: previous season mean, defence allowed: offensive drives |
| `diff_l4_def_neutral_epa_play` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `diff_l8_def_neutral_epa_play` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `diff_ewm_def_neutral_epa_play` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `diff_std_def_neutral_epa_play` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `diff_prev_def_neutral_epa_play` | 96% | 2000 | home minus away: previous season mean, defence allowed: EPA per play while score within 8 points, quarters 1-3 |
| `diff_l4_def_penalty_yards` | 98% | 1999 | home minus away: mean of previous 4 games, defence allowed: penalty yards committed |
| `diff_l8_def_penalty_yards` | 98% | 1999 | home minus away: mean of previous 8 games, defence allowed: penalty yards committed |
| `diff_ewm_def_penalty_yards` | 100% | 1999 | home minus away: EWM (half-life 6 games), defence allowed: penalty yards committed |
| `diff_std_def_penalty_yards` | 100% | 1999 | home minus away: season-to-date mean (prev season in week 1), defence allowed: penalty yards committed |
| `diff_prev_def_penalty_yards` | 96% | 2000 | home minus away: previous season mean, defence allowed: penalty yards committed |

## quarterback (23 columns)

| column | non-null | from | description |
|---|---|---|---|
| `home_qb_ewm_epa_db` | 97% | 1999 | home team: scheduled starting QB: EWM (half-life 8 games) of EPA per dropback before this game |
| `home_qb_ewm_cpoe` | 72% | 2006 | home team: starting QB: EWM of completion % over expected (2006+) |
| `home_qb_ewm_success` | 97% | 1999 | home team: starting QB: EWM success rate per dropback |
| `home_qb_ewm_sack_rate` | 97% | 1999 | home team: starting QB: EWM sack rate per dropback |
| `home_qb_ewm_int_rate` | 97% | 1999 | home team: starting QB: EWM interception rate per dropback |
| `home_qb_career_dropbacks` | 100% | 1999 | home team: starting QB: dropbacks in all prior games |
| `home_qb_career_games` | 100% | 1999 | home team: starting QB: prior games with a dropback |
| `home_qb_changed` | 98% | 1999 | home team: 1 if the starter differs from the team's previous game |
| `home_qb_starts_with_team` | 98% | 1999 | home team: starter's prior starts for this team |
| `away_qb_ewm_epa_db` | 97% | 1999 | away team: scheduled starting QB: EWM (half-life 8 games) of EPA per dropback before this game |
| `away_qb_ewm_cpoe` | 72% | 2006 | away team: starting QB: EWM of completion % over expected (2006+) |
| `away_qb_ewm_success` | 97% | 1999 | away team: starting QB: EWM success rate per dropback |
| `away_qb_ewm_sack_rate` | 97% | 1999 | away team: starting QB: EWM sack rate per dropback |
| `away_qb_ewm_int_rate` | 97% | 1999 | away team: starting QB: EWM interception rate per dropback |
| `away_qb_career_dropbacks` | 100% | 1999 | away team: starting QB: dropbacks in all prior games |
| `away_qb_career_games` | 100% | 1999 | away team: starting QB: prior games with a dropback |
| `away_qb_changed` | 98% | 1999 | away team: 1 if the starter differs from the team's previous game |
| `away_qb_starts_with_team` | 98% | 1999 | away team: starter's prior starts for this team |
| `diff_qb_ewm_epa_db` | 96% | 1999 | home minus away: scheduled starting QB: EWM (half-life 8 games) of EPA per dropback before this game |
| `diff_qb_ewm_cpoe` | 71% | 2006 | home minus away: starting QB: EWM of completion % over expected (2006+) |
| `diff_qb_ewm_success` | 96% | 1999 | home minus away: starting QB: EWM success rate per dropback |
| `diff_qb_ewm_sack_rate` | 96% | 1999 | home minus away: starting QB: EWM sack rate per dropback |
| `diff_qb_ewm_int_rate` | 96% | 1999 | home minus away: starting QB: EWM interception rate per dropback |

## injuries (44 columns)

| column | non-null | from | description |
|---|---|---|---|
| `home_inj_out_DB` | 65% | 2009 | home team: players Out/Doubtful at DB (2009+) |
| `home_inj_out_DL` | 65% | 2009 | home team: players Out/Doubtful at DL (2009+) |
| `home_inj_out_LB` | 65% | 2009 | home team: players Out/Doubtful at LB (2009+) |
| `home_inj_out_OL` | 65% | 2009 | home team: players Out/Doubtful at OL (2009+) |
| `home_inj_out_QB` | 65% | 2009 | home team: players Out/Doubtful at QB (2009+) |
| `home_inj_out_RB` | 65% | 2009 | home team: players Out/Doubtful at RB (2009+) |
| `home_inj_out_ST` | 65% | 2009 | home team: players Out/Doubtful at ST (2009+) |
| `home_inj_out_TE` | 65% | 2009 | home team: players Out/Doubtful at TE (2009+) |
| `home_inj_out_WR` | 65% | 2009 | home team: players Out/Doubtful at WR (2009+) |
| `home_inj_quest_DB` | 65% | 2009 | home team: players Questionable at DB (2009+) |
| `home_inj_quest_DL` | 65% | 2009 | home team: players Questionable at DL (2009+) |
| `home_inj_quest_LB` | 65% | 2009 | home team: players Questionable at LB (2009+) |
| `home_inj_quest_OL` | 65% | 2009 | home team: players Questionable at OL (2009+) |
| `home_inj_quest_QB` | 65% | 2009 | home team: players Questionable at QB (2009+) |
| `home_inj_quest_RB` | 65% | 2009 | home team: players Questionable at RB (2009+) |
| `home_inj_quest_ST` | 65% | 2009 | home team: players Questionable at ST (2009+) |
| `home_inj_quest_TE` | 65% | 2009 | home team: players Questionable at TE (2009+) |
| `home_inj_quest_WR` | 65% | 2009 | home team: players Questionable at WR (2009+) |
| `home_inj_out_total` | 65% | 2009 | home team: players listed Out or Doubtful on the final injury report (2009+) |
| `home_inj_quest_total` | 65% | 2009 | home team: players listed Questionable (2009+) |
| `home_inj_snapwt_off` | 51% | 2013 | home team: sum of previous-game offensive snap share of players now Out/Doubtful (2013+) |
| `home_inj_snapwt_def` | 51% | 2013 | home team: sum of previous-game defensive snap share of players now Out/Doubtful (2013+) |
| `away_inj_out_DB` | 65% | 2009 | away team: players Out/Doubtful at DB (2009+) |
| `away_inj_out_DL` | 65% | 2009 | away team: players Out/Doubtful at DL (2009+) |
| `away_inj_out_LB` | 65% | 2009 | away team: players Out/Doubtful at LB (2009+) |
| `away_inj_out_OL` | 65% | 2009 | away team: players Out/Doubtful at OL (2009+) |
| `away_inj_out_QB` | 65% | 2009 | away team: players Out/Doubtful at QB (2009+) |
| `away_inj_out_RB` | 65% | 2009 | away team: players Out/Doubtful at RB (2009+) |
| `away_inj_out_ST` | 65% | 2009 | away team: players Out/Doubtful at ST (2009+) |
| `away_inj_out_TE` | 65% | 2009 | away team: players Out/Doubtful at TE (2009+) |
| `away_inj_out_WR` | 65% | 2009 | away team: players Out/Doubtful at WR (2009+) |
| `away_inj_quest_DB` | 65% | 2009 | away team: players Questionable at DB (2009+) |
| `away_inj_quest_DL` | 65% | 2009 | away team: players Questionable at DL (2009+) |
| `away_inj_quest_LB` | 65% | 2009 | away team: players Questionable at LB (2009+) |
| `away_inj_quest_OL` | 65% | 2009 | away team: players Questionable at OL (2009+) |
| `away_inj_quest_QB` | 65% | 2009 | away team: players Questionable at QB (2009+) |
| `away_inj_quest_RB` | 65% | 2009 | away team: players Questionable at RB (2009+) |
| `away_inj_quest_ST` | 65% | 2009 | away team: players Questionable at ST (2009+) |
| `away_inj_quest_TE` | 65% | 2009 | away team: players Questionable at TE (2009+) |
| `away_inj_quest_WR` | 65% | 2009 | away team: players Questionable at WR (2009+) |
| `away_inj_out_total` | 65% | 2009 | away team: players listed Out or Doubtful on the final injury report (2009+) |
| `away_inj_quest_total` | 65% | 2009 | away team: players listed Questionable (2009+) |
| `away_inj_snapwt_off` | 51% | 2013 | away team: sum of previous-game offensive snap share of players now Out/Doubtful (2013+) |
| `away_inj_snapwt_def` | 51% | 2013 | away team: sum of previous-game defensive snap share of players now Out/Doubtful (2013+) |
