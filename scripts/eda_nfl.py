"""Exploratory analysis of NFL final scores 2015-2026: margin, total and their joint structure.

Writes figures to reports/figures and summary tables to data/processed/nfl_eda_*.csv.
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

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
KEY_NUMBERS = [3, 7, 6, 10, 4, 14]


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    g = completed_games(load_schedules())
    reg = g[g.game_type == "REG"]
    summary = {"n_games": int(len(g)), "n_regular": int(len(reg)), "seasons": f"{g.season.min()}-{g.season.max()}"}

    # --- 1. Margin distribution and key numbers -----------------------------------
    absm = g.margin.abs()
    freq = absm.value_counts(normalize=True).sort_index()
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(freq.index, freq.values, color="#4C72B0", width=0.8)
    for k in KEY_NUMBERS:
        ax.bar(k, freq.get(k, 0), color="#DD8452", width=0.8)
    ax.set(xlim=(-0.5, 40), xlabel="|home − away| (points)", ylabel="share of games",
           title="Absolute margin of victory, 2015–2026 (key numbers highlighted)")
    fig.tight_layout(); fig.savefig(FIGURES / "nfl_abs_margin.png"); plt.close(fig)
    summary["p_margin"] = {int(k): round(float(freq.get(k, 0)), 4) for k in [1, 2, 3, 4, 5, 6, 7, 8, 10, 14]}
    summary["p_tie"] = round(float((g.margin == 0).mean()), 4)
    summary["home_win_rate"] = round(float((g.margin > 0).mean()), 4)

    # --- 2. Margin vs Stern normal given the closing spread ------------------------
    lined = g.dropna(subset=["spread_line"])
    err = lined.ats_error
    summary["ats_error_mean"] = round(float(err.mean()), 3)
    summary["ats_error_sd"] = round(float(err.std()), 3)
    by_season = lined.groupby("season").ats_error.agg(["mean", "std", "count"]).round(3)
    by_season.to_csv(DATA_PROCESSED / "nfl_eda_ats_by_season.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    bins = np.arange(-45.5, 46.5, 1)
    ax.hist(err, bins=bins, density=True, color="#4C72B0", alpha=0.8, label="actual margin − spread")
    x = np.linspace(-45, 45, 400)
    ax.plot(x, stats.norm.pdf(x, 0, 13.86), "k--", lw=1.5, label="N(0, 13.86²)  Stern 1991")
    ax.plot(x, stats.norm.pdf(x, err.mean(), err.std()), color="#DD8452", lw=1.5, label=f"N({err.mean():.2f}, {err.std():.2f}²) fitted")
    ax.set(xlabel="margin − closing spread", ylabel="density", title="Cover margin vs normal"); ax.legend(fontsize=8)
    ax = axes[1]
    ax.errorbar(by_season.index, by_season["mean"], yerr=1.96 * by_season["std"] / np.sqrt(by_season["count"]), fmt="o-", color="#4C72B0")
    ax.axhline(0, color="k", lw=0.8); ax.set(xlabel="season", ylabel="mean(margin − spread) ± 95% CI", title="Closing spread bias by season")
    fig.tight_layout(); fig.savefig(FIGURES / "nfl_ats_error.png"); plt.close(fig)

    # Discrete residual vs normal: how much mass does the normal miss at key numbers?
    disc = pd.DataFrame({"k": range(0, 22)})
    disc["empirical"] = [float((absm == k).mean()) for k in disc.k]
    # Normal margin around each game's spread, folded to |margin|, integer-rounded.
    sim = np.concatenate([stats.norm.rvs(loc=lined.spread_line, scale=13.86, size=len(lined), random_state=s) for s in range(20)])
    sim_abs = np.abs(np.round(sim))
    disc["normal_13.86"] = [float((sim_abs == k).mean()) for k in disc.k]
    disc["ratio"] = (disc.empirical / disc["normal_13.86"]).round(2)
    disc.to_csv(DATA_PROCESSED / "nfl_eda_margin_vs_normal.csv", index=False)
    summary["key_number_ratio"] = {int(r.k): float(r.ratio) for r in disc.itertuples() if r.k in KEY_NUMBERS}

    # --- 3. Push probabilities at integer spreads -----------------------------------
    push = pd.DataFrame({"spread": KEY_NUMBERS + [1, 2, 5, 8, 9, 11, 13, 17, 21]}).sort_values("spread")
    push["p_land_exactly"] = [float((absm == k).mean()) for k in push.spread]
    push.to_csv(DATA_PROCESSED / "nfl_eda_push_probs.csv", index=False)

    # --- 4. Totals ---------------------------------------------------------------------
    tl = g.dropna(subset=["total_line"])
    summary["total_mean"] = round(float(g.total_pts.mean()), 2)
    summary["total_sd"] = round(float(g.total_pts.std()), 2)
    summary["total_error_mean"] = round(float(tl.total_error.mean()), 3)
    summary["total_error_sd"] = round(float(tl.total_error.std()), 3)
    tot_by_season = g.groupby("season").total_pts.agg(["mean", "std"]).round(2)
    tot_by_season.to_csv(DATA_PROCESSED / "nfl_eda_total_by_season.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    tf = g.total_pts.value_counts(normalize=True).sort_index()
    axes[0].bar(tf.index, tf.values, color="#55A868", width=0.8)
    axes[0].set(xlabel="total points", ylabel="share", title="Total points distribution", xlim=(0, 90))
    axes[1].hist(tl.total_error, bins=np.arange(-40.5, 41.5, 1), density=True, color="#55A868", alpha=0.8)
    x = np.linspace(-40, 40, 300)
    axes[1].plot(x, stats.norm.pdf(x, tl.total_error.mean(), tl.total_error.std()), "k--", lw=1.5,
                 label=f"N({tl.total_error.mean():.2f}, {tl.total_error.std():.2f}²)")
    axes[1].set(xlabel="total − closing total line", title="Total vs closing line"); axes[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "nfl_totals.png"); plt.close(fig)

    # --- 5. Joint structure: margin vs total, score grid ------------------------------
    summary["corr_margin_total"] = round(float(g[["margin", "total_pts"]].corr().iloc[0, 1]), 4)
    summary["corr_absmargin_total"] = round(float(np.corrcoef(absm, g.total_pts)[0, 1]), 4)
    summary["corr_ats_err_total_err"] = round(float(lined.dropna(subset=["total_line"])[["ats_error", "total_error"]].corr().iloc[0, 1]), 4)
    # Parity: margin and total always share parity, so half the (margin,total) grid is empty.
    summary["parity_check_same"] = float(((g.margin % 2) == (g.total_pts % 2)).mean())
    # Conditional spread of the margin given total: does a higher total widen the margin?
    q = pd.qcut(g.total_pts, 4)
    cond = g.groupby(q, observed=True).margin.agg(mean="mean", sd="std", abs_mean=lambda s: s.abs().mean()).round(2)
    cond.to_csv(DATA_PROCESSED / "nfl_eda_margin_given_total.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    grid = pd.crosstab(g.home_score.astype(int), g.away_score.astype(int))
    grid = grid.reindex(index=range(0, 61), columns=range(0, 61), fill_value=0)
    im = axes[0].imshow(np.log1p(grid.values), origin="lower", cmap="viridis")
    axes[0].plot([0, 60], [0, 60], "w--", lw=0.6)
    axes[0].set(xlabel="away score", ylabel="home score", title="Final score grid  p(h, a), log(1+count)")
    fig.colorbar(im, ax=axes[0], fraction=0.046)
    h = axes[1].hist2d(g.margin, g.total_pts, bins=[np.arange(-40.5, 41.5, 1), np.arange(-0.5, 90.5, 1)], cmap="magma")
    axes[1].set(xlabel="margin (home − away)", ylabel="total", title=f"Margin × total  (corr={summary['corr_margin_total']:.3f})")
    fig.tight_layout(); fig.savefig(FIGURES / "nfl_score_grid.png"); plt.close(fig)

    top = g.groupby(["home_score", "away_score"]).size().sort_values(ascending=False).head(15)
    top = (top / len(g)).rename("share").reset_index()
    top.to_csv(DATA_PROCESSED / "nfl_eda_top_scores.csv", index=False)

    # --- 6. How well does the closing moneyline predict the winner? ------------------------
    ml = g.dropna(subset=["home_moneyline", "away_moneyline"]).copy()
    def implied(m):
        return np.where(m < 0, -m / (-m + 100), 100 / (m + 100))
    ph, pa = implied(ml.home_moneyline.values), implied(ml.away_moneyline.values)
    ml["overround"] = ph + pa - 1
    ml["p_home_fair"] = ph / (ph + pa)
    ml["home_win"] = (ml.margin > 0).astype(float) + 0.5 * (ml.margin == 0)
    summary["sportsbook_overround_mean"] = round(float(ml.overround.mean()), 4)
    summary["sportsbook_brier"] = round(float(((ml.p_home_fair - ml.home_win) ** 2).mean()), 4)
    summary["sportsbook_logloss"] = round(float(-(ml.home_win * np.log(ml.p_home_fair) + (1 - ml.home_win) * np.log(1 - ml.p_home_fair)).mean()), 4)
    # Stern-normal win prob from the spread, for comparison.
    p_stern = stats.norm.cdf(ml.spread_line / 13.86)
    summary["stern_brier"] = round(float(((p_stern - ml.home_win) ** 2).mean()), 4)
    ml["bin"] = pd.cut(ml.p_home_fair, np.arange(0, 1.01, 0.1))
    cal = ml.groupby("bin", observed=True).agg(p_pred=("p_home_fair", "mean"), p_obs=("home_win", "mean"), n=("home_win", "size")).round(3)
    cal.to_csv(DATA_PROCESSED / "nfl_eda_moneyline_calibration.csv")
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.scatter(cal.p_pred, cal.p_obs, s=cal.n / 4, color="#4C72B0")
    ax.set(xlabel="de-vigged closing moneyline P(home)", ylabel="observed home win rate", title="Sportsbook closing line calibration")
    fig.tight_layout(); fig.savefig(FIGURES / "nfl_moneyline_calibration.png"); plt.close(fig)

    (DATA_PROCESSED / "nfl_eda_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(disc[disc.k.isin(KEY_NUMBERS + [1, 2, 5])].to_string(index=False))
    print(top.to_string(index=False))
    print(cond.to_string())


if __name__ == "__main__":
    main()
