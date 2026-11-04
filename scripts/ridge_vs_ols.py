"""OLS vs ridge on the real feature table, for the explainer workbook reports/ridge_vs_ols.xlsx.

Same feature set and walk-forward as scripts/baseline_models.py (target: home margin).
Writes data/processed/ridge_vs_ols.json.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge, RidgeCV
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
feats = [c for c in num if c.startswith("diff_") or c in ("elo_diff", "elo_spread", "elo_p_home", "neutral_site", "dome", "grass", "temp_filled", "wind_filled",
         "primetime", "rest_diff", "bye_home", "bye_away", "short_week_home", "short_week_away", "div_game", "playoff", "home_qb_changed", "away_qb_changed",
         "home_qb_career_dropbacks", "away_qb_career_dropbacks", "home_games_played_season")]
feats += [c for c in g.columns if c.startswith(("home_ewm_", "away_ewm_")) and c.endswith(("epa_play", "pass_epa_play", "success_rate", "points_per_drive", "def_epa_play", "def_points_per_drive"))]
ALPHAS = np.logspace(-1, 4, 20)

def pipe(est):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), est)

def coefs(m):
    return m[-1].coef_

def fit_eval(est, tr, te):
    m = pipe(est).fit(tr[feats], tr.margin)
    b = coefs(m)
    return m, {"train_mae": float((tr.margin - m.predict(tr[feats])).abs().mean()),
               "test_mae": float((te.margin - m.predict(te[feats])).abs().mean()),
               "max_abs_coef": float(np.abs(b).max()), "sum_sq_coef": float((b ** 2).sum()), "sum_abs_coef": float(np.abs(b).sum())}

out = {"n_features": len(feats), "features": feats}

# 1. walk-forward, full training history
wf = []
for t in range(2010, 2026):
    tr, te = g[g.season < t], g[g.season == t]
    mo, ro = fit_eval(LinearRegression(), tr, te)
    mr, rr = fit_eval(RidgeCV(alphas=ALPHAS), tr, te)
    wf.append({"season": t, "n_train": len(tr), "n_test": len(te), "ols": ro, "ridge": rr, "alpha": float(mr[-1].alpha_),
               "line_mae": float((te.margin - te.spread_line).abs().mean())})
    print(t, len(tr), f"ols {ro['test_mae']:.3f} ridge {rr['test_mae']:.3f} alpha {mr[-1].alpha_:.1f}")
out["walk_forward"] = wf

# 2. same, but training on only the previous ONE season (small n vs p)
small = []
for t in range(2010, 2026):
    tr, te = g[g.season == t - 1], g[g.season == t]
    mo, ro = fit_eval(LinearRegression(), tr, te)
    mr, rr = fit_eval(RidgeCV(alphas=ALPHAS), tr, te)
    small.append({"season": t, "n_train": len(tr), "n_test": len(te), "ols": ro, "ridge": rr, "alpha": float(mr[-1].alpha_)})
    print("1-season", t, len(tr), f"ols {ro['test_mae']:.3f} ridge {rr['test_mae']:.3f} alpha {mr[-1].alpha_:.1f}")
out["one_season_train"] = small

# 3. alpha path on the 2025 fold, full history and one season
for key, tr in (("full", g[g.season < 2025]), ("one_season", g[g.season == 2024])):
    te = g[g.season == 2025]
    path = []
    for a in [0, 0.1, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 100000]:
        est = LinearRegression() if a == 0 else Ridge(alpha=a)
        m, r = fit_eval(est, tr, te)
        path.append({"alpha": a, **r})
    out[f"alpha_path_{key}"] = path

# 4. twin features: correlations and OLS vs ridge coefficients (2025 fold, full history)
tr, te = g[g.season < 2025], g[g.season == 2025]
X = pipe(StandardScaler())[:2].fit_transform(tr[feats])  # imputed + scaled
C = np.corrcoef(X, rowvar=False)
pairs = []
for i in range(len(feats)):
    for j in range(i + 1, len(feats)):
        pairs.append((feats[i], feats[j], float(C[i, j])))
pairs.sort(key=lambda p: -abs(p[2]))
out["top_corr_pairs"] = [{"a": a, "b": b, "corr": c} for a, b, c in pairs[:15]]
mo, _ = fit_eval(LinearRegression(), tr, te)
mr, _ = fit_eval(RidgeCV(alphas=ALPHAS), tr, te)
bo, br = coefs(mo), coefs(mr)
out["coef_table"] = [{"feature": f, "ols": float(o), "ridge": float(r)} for f, o, r in zip(feats, bo, br)]
out["alpha_2025"] = float(mr[-1].alpha_)
# same table trained on one season only
mo1, _ = fit_eval(LinearRegression(), g[g.season == 2024], te)
mr1, _ = fit_eval(RidgeCV(alphas=ALPHAS), g[g.season == 2024], te)
out["coef_table_one_season"] = [{"feature": f, "ols": float(o), "ridge": float(r)} for f, o, r in zip(feats, coefs(mo1), coefs(mr1))]
out["alpha_2025_one_season"] = float(mr1[-1].alpha_)
out["margin_sd"] = float(g.margin.std())
(DATA_PROCESSED / "ridge_vs_ols.json").write_text(json.dumps(out, indent=1))
print("wrote", DATA_PROCESSED / "ridge_vs_ols.json")
