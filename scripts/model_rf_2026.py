"""Train the forest on 2000-2025, predict the 2026 games played so far, and compare with Kalshi pre-kickoff prices."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pmrisk import DATA_PROCESSED
from pmrisk.score_model import empirical_grid, tilt

g = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet")
EXCLUDE = {"home_score", "away_score", "margin", "total_pts", "home_win", "season", "week", "home_elo", "away_elo"}
MARKET = ["spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds", "market_p_home", "market_overround"]
FEATS = [c for c in g.columns if pd.api.types.is_numeric_dtype(g[c]) and c not in EXCLUDE and c not in MARKET]
tr = g[(g.season >= 2000) & (g.season < 2026) & g.home_score.notna()]
te = g[(g.season == 2026) & g.home_score.notna()].copy()
m = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                  RandomForestRegressor(n_estimators=500, min_samples_leaf=20, max_features=0.3, n_jobs=-1, random_state=0)).fit(tr[FEATS], tr[["home_score", "away_score"]])
p = m.predict(te[FEATS]); te["rf_home"], te["rf_away"] = p[:, 0], p[:, 1]
te["rf_margin"], te["rf_total"] = te.rf_home - te.rf_away, te.rf_home + te.rf_away
prior = empirical_grid(tr, smooth=0.02)
te["rf_p_home"] = [tilt(prior, r.rf_margin, r.rf_total)[0].p_home_win() for r in te.itertuples()]
k = pd.read_csv(DATA_PROCESSED / "kalshi_eda_winner_vs_book.csv", index_col=0)
k = k[k.is_home].rename(columns={"price": "kalshi_p_home"})[["event_ticker", "kalshi_p_home", "book_fair", "won"]]
ev = pd.read_csv(DATA_PROCESSED / "kalshi_eda_pregame_prices.csv", index_col=0)[["event_ticker", "game_id"]].drop_duplicates()
k = k.merge(ev, on="event_ticker").merge(te[["game_id", "rf_p_home", "rf_margin", "rf_total", "margin", "total_pts", "spread_line", "total_line", "elo_p_home", "home_win"]], on="game_id")
def brier(p, y): return float(((p - y) ** 2).mean())
out = {"n_games": int(len(k)),
       "brier": {"random forest -> grid": brier(k.rf_p_home, k.home_win), "Elo": brier(k.elo_p_home, k.home_win),
                 "Kalshi pre-kickoff": brier(k.kalshi_p_home, k.home_win), "sportsbook closing": brier(k.book_fair, k.home_win)},
       "mae_margin": {"random forest": float((k.rf_margin - k.margin).abs().mean()), "closing spread": float((k.spread_line - k.margin).abs().mean())},
       "mae_total": {"random forest": float((k.rf_total - k.total_pts).abs().mean()), "closing total": float((k.total_line - k.total_pts).abs().mean())},
       "corr_rf_vs_kalshi": float(np.corrcoef(k.rf_p_home, k.kalshi_p_home)[0, 1]),
       "mean_abs_gap_rf_vs_kalshi": float((k.rf_p_home - k.kalshi_p_home).abs().mean()),
       "winner_accuracy": {"random forest": float(((k.rf_p_home > 0.5) == (k.home_win == 1)).mean()), "Kalshi": float(((k.kalshi_p_home > 0.5) == (k.home_win == 1)).mean())}}
k.round(3).to_csv(DATA_PROCESSED / "model_rf_2026_vs_kalshi.csv", index=False)
(DATA_PROCESSED / "model_rf_2026_summary.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
# upcoming week forecasts
up = g[(g.season == 2026) & g.home_score.isna()].sort_values("kickoff").head(16).copy()
pu = m.predict(up[FEATS]); up["rf_home"], up["rf_away"] = pu[:, 0].round(1), pu[:, 1].round(1)
up["rf_margin"] = (up.rf_home - up.rf_away).round(1); up["rf_total"] = (up.rf_home + up.rf_away).round(1)
up["rf_p_home"] = [round(tilt(prior, r.rf_margin, r.rf_total)[0].p_home_win(), 3) for r in up.itertuples()]
cols = ["game_id", "gameday", "away_team", "home_team", "rf_away", "rf_home", "rf_margin", "rf_total", "rf_p_home", "spread_line", "total_line"]
up[cols].to_csv(DATA_PROCESSED / "model_rf_next_week.csv", index=False); print(up[cols].to_string(index=False))
