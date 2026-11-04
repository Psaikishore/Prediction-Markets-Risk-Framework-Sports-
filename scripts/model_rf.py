"""Multi-output random forest for (home_score, away_score), walk-forward by season, with benchmarks
and a probabilistic layer that feeds the forest's score predictions into the empirical score grid.

Outputs: data/processed/model_rf_*.csv, reports/figures/rf_*.png
"""

import json
import sys
import time
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pmrisk import DATA_PROCESSED, FIGURES
from pmrisk.nfl import completed_games, load_schedules
from pmrisk.score_model import empirical_grid, tilt

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
C = {"rf": "#4C72B0", "ridge": "#55A868", "elo": "#8172B2", "line": "#DD8452", "avg": "#999999"}
TEST_SEASONS = list(range(2010, 2026))

g = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet")
g = g[g.home_score.notna() & (g.season >= 2000)].reset_index(drop=True)

TARGETS = ["home_score", "away_score"]
EXCLUDE = {"home_score", "away_score", "margin", "total_pts", "home_win", "season", "week", "home_elo", "away_elo"}
MARKET = ["spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds", "market_p_home", "market_overround"]
FEATS = [c for c in g.columns if pd.api.types.is_numeric_dtype(g[c]) and c not in EXCLUDE and c not in MARKET]
print(f"{len(g)} games, {len(FEATS)} features")


def rf():
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                         RandomForestRegressor(n_estimators=500, min_samples_leaf=20, max_features=0.3, n_jobs=-1, random_state=0))


def ridge():
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), RidgeCV(alphas=np.logspace(0, 4, 15)))


# ---------------------------------------------------------------- walk-forward -------------------------------
preds, rows, importances = [], [], []
t0 = time.time()
for t in TEST_SEASONS:
    tr, te = g[g.season < t], g[g.season == t]
    out = te[["game_id", "season", "week", "home_team", "away_team", "home_score", "away_score", "margin", "total_pts", "home_win",
              "spread_line", "total_line", "market_p_home", "elo_spread", "elo_p_home"]].copy()
    m_rf = rf().fit(tr[FEATS], tr[TARGETS]); p = m_rf.predict(te[FEATS])
    out["rf_home"], out["rf_away"] = p[:, 0], p[:, 1]
    # per-tree spread as an uncertainty signal
    imp = m_rf[-1]; Xte = m_rf[0].transform(te[FEATS])
    tree_preds = np.stack([est.predict(Xte) for est in imp.estimators_])  # trees x n x 2
    out["rf_sd_margin"] = (tree_preds[:, :, 0] - tree_preds[:, :, 1]).std(axis=0)
    importances.append(pd.Series(imp.feature_importances_, index=FEATS))
    m_rg = ridge().fit(tr[FEATS], tr[TARGETS]); q = m_rg.predict(te[FEATS])
    out["ridge_home"], out["ridge_away"] = q[:, 0], q[:, 1]
    out["avg_home"], out["avg_away"] = tr.home_score.mean(), tr.away_score.mean()
    preds.append(out)
    print(f"season {t}: {len(te)} games, {time.time()-t0:.0f}s")
P = pd.concat(preds, ignore_index=True)
for m in ["rf", "ridge", "avg"]:
    P[f"{m}_margin"] = P[f"{m}_home"] - P[f"{m}_away"]; P[f"{m}_total"] = P[f"{m}_home"] + P[f"{m}_away"]
P.to_csv(DATA_PROCESSED / "model_rf_predictions.csv", index=False)

# ---------------------------------------------------------------- point accuracy -----------------------------
def mae(a, b): return float((a - b).abs().mean())
acc = {
    "league average": {"home": mae(P.avg_home, P.home_score), "away": mae(P.avg_away, P.away_score), "margin": mae(P.avg_margin, P.margin), "total": mae(P.avg_total, P.total_pts)},
    "Elo": {"margin": mae(P.elo_spread, P.margin)},
    "ridge (multi-output)": {"home": mae(P.ridge_home, P.home_score), "away": mae(P.ridge_away, P.away_score), "margin": mae(P.ridge_margin, P.margin), "total": mae(P.ridge_total, P.total_pts)},
    "random forest (multi-output)": {"home": mae(P.rf_home, P.home_score), "away": mae(P.rf_away, P.away_score), "margin": mae(P.rf_margin, P.margin), "total": mae(P.rf_total, P.total_pts)},
    "closing line": {"margin": mae(P.spread_line, P.margin), "total": mae(P.total_line, P.total_pts)},
}
acc_df = pd.DataFrame(acc).T.round(3); acc_df.to_csv(DATA_PROCESSED / "model_rf_point_accuracy.csv")
by_season = P.groupby("season").apply(lambda d: pd.Series({"rf": mae(d.rf_margin, d.margin), "ridge": mae(d.ridge_margin, d.margin), "elo": mae(d.elo_spread, d.margin), "line": mae(d.spread_line, d.margin)}), include_groups=False)
by_season.round(3).to_csv(DATA_PROCESSED / "model_rf_margin_by_season.csv")

