"""Walk-forward RF with the observed-weather columns removed, to answer the timing question."""
import sys, time; sys.path.insert(0, 'src'); import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from pmrisk import DATA_PROCESSED
g = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet")
g = g[g.home_score.notna() & (g.season >= 2000)].reset_index(drop=True)
EXCLUDE = {"home_score", "away_score", "margin", "total_pts", "home_win", "season", "week", "home_elo", "away_elo"}
MARKET = ["spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds", "market_p_home", "market_overround"]
WEATHER = {"temp", "wind", "temp_filled", "wind_filled"}
FEATS = [c for c in g.columns if pd.api.types.is_numeric_dtype(g[c]) and c not in EXCLUDE and c not in MARKET and c not in WEATHER]
print(len(FEATS), "features without weather")
def rf(): return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), RandomForestRegressor(n_estimators=500, min_samples_leaf=20, max_features=0.3, n_jobs=-1, random_state=0))
rows = []; t0 = time.time()
for t in range(2010, 2026):
    tr, te = g[g.season < t], g[g.season == t]
    p = rf().fit(tr[FEATS], tr[["home_score", "away_score"]]).predict(te[FEATS])
    rows.append(pd.DataFrame({"game_id": te.game_id.values, "season": t, "nw_home": p[:, 0], "nw_away": p[:, 1]}))
    print(t, f"{time.time()-t0:.0f}s", flush=True)
out = pd.concat(rows); out.to_csv(DATA_PROCESSED / "model_rf_noweather_predictions.csv", index=False)
P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv").merge(out, on=["game_id", "season"])
P["nw_margin"] = P.nw_home - P.nw_away; P["nw_total"] = P.nw_home + P.nw_away
for k, (a, b) in {"margin": ("rf_margin", "nw_margin"), "total": ("rf_total", "nw_total")}.items():
    y = P.margin if k == "margin" else P.total_pts
    print(k, "with weather", round((P[a] - y).abs().mean(), 3), "without", round((P[b] - y).abs().mean(), 3))
print("home", round((P.rf_home - P.home_score).abs().mean(), 3), round((P.nw_home - P.home_score).abs().mean(), 3))
print("away", round((P.rf_away - P.away_score).abs().mean(), 3), round((P.nw_away - P.away_score).abs().mean(), 3))
