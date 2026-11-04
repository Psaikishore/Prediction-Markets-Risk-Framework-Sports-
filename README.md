# Prediction-Markets Risk Framework (Sports)

Pricing and risk for NFL game contracts on Kalshi (winner, spread, total), built on a joint
distribution over the final score `p(home, away)`.

## Setup

```bash
mamba env create -f environment.yml   # creates the `nfl` env
mamba activate nfl
```

Optional: Kalshi API credentials in a `.env` at the repo root (gitignored) enable the
authenticated endpoints (candlesticks, order book):

```
KALSHI_API_KEY_ID=...
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem
```

## Pipeline

```bash
python scripts/pull_nfl.py      # nflverse schedules + closing lines, 2015-2026
python scripts/pull_kalshi.py   # Kalshi NFL markets, events, full trade tape (cached, incremental)
python scripts/eda_nfl.py       # score-distribution analysis -> reports/figures, data/processed
python scripts/eda_kalshi.py    # market analysis linked to results
python scripts/pull_kalshi_candles.py   # hourly bid/ask/OI candles for every market (needs .env credentials)
python scripts/eda_candles.py           # quoted spread, open interest, hourly volatility
python scripts/export_csv.py            # everything above as CSV under data/csv (see data/csv/README.md)
python scripts/toy_score_model.py       # worked example: tilted empirical score grid priced vs live Kalshi book
python scripts/build_features.py        # pre-game feature table 1999-2026 -> data/processed/features + reports/feature_dictionary.md
python scripts/test_leakage.py          # perturbation test: no feature uses its own game's data
python scripts/analyze_features.py      # integrity, coverage, signal, redundancy, drift, group value -> reports/features_analysis.md
python scripts/baseline_models.py       # walk-forward ridge/GBM vs Elo and the closing line
python scripts/model_rf.py              # multi-output random forest (both scores), walk-forward, grid probabilities, figures
python scripts/model_rf_2026.py         # 2026 live comparison vs Kalshi + next-week forecasts
python scripts/rf_bivariate.py          # joint home/away residuals, per-score calibration of the forest
python scripts/ensemble_external.py     # stacking test: our models + nfelo + 538 Elo + opening/closing lines
python scripts/game_distributions.py    # per-game margin/total distributions vs Vegas lines; cover/over calibration
python scripts/line_var.py              # line Greeks, open-to-close line moves, pre-game VaR + 2026 Kalshi backtest
python scripts/model_rf_noweather.py    # walk-forward forest without the observed-weather columns (forecast-timing check)
python scripts/forecast_checks.py       # review checks: paired-error SEs, fold-wise residuals, grid smoothing, fixed-threshold calibration
python scripts/pull_kalshi_parlays.py   # Kalshi parlay (MVE) markets with all-NFL legs, their fills from hourly candles (needs .env)
python scripts/parlay_analysis.py       # Kalshi parlays vs product of legs, independence, same-game premium, settlement (winner legs; --all-kinds, --sample N, --check)
python scripts/parlay_independence.py   # are cross-game legs independent? permutation and simulation tests -> reports/parlay_independence/
```

External forecasts live in `data/raw/external/` (nfelo output files from github.com/greerreNFL/nfelo; FiveThirtyEight's nfl_games.csv).

To validate the modelling end to end, run `notebooks/rf_two_score_model.ipynb` (about 6 minutes).

The presentation report with embedded figures is `reports/NFL_two_output_random_forest.docx`, built by `node scripts/build_report_docx.js` (needs `npm install docx`).

Raw and processed data live under `data/` and are not committed.

## Layout

- `src/pmrisk/kalshi.py` — rate-limited Kalshi API client (public + optional RSA-signed requests)
- `src/pmrisk/nfl.py` — nflverse loader and derived fields (margin, total, line residuals)
- `src/pmrisk/link.py` — Kalshi event ↔ nflverse game matching, pre-kickoff prices from trades
- `src/pmrisk/score_model.py` — empirical score grid, exponential tilting to a game's line, contract pricing
- `src/pmrisk/risk.py` — line Greeks (exact, from the tilt), (spread, total) price lattice, Kalshi-implied line, historical-simulation VaR
- `src/pmrisk/parlay.py` — parlay legs on the grid: joint probability of same-game legs, product across games, correlation premium (tests in `tests/test_parlay.py`)
- `src/pmrisk/features/` — pre-game features: play-by-play team form (`team_game`, `rolling`), Elo and margin ratings (`ratings`), starting QB (`qb`), injury reports (`injuries`), assembler (`build`)
- `reports/eda.md` — exploratory findings and modelling implications
- `reports/toy_example.md` — one-game walkthrough of building and pricing the joint distribution
- `reports/line_var.md` — pre-game line risk: Greeks, line-move distribution, VaR and its 2026 backtest
- `reports/parlay.md` — parlays: Kalshi fills vs the product of legs, independence across games, same-game premium, netting on the grid
- `reports/literature_data_sources.md` — what data the literature used, and what nflverse provides
- `reports/feature_dictionary.md` — every column of the feature table with coverage and definition
- `reports/latex/` — the research report (plain `article`): `report.tex` + `sections/{idea,data,week_*,conclusions}.tex` + `riskpredictor.bib`; compile with `pdflatex`, `bibtex`, `pdflatex` ×2, or upload `RiskPredictor_report_overleaf.zip` to Overleaf. Add a week by writing `sections/week_MMDD.tex` and one `\input` line.