# Straight-up winner accuracy and against-the-spread rate
win = {"rf": ((P.rf_margin > 0) == (P.margin > 0)).mean(), "ridge": ((P.ridge_margin > 0) == (P.margin > 0)).mean(),
       "elo": ((P.elo_spread > 0) == (P.margin > 0)).mean(), "line": ((P.spread_line > 0) == (P.margin > 0)).mean()}
nopush = P[P.margin != P.spread_line]
ats = {m: float(((nopush[f"{m}_margin"] > nopush.spread_line) == (nopush.margin > nopush.spread_line)).mean()) for m in ["rf", "ridge"]}
ats["elo"] = float(((nopush.elo_spread > nopush.spread_line) == (nopush.margin > nopush.spread_line)).mean())

# ---------------------------------------------------------------- probabilistic layer -----------------------
# Feed each model's (margin, total) into the empirical score grid (prior = all games before the test season)
hist_all = completed_games(load_schedules())
hist_full = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet")
hist_full = hist_full[hist_full.home_score.notna()]
def grid_probs(sub, src_margin, src_total, prior):
    pw, pc, po = [], [], []
    for r in sub.itertuples():
        try:
            gr, _ = tilt(prior, getattr(r, src_margin), getattr(r, src_total))
            pw.append(gr.p_home_win()); pc.append(gr.p_margin_over(r.spread_line)); po.append(gr.p_total_over(r.total_line))
        except Exception:
            pw.append(np.nan); pc.append(np.nan); po.append(np.nan)
    return np.array(pw), np.array(pc), np.array(po)

prob_rows = []
P["y_cover"] = np.where(P.margin == P.spread_line, np.nan, (P.margin > P.spread_line).astype(float))
P["y_over"] = np.where(P.total_pts == P.total_line, np.nan, (P.total_pts > P.total_line).astype(float))
for t in TEST_SEASONS[6:]:  # 2016-2025 to keep runtime modest
    sub = P[P.season == t]
    prior = empirical_grid(hist_full[hist_full.season < t], smooth=0.02)
    for src in ["rf", "ridge"]:
        pw, pc, po = grid_probs(sub, f"{src}_margin", f"{src}_total", prior)
        P.loc[sub.index, f"{src}_grid_p_win"], P.loc[sub.index, f"{src}_grid_p_cover"], P.loc[sub.index, f"{src}_grid_p_over"] = pw, pc, po
    pw, pc, po = grid_probs(sub, "spread_line", "total_line", prior)
    P.loc[sub.index, "line_grid_p_win"], P.loc[sub.index, "line_grid_p_cover"], P.loc[sub.index, "line_grid_p_over"] = pw, pc, po
    # normal alternative for the forest: N(rf_margin, 12.73)
    P.loc[sub.index, "rf_normal_p_win"] = stats.norm.cdf(sub.rf_margin / 12.73)
    print(f"grid probabilities {t}")
Q = P[P.season >= 2016]
def brier(p, y):
    m = p.notna() & y.notna(); return float(((p[m] - y[m]) ** 2).mean())
def logloss(p, y):
    m = p.notna() & y.notna(); p = p[m].clip(0.01, 0.99); return float(-(y[m] * np.log(p) + (1 - y[m]) * np.log(1 - p)).mean())
