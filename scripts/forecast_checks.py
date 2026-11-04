"""Checks requested in the review of the 21 October report (Prof. Amine).

1. Uncertainty of the error differences between forecasts on the same games: paired mean absolute-error
   differences with i.i.d., week-clustered, season-clustered and Newey-West standard errors, plus a
   season-level paired t (16 test seasons).
2. Fold-wise residual covariance: the bivariate-normal win probability refitted with residual standard
   deviations from seasons before each test season, against the pooled version in the report.
3. Smoothing of the empirical score grid: zero cells, unseen score pairs, and the effect of the pseudo-count
   on tail probabilities and expected shortfall.
4. Calibration at thresholds fixed in advance (home wins by more than 0, 3, 7; away by more than 3;
   total over 41, 45, 48) against the market-set thresholds (cover, over), 2016-2025, fold-wise grid.
5. Forecast timing: the walk-forward forest refitted without the observed-weather columns
   (needs data/processed/model_rf_noweather_predictions.csv from the same refit loop as model_rf.py).

Outputs: data/processed/forecast_checks.json, forecast_checks_*.csv, reports/figures/fixed_threshold_calibration.png.
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, FIGURES
from pmrisk.nfl import completed_games, load_schedules
from pmrisk.score_model import empirical_grid, tilt

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv").sort_values(["season", "week"]).reset_index(drop=True)
out = {}


def brier(p, y):
    m = pd.notna(p) & pd.notna(y)
    return float(((p[m] - y[m]) ** 2).mean())


# ---- 1. paired error differences ----------------------------------------------------------------------------
def cluster_se(d, groups):
    """Cluster-robust standard error of the mean of d (Liang-Zeger with the G/(G-1) correction)."""
    m = pd.DataFrame({"d": d, "g": groups}).groupby("g").d.agg(["sum", "size"])
    u = m["sum"] - d.mean() * m["size"]
    return float(np.sqrt((u ** 2).sum()) / len(d) * np.sqrt(len(m) / (len(m) - 1)))


def newey_west_se(d, lags):
    x = np.asarray(d) - np.mean(d); n = len(x); v = np.sum(x * x) / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * np.sum(x[L:] * x[:-L]) / n
    return float(np.sqrt(v / n))


E = pd.DataFrame({"rf": (P.rf_margin - P.margin).abs(), "ridge": (P.ridge_margin - P.margin).abs(),
                  "elo": (P.elo_spread - P.margin).abs(), "line": (P.spread_line - P.margin).abs()})
week_id = P.season.astype(str) + "_" + P.week.astype(str).str.zfill(2)
rows = []
for a, b in [("rf", "elo"), ("ridge", "elo"), ("rf", "ridge"), ("rf", "line"), ("ridge", "line"), ("elo", "line")]:
    d = E[a] - E[b]
    per = d.groupby(P.season).mean()
    rows.append({"pair": f"{a} - {b}", "mean_diff": d.mean(), "se_iid": d.std() / np.sqrt(len(d)),
                 "se_week": cluster_se(d, week_id), "se_season": cluster_se(d, P.season),
                 "se_newey_west_68": newey_west_se(d, 68), "t_season_level": per.mean() / (per.std() / np.sqrt(len(per))),
                 "seasons_first_better": int((per < 0).sum()), "n_seasons": len(per), "n_games": len(d)})
pairs = pd.DataFrame(rows).round(4)
pairs.to_csv(DATA_PROCESSED / "forecast_checks_error_differences.csv", index=False)
out["error_differences"] = pairs.to_dict(orient="records")

# ---- 2. fold-wise residual covariance --------------------------------------------------------------------------
P["res_h"], P["res_a"] = P.home_score - P.rf_home, P.away_score - P.rf_away
fold = []
for t in range(2016, 2026):
    tr = P[P.season < t]
    sh, sa, rho = tr.res_h.std(), tr.res_a.std(), tr[["res_h", "res_a"]].corr().iloc[0, 1]
    sdm = np.sqrt(sh ** 2 + sa ** 2 - 2 * rho * sh * sa)
    P.loc[P.season == t, "bvn_fold_p_home"] = stats.norm.cdf(P.loc[P.season == t, "rf_margin"] / sdm)
    fold.append({"season": t, "sd_home": sh, "sd_away": sa, "rho": rho, "sd_margin": sdm, "n_train": len(tr)})
fold = pd.DataFrame(fold).round(4)
fold.to_csv(DATA_PROCESSED / "forecast_checks_foldwise_residuals.csv", index=False)
sh, sa, rho = P.res_h.std(), P.res_a.std(), P[["res_h", "res_a"]].corr().iloc[0, 1]
Q = P[P.season >= 2016].copy()
Q["bvn_pooled_p_home"] = stats.norm.cdf(Q.rf_margin / np.sqrt(sh ** 2 + sa ** 2 - 2 * rho * sh * sa))
out["win_brier_2016_2025"] = {"bvn_pooled": brier(Q.bvn_pooled_p_home, Q.home_win), "bvn_foldwise": brier(Q.bvn_fold_p_home, Q.home_win),
                              "grid_foldwise": brier(Q.rf_grid_p_win, Q.home_win), "elo": brier(Q.elo_p_home, Q.home_win),
                              "market": brier(Q.market_p_home, Q.home_win),
                              "foldwise_sd_margin_range": [float(fold.sd_margin.min()), float(fold.sd_margin.max())]}

# ---- 3. smoothing --------------------------------------------------------------------------------------------
hist = completed_games(load_schedules()); hist = hist[hist.season <= 2025]
sm_rows = []
for sm in [0.0, 0.02, 0.1]:
    g = empirical_grid(hist, smooth=sm)
    reach = np.ones_like(g.p, dtype=bool); reach[1, :] = False; reach[:, 1] = False  # a score of 1 is impossible
    gt, _ = tilt(g, -3.0, 44.5)
    pm, pt = gt.margin_pmf(), gt.total_pmf()
    row = {"smooth": sm, "nonzero_cells": int((g.p > 0).sum()), "zero_reachable_cells": int(((g.p == 0) & reach).sum()),
           "mass_added": sm / (1 + sm)}
    for k in (21, 28, 35, 42):
        row[f"P_abs_margin_ge_{k}"] = float(pm[np.abs(pm.index.to_numpy()) >= k].sum())
    for k in (60, 70, 80):
        row[f"P_total_ge_{k}"] = float(pt[pt.index.to_numpy() >= k].sum())
    for name, mask, short in [("long_home_gt_27.5", gt.margin > 27.5, False), ("short_home_gt_27.5", gt.margin > 27.5, True), ("short_over_69.5", gt.total > 69.5, True)]:
        price = float(gt.p[mask].sum())
        pnl = np.where(mask, 1 - price, -price) * 1000 * (-1 if short else 1)
        v, pr = pnl.ravel(), gt.p.ravel(); o = np.argsort(v); v, pr = v[o], pr[o]; c = np.cumsum(pr)
        k = np.searchsorted(c, 0.01); tail = pr[:k + 1].copy(); tail[-1] -= c[k] - 0.01
        row[f"{name}_price"], row[f"{name}_ES99"] = price, float(-(v[:k + 1] * tail).sum() / 0.01)
    sm_rows.append(row)
smooth = pd.DataFrame(sm_rows)
smooth.to_csv(DATA_PROCESSED / "forecast_checks_smoothing.csv", index=False)
unseen = {}
for t in (2020, 2023, 2025):
    seen = set(zip(hist[hist.season < t].home_score.astype(int), hist[hist.season < t].away_score.astype(int)))
    st = hist[hist.season == t]
    unseen[str(t)] = float(np.mean([(int(a), int(b)) not in seen for a, b in zip(st.home_score, st.away_score)]))
out["smoothing"] = {"table": smooth.round(5).to_dict(orient="records"), "share_of_games_with_unseen_score_pair": unseen}

# ---- 4. fixed-threshold calibration ----------------------------------------------------------------------------
feats = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet"); feats = feats[feats.home_score.notna()]
TH = {"home wins": ("m", 0), "home by > 3": ("m", 3), "home by > 7": ("m", 7), "away by > 3": ("m", -3),
      "total > 41": ("t", 41), "total > 45": ("t", 45), "total > 48": ("t", 48)}
for t in range(2016, 2026):
    prior = empirical_grid(feats[feats.season < t], smooth=0.02)
    for i in Q.index[Q.season == t]:
        g, _ = tilt(prior, Q.at[i, "rf_margin"], Q.at[i, "rf_total"])
        for k, (kind, v) in TH.items():
            Q.at[i, f"p:{k}"] = g.p_total_over(v) if kind == "t" else (g.p_margin_over(v) if v >= 0 else g.p_margin_under(v))
Q["y:home wins"] = np.where(Q.margin == 0, np.nan, (Q.margin > 0).astype(float))
Q["y:home by > 3"], Q["y:home by > 7"], Q["y:away by > 3"] = (Q.margin > 3) * 1.0, (Q.margin > 7) * 1.0, (Q.margin < -3) * 1.0
for v in (41, 45, 48):
    Q[f"y:total > {v}"] = (Q.total_pts > v) * 1.0
Q["p:cover (market)"], Q["y:cover (market)"] = Q.rf_grid_p_cover, Q.y_cover
Q["p:over (market)"], Q["y:over (market)"] = Q.rf_grid_p_over, Q.y_over
cal_rows, rel = [], {}
for k in list(TH) + ["cover (market)", "over (market)"]:
    p, y = Q[f"p:{k}"], Q[f"y:{k}"]; m = p.notna() & y.notna(); p, y = p[m], y[m]
    clim = float(((y.mean() - y) ** 2).mean()); b = brier(p, y)
    cal_rows.append({"threshold": k, "n": int(m.sum()), "base_rate": y.mean(), "sd_of_p": p.std(), "brier": b,
                     "brier_climatology": clim, "skill_vs_climatology": 1 - b / clim, "reliability_slope": np.polyfit(p, y, 1)[0]})
    bins = pd.cut(p, [0, .2, .3, .4, .5, .6, .7, .8, 1])
    rel[k] = pd.DataFrame({"p": p, "y": y}).groupby(bins, observed=True).agg(n=("y", "size"), pred=("p", "mean"), obs=("y", "mean"))
cal = pd.DataFrame(cal_rows).round(4)
cal.to_csv(DATA_PROCESSED / "forecast_checks_fixed_thresholds.csv", index=False)
out["fixed_threshold_calibration"] = cal.to_dict(orient="records")

fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, keys, title in [(axes[0], ["home wins", "home by > 3", "home by > 7", "away by > 3"], "margin thresholds fixed in advance"),
                        (axes[1], ["total > 41", "total > 45", "total > 48"], "total thresholds fixed in advance"),
                        (axes[2], ["cover (market)", "over (market)"], "thresholds set by the market")]:
    for k in keys:
        r = rel[k][rel[k].n >= 30]
        ax.plot(r.pred, r.obs, "o-", ms=3, label=k)
    ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set(xlim=(0.1, 0.9), ylim=(0.1, 0.9), xlabel="model probability", ylabel="observed frequency", title=title)
    ax.title.set_fontsize(9); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(FIGURES / "fixed_threshold_calibration.png"); plt.close(fig)

# ---- 5. forest without observed weather -------------------------------------------------------------------------
nw_path = DATA_PROCESSED / "model_rf_noweather_predictions.csv"
if nw_path.exists():
    nw = P.merge(pd.read_csv(nw_path), on=["game_id", "season"])
    nw["nw_margin"], nw["nw_total"] = nw.nw_home - nw.nw_away, nw.nw_home + nw.nw_away
    out["no_weather_refit"] = {"n_games": len(nw),
                               "margin_mae_with": float((nw.rf_margin - nw.margin).abs().mean()), "margin_mae_without": float((nw.nw_margin - nw.margin).abs().mean()),
                               "total_mae_with": float((nw.rf_total - nw.total_pts).abs().mean()), "total_mae_without": float((nw.nw_total - nw.total_pts).abs().mean()),
                               "home_mae_with": float((nw.rf_home - nw.home_score).abs().mean()), "home_mae_without": float((nw.nw_home - nw.home_score).abs().mean()),
                               "away_mae_with": float((nw.rf_away - nw.away_score).abs().mean()), "away_mae_without": float((nw.nw_away - nw.away_score).abs().mean())}

json.dump(out, open(DATA_PROCESSED / "forecast_checks.json", "w"), indent=2, default=float)
print(json.dumps(out, indent=2, default=float))
