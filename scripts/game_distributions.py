"""Full outcome distributions from the two predicted scores, compared with the Vegas spread and total.

For selected 2025 games: margin and total distributions from (a) the empirical score grid tilted to the
forest's predicted margin and total and (b) a bivariate normal with the pooled residual covariance;
the Vegas spread and total are marked, and P(cover), P(over), P(win) are tabulated for all games.
"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pmrisk import DATA_PROCESSED, FIGURES
from pmrisk.score_model import empirical_grid, tilt
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})

P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv")
SH, SA, RHO = 9.64, 9.36, 0.011   # pooled residual sds and correlation of the two-output forest
SD_M, SD_T = np.sqrt(SH**2 + SA**2 - 2*RHO*SH*SA), np.sqrt(SH**2 + SA**2 + 2*RHO*SH*SA)
full = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet"); full = full[full.home_score.notna()]
prior = empirical_grid(full[full.season < 2025], smooth=0.02)

S = P[P.season == 2025].copy()
# pick four contrasting games: biggest home favourite, near pick'em, highest and lowest predicted total
picks = {"big favourite": S.loc[S.rf_margin.idxmax()], "pick'em": S.loc[(S.rf_margin).abs().idxmin()],
         "high total": S.loc[S.rf_total.idxmax()], "low total": S.loc[S.rf_total.idxmin()]}
fig, axes = plt.subplots(2, 4, figsize=(16, 7))
rows = []
for j, (label, r) in enumerate(picks.items()):
    g, _ = tilt(prior, r.rf_margin, r.rf_total)
    pm, pt = g.margin_pmf(), g.total_pmf()
    ks = np.arange(-35, 36); ts = np.arange(10, 81)
    ax = axes[0, j]
    ax.bar(ks, pm.reindex(ks, fill_value=0).values, color="#4C72B0", width=0.9, label="score grid tilted to forest")
    ax.plot(ks, stats.norm.pdf(ks, r.rf_margin, SD_M), "k--", lw=1, label="bivariate normal")
    ax.axvline(r.spread_line, color="#DD8452", lw=1.5, label=f"Vegas spread {r.spread_line:+.1f}")
    ax.axvline(r.margin, color="#55A868", lw=1.2, ls=":", label=f"actual {r.margin:+.0f}")
    ax.set(title=f"{label}: {r.away_team} at {r.home_team}, wk {r.week}\nP(cover)={g.p_margin_over(r.spread_line):.2f}  P(home win)={g.p_home_win():.2f}", xlabel=f"margin ({r.home_team} − {r.away_team})")
    ax.title.set_fontsize(9)
    if j == 0: ax.legend(fontsize=6); ax.set_ylabel("probability")
    ax = axes[1, j]
    ax.bar(ts, pt.reindex(ts, fill_value=0).values, color="#55A868", width=0.9)
    ax.plot(ts, stats.norm.pdf(ts, r.rf_total, SD_T), "k--", lw=1)
    ax.axvline(r.total_line, color="#DD8452", lw=1.5, label=f"Vegas total {r.total_line}")
    ax.axvline(r.total_pts, color="#4C72B0", lw=1.2, ls=":", label=f"actual {r.total_pts:.0f}")
    ax.set(title=f"P(over)={g.p_total_over(r.total_line):.2f}   model total {r.rf_total:.1f}", xlabel="total points"); ax.title.set_fontsize(9); ax.legend(fontsize=6)
    if j == 0: ax.set_ylabel("probability")
    rows.append({"game": f"{r.away_team} at {r.home_team}", "week": r.week, "pred_home": round(r.rf_home, 1), "pred_away": round(r.rf_away, 1),
                 "model_margin": round(r.rf_margin, 1), "vegas_spread": r.spread_line, "p_cover": round(g.p_margin_over(r.spread_line), 3),
                 "model_total": round(r.rf_total, 1), "vegas_total": r.total_line, "p_over": round(g.p_total_over(r.total_line), 3), "p_home_win": round(g.p_home_win(), 3),
                 "actual": f"{r.home_score:.0f}-{r.away_score:.0f}"})
fig.suptitle("Model outcome distributions vs the Vegas lines, four 2025 games", y=1.01)
fig.tight_layout(); fig.savefig(FIGURES / "game_distributions.png", bbox_inches="tight"); plt.close(fig)
ex = pd.DataFrame(rows); ex.to_csv(DATA_PROCESSED / "game_distributions_examples.csv", index=False); print(ex.to_string(index=False))

# all 2016-2025 games: how far do model cover/over probabilities stray from 0.5, and are they calibrated?
Q = P[P.season >= 2016].dropna(subset=["rf_grid_p_cover", "rf_grid_p_over"])
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
for ax, col, y, lab in [(axes[0], "rf_grid_p_cover", "y_cover", "P(home covers Vegas spread)"), (axes[1], "rf_grid_p_over", "y_over", "P(over Vegas total)")]:
    d = Q.dropna(subset=[y]); b = pd.cut(d[col], np.arange(0.2, 0.81, 0.1)); cal = d.groupby(b, observed=True).agg(p=(col, "mean"), yy=(y, "mean"), n=(y, "size"))
    ax.plot([0.2, 0.8], [0.2, 0.8], "k--", lw=0.8); ax.errorbar(cal.p, cal.yy, yerr=1.96*np.sqrt(cal.p*(1-cal.p)/cal.n), fmt="o-", color="#4C72B0", capsize=2)
    for p_, yy_, n_ in zip(cal.p, cal.yy, cal.n): ax.annotate(int(n_), (p_, yy_), textcoords="offset points", xytext=(4, -10), fontsize=7)
    ax.set(xlabel=f"model {lab}", ylabel="observed frequency", title=f"{lab}: calibration 2016-2025", xlim=(0.2, 0.8), ylim=(0.2, 0.8)); ax.title.set_fontsize(9)
fig.tight_layout(); fig.savefig(FIGURES / "cover_over_calibration.png"); plt.close(fig)
summary = {"sd_margin_model": round(SD_M, 2), "sd_total_model": round(SD_T, 2), "p_cover_mean": round(Q.rf_grid_p_cover.mean(), 3), "p_cover_sd": round(Q.rf_grid_p_cover.std(), 3),
           "p_over_mean": round(Q.rf_grid_p_over.mean(), 3), "p_over_sd": round(Q.rf_grid_p_over.std(), 3),
           "share_p_cover_beyond_60_40": round(float(((Q.rf_grid_p_cover > 0.6) | (Q.rf_grid_p_cover < 0.4)).mean()), 3),
           "cover_brier": round(float(((Q.rf_grid_p_cover - Q.y_cover)**2).dropna().mean()), 4), "over_brier": round(float(((Q.rf_grid_p_over - Q.y_over)**2).dropna().mean()), 4)}
json.dump(summary, open(DATA_PROCESSED / "game_distributions_summary.json", "w"), indent=2); print(summary)