prob = {
    "RF scores -> grid": {"win Brier": brier(Q.rf_grid_p_win, Q.home_win), "win logloss": logloss(Q.rf_grid_p_win, Q.home_win), "cover Brier": brier(Q.rf_grid_p_cover, Q.y_cover), "over Brier": brier(Q.rf_grid_p_over, Q.y_over)},
    "RF margin -> normal(12.73)": {"win Brier": brier(Q.rf_normal_p_win, Q.home_win), "win logloss": logloss(Q.rf_normal_p_win, Q.home_win)},
    "ridge scores -> grid": {"win Brier": brier(Q.ridge_grid_p_win, Q.home_win), "win logloss": logloss(Q.ridge_grid_p_win, Q.home_win), "cover Brier": brier(Q.ridge_grid_p_cover, Q.y_cover), "over Brier": brier(Q.ridge_grid_p_over, Q.y_over)},
    "Elo": {"win Brier": brier(Q.elo_p_home, Q.home_win), "win logloss": logloss(Q.elo_p_home, Q.home_win)},
    "closing line -> grid": {"win Brier": brier(Q.line_grid_p_win, Q.home_win), "win logloss": logloss(Q.line_grid_p_win, Q.home_win), "cover Brier": brier(Q.line_grid_p_cover, Q.y_cover), "over Brier": brier(Q.line_grid_p_over, Q.y_over)},
    "de-vigged moneyline": {"win Brier": brier(Q.market_p_home, Q.home_win), "win logloss": logloss(Q.market_p_home, Q.home_win)},
}
prob_df = pd.DataFrame(prob).T.round(4); prob_df.to_csv(DATA_PROCESSED / "model_rf_probabilistic.csv")
P.to_csv(DATA_PROCESSED / "model_rf_predictions.csv", index=False)

# ---------------------------------------------------------------- figures ---------------------------------
imp = pd.concat(importances, axis=1).mean(axis=1).sort_values(ascending=False)
imp.to_csv(DATA_PROCESSED / "model_rf_importance.csv")
fig, ax = plt.subplots(figsize=(8, 6.5))
top = imp.head(25)[::-1]
ax.barh(top.index, top.values, color=C["rf"]); ax.set(xlabel="mean impurity importance (16 walk-forward fits)", title="Random forest: top 25 features")
ax.tick_params(axis="y", labelsize=7); fig.tight_layout(); fig.savefig(FIGURES / "rf_importance.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4))
for m, lab in [("rf", "random forest"), ("ridge", "ridge"), ("elo", "Elo"), ("line", "closing line")]:
    ax.plot(by_season.index, by_season[m], "o-", color=C[m], label=lab, ms=4)
ax.set(xlabel="test season", ylabel="MAE of home margin (points)", title="Walk-forward margin error by season"); ax.legend()
fig.tight_layout(); fig.savefig(FIGURES / "rf_mae_by_season.png"); plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
axes[0].scatter(P.rf_margin, P.margin, s=4, alpha=0.3, color=C["rf"]); axes[0].plot([-30, 30], [-30, 30], "k--", lw=0.8)
axes[0].set(xlabel="RF predicted margin", ylabel="actual margin", title=f"Margin: MAE {acc['random forest (multi-output)']['margin']:.2f}", xlim=(-30, 30), ylim=(-45, 45))
axes[1].scatter(P.spread_line, P.rf_margin, s=4, alpha=0.3, color=C["line"]); axes[1].plot([-20, 20], [-20, 20], "k--", lw=0.8)
axes[1].set(xlabel="closing spread (home)", ylabel="RF predicted margin", title=f"RF vs market: corr {P[['spread_line','rf_margin']].corr().iloc[0,1]:.3f}")
fig.tight_layout(); fig.savefig(FIGURES / "rf_pred_vs_actual.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(4.8, 4.5))
bins = np.arange(0, 1.01, 0.1); ax.plot([0, 1], [0, 1], "k--", lw=0.8)
for col, lab, c in [("rf_grid_p_win", "RF -> grid", C["rf"]), ("elo_p_home", "Elo", C["elo"]), ("market_p_home", "moneyline", C["line"])]:
    d = Q.dropna(subset=[col]); b = pd.cut(d[col], bins); cal = d.groupby(b, observed=True).agg(p=(col, "mean"), y=("home_win", "mean"))
    ax.plot(cal.p, cal.y, "o-", ms=4, color=c, label=lab)
ax.set(xlabel="predicted P(home win)", ylabel="observed", title="Calibration, 2016–2025"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIGURES / "rf_calibration.png"); plt.close(fig)

summary = {"n_games": int(len(P)), "n_features": len(FEATS), "test_seasons": f"{TEST_SEASONS[0]}-{TEST_SEASONS[-1]}",
           "point_mae": acc, "winner_accuracy": {k: round(float(v), 4) for k, v in win.items()}, "ats_accuracy": {k: round(v, 4) for k, v in ats.items()},
           "probabilistic_2016_2025": prob, "top_features": imp.head(15).round(4).to_dict(),
           "rf_sd_margin_corr_with_abs_error": round(float(np.corrcoef(P.rf_sd_margin, (P.rf_margin - P.margin).abs())[0, 1]), 4)}
(DATA_PROCESSED / "model_rf_summary.json").write_text(json.dumps(summary, indent=2))
print(acc_df.to_string()); print(); print(prob_df.to_string()); print(); print("winner acc", win); print("ATS", ats)
print(imp.head(15).round(4).to_string())
