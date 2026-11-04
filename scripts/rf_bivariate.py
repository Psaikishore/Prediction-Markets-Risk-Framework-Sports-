"""Bivariate analysis of the two-output random forest: joint residuals of home and away score,
per-score calibration, and win probabilities from a bivariate normal on the residuals."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pmrisk import DATA_PROCESSED, FIGURES
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv")
P["res_h"], P["res_a"] = P.home_score - P.rf_home, P.away_score - P.rf_away
out = {"n": int(len(P)), "sd_home_res": round(P.res_h.std(), 2), "sd_away_res": round(P.res_a.std(), 2),
       "corr_res": round(P[["res_h", "res_a"]].corr().iloc[0, 1], 3),
       "sd_margin_res": round((P.margin - P.rf_margin).std(), 2), "sd_total_res": round((P.total_pts - P.rf_total).std(), 2),
       "sd_home_score": round(P.home_score.std(), 2), "sd_away_score": round(P.away_score.std(), 2),
       "r2_home": round(1 - P.res_h.var() / P.home_score.var(), 3), "r2_away": round(1 - P.res_a.var() / P.away_score.var(), 3),
       "pred_range_home": [round(P.rf_home.min(), 1), round(P.rf_home.max(), 1)], "pred_range_away": [round(P.rf_away.min(), 1), round(P.rf_away.max(), 1)]}
# heteroscedasticity: residual sd by predicted score tercile
for side in ["home", "away"]:
    q = pd.qcut(P[f"rf_{side}"], 3, labels=["low", "mid", "high"])
    out[f"res_sd_by_pred_{side}"] = P.groupby(q, observed=True)[f"res_{side[0]}"].std().round(2).to_dict()
# bivariate-normal win probability from pooled residual covariance (walk-forward would fit it on training residuals; here pooled for illustration)
sh, sa, rho = out["sd_home_res"], out["sd_away_res"], out["corr_res"]
sd_m = np.sqrt(sh**2 + sa**2 - 2 * rho * sh * sa)
P["bvn_p_home"] = stats.norm.cdf((P.rf_margin) / sd_m)
Q = P[P.season >= 2016]
out["bvn_win_brier_2016_2025"] = round(float(((Q.bvn_p_home - Q.home_win) ** 2).mean()), 4)
out["grid_win_brier_2016_2025"] = round(float(((Q.rf_grid_p_win - Q.home_win) ** 2).mean()), 4)
# per-score calibration
fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
for ax, side, c in zip(axes[:2], ["home", "away"], ["#4C72B0", "#DD8452"]):
    b = pd.cut(P[f"rf_{side}"], np.arange(10, 36, 2.5)); cal = P.groupby(b, observed=True).agg(p=(f"rf_{side}", "mean"), y=(f"{side}_score", "mean"), n=(f"{side}_score", "size"))
    ax.plot([12, 34], [12, 34], "k--", lw=0.8); ax.errorbar(cal.p, cal.y, yerr=1.96 * P[f"res_{side[0]}"].std() / np.sqrt(cal.n), fmt="o-", color=c, ms=4, capsize=2)
    ax.set(xlabel=f"predicted {side} score", ylabel=f"mean actual {side} score", title=f"{side} score calibration (MAE {np.abs(P[f'res_{side[0]}']).mean():.2f})")
axes[2].hist2d(P.res_h, P.res_a, bins=[np.arange(-30, 31, 2), np.arange(-30, 31, 2)], cmap="Blues")
axes[2].set(xlabel="home score residual", ylabel="away score residual", title=f"joint residuals: sd {sh}, {sa}; corr {rho}")
fig.tight_layout(); fig.savefig(FIGURES / "rf_bivariate.png"); plt.close(fig)
(DATA_PROCESSED / "model_rf_bivariate.json").write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))
