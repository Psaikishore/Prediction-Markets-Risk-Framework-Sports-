"""Walk-forward baselines on the feature table: how close do pre-game features get to the closing line?

Trains on seasons < t, tests on season t, for t in 2010..2025. Targets: home margin and total.
Models: ridge on team-form/rating/QB/situational features (no market), and the same plus the closing line.
Benchmarks: league-average, Elo spread, closing line.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pmrisk import DATA_PROCESSED

g = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet")
g = g[g.home_score.notna() & (g.season >= 2000)].copy()

ident = {"home_score", "away_score", "margin", "total_pts", "home_win"}
market = ["spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds", "market_p_home", "market_overround"]
num = [c for c in g.columns if pd.api.types.is_numeric_dtype(g[c]) and c not in ident and c not in market
       and c not in ("season", "week", "home_elo", "away_elo") and not c.startswith(("home_inj_", "away_inj_"))]
# Use diff_* and situational columns plus Elo-derived; drop raw home_/away_ team form to keep ridge tractable.
feats = [c for c in num if c.startswith("diff_") or c in ("elo_diff", "elo_spread", "elo_p_home", "neutral_site", "dome", "grass", "temp_filled", "wind_filled",
         "primetime", "rest_diff", "bye_home", "bye_away", "short_week_home", "short_week_away", "div_game", "playoff", "home_qb_changed", "away_qb_changed",
         "home_qb_career_dropbacks", "away_qb_career_dropbacks", "home_games_played_season")]
feats += [c for c in g.columns if c.startswith(("home_ewm_", "away_ewm_")) and c.endswith(("epa_play", "pass_epa_play", "success_rate", "points_per_drive", "def_epa_play", "def_points_per_drive"))]
print(f"{len(feats)} features")

def ridge():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), RidgeCV(alphas=np.logspace(-1, 4, 20)))

def gbm():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, random_state=0)

rows = []
for target, line, label in [("margin", "spread_line", "margin"), ("total_pts", "total_line", "total")]:
    for t in range(2010, 2026):
        tr, te = g[g.season < t], g[g.season == t]
        y_tr, y_te = tr[target], te[target]
        res = {"target": label, "season": t, "n": len(te),
               "league_avg": (y_te - y_tr.mean()).abs().mean(),
               "closing_line": (y_te - te[line]).abs().mean()}
        if label == "margin":
            res["elo_spread"] = (y_te - te.elo_spread).abs().mean()
        for name, mk in (("ridge", ridge), ("gbm", gbm)):
            m = mk().fit(tr[feats], y_tr); res[f"{name}_no_market"] = (y_te - m.predict(te[feats])).abs().mean()
            m = mk().fit(tr[feats + [line]], y_tr); res[f"{name}_with_line"] = (y_te - m.predict(te[feats + [line]])).abs().mean()
        rows.append(res)
        print(f"{label} {t}: " + "  ".join(f"{k}={v:.2f}" for k, v in res.items() if k not in ("target", "season", "n")))
r = pd.DataFrame(rows)
r.to_csv(DATA_PROCESSED / "baseline_walkforward.csv", index=False)
print("\nMean absolute error, 2010-2025 pooled:")
print(r.groupby("target")[[c for c in r.columns if c not in ("target", "season", "n")]].mean().round(3).T.to_string())
