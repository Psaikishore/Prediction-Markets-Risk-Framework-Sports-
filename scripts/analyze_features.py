"""Analysis of data/processed/features/games_features.parquet. Re-run after every rebuild of the table.

A. Integrity: identities, ranges, leakage screen, what unplayed games really contain.
B. Coverage: non-null share by feature group and season; what unplayed games have by week.
C. Signal: within-season rank correlation with margin and total, and with both net of the closing line.
D. Redundancy: clusters of near-duplicate features, variance spectrum, windows compared.
E. Drift: which features' levels move across seasons, 1999-2025.
F. Value: walk-forward ridge on each feature group alone and removed, 2010-2025, paired and clustered.

Outputs: data/processed/features_analysis_*.csv, features_analysis_summary.json, reports/figures/features_*.png,
reports/features_analysis.md (generated; do not edit by hand). Library: src/pmrisk/features/analysis.py.
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, FIGURES, REPORTS
from pmrisk.features.analysis import (DICTIONARY, ENCODING_FOR, GROUPS, coverage_by_season, describe_features, drift_table,
                                      features_for, forecast_coverage, group_value, integrity_checks, load_table, matchup_view,
                                      played, redundancy, signal_table, target_frame, window_matrix)

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
C = {"a": "#4C72B0", "b": "#DD8452", "ref": "#555555", "grid": "#E5E5E5"}
TEST_SEASONS = list(range(2010, 2026))
TITLES = {"margin": "Margin", "margin_vs_spread": "Margin net of the closing spread", "total_pts": "Total", "total_vs_line": "Total net of the closing total"}


def out(df, name, **kw):
    df.to_csv(DATA_PROCESSED / f"features_analysis_{name}.csv", **kw)


def md_table(df, fmt="{:.3f}"):
    def cell(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else fmt.format(v)
        return "" if v is None else str(v).replace("|", "\\|")
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    return "\n".join(lines + ["| " + " | ".join(cell(v) for v in r) + " |" for r in df.itertuples(index=False)])


def heatmap(ax, m, vmax=None, fmt="{:.0%}", fontsize=7):
    im = ax.imshow(m.values, aspect="auto", cmap="Blues", vmin=0, vmax=vmax if vmax is not None else np.nanmax(m.values))
    ax.set_xticks(range(m.shape[1]), m.columns); ax.set_yticks(range(m.shape[0]), m.index)
    ax.spines[:].set_visible(False); ax.tick_params(length=0)
    limit = im.norm.vmin + 0.6 * (im.norm.vmax - im.norm.vmin)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=fontsize, color="white" if v > limit else "#222222")
    return im


def fig_coverage(by_group):
    fig, ax = plt.subplots(figsize=(13, 2.8))
    heatmap(ax, by_group, vmax=1, fmt="{:.0%}", fontsize=6)
    ax.tick_params(axis="x", rotation=90)
    ax.set_title("Non-null share of each feature group by season (played games)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIGURES / "features_coverage.png"); plt.close(fig)


def fig_forecast(fc):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    heatmap(ax, fc, vmax=1, fontsize=7)
    ax.tick_params(axis="x", rotation=30)
    ax.set(ylabel="week")
    ax.set_title("Non-null share on unplayed 2026 games by week", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIGURES / "features_forecast_coverage.png"); plt.close(fig)


def fig_signal(signals, k=12):
    lim = 1.1 * max((s.head(k).rho_mean.abs() + 1.96 * s.head(k).rho_se).max() for s in signals.values())
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5), sharex=True)
    for ax, (target, s) in zip(axes.ravel(), signals.items()):
        top = s.head(k).iloc[::-1]
        ax.errorbar(top.rho_mean, range(len(top)), xerr=1.96 * top.rho_se, fmt="o", ms=5, color=C["a"], ecolor=C["a"], elinewidth=1.2)
        ax.axvline(0, color=C["ref"], lw=0.8)
        ax.set_yticks(range(len(top)), top.index, fontsize=7.5)
        ax.set_title(f"{TITLES[target]}: {int((s.q < 0.05).sum())} of {len(s)} pass q < 5%", loc="left", fontsize=10)
        ax.set_xlim(-lim, lim); ax.grid(axis="x", color=C["grid"], lw=0.6); ax.set_axisbelow(True); ax.tick_params(labelbottom=True)
    for ax in axes[1]:
        ax.set_xlabel("mean within-season Spearman ρ, ±1.96 SE across seasons", fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "features_signal.png"); plt.close(fig)


def fig_windows(mats):
    fig, axes = plt.subplots(1, 2, figsize=(11, 10))
    vmax = max(np.nanmax(m.values) for m in mats.values())
    for ax, (target, m) in zip(axes, mats.items()):
        heatmap(ax, m, vmax=vmax, fmt="{:.2f}", fontsize=6.5)
        ax.tick_params(axis="y", labelsize=7); ax.xaxis.tick_top()
        ax.set_title(f"|ρ| with {TITLES[target].lower()}", loc="left", fontsize=10, pad=18)
    fig.tight_layout(); fig.savefig(FIGURES / "features_windows.png"); plt.close(fig)


def fig_redundancy(spectra):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    styles = {"diff": (C["a"], "-", "o"), "avg": (C["b"], "--", "s")}
    for enc, cum in spectra.items():
        color, ls, mk = styles[enc]
        n90 = int(np.searchsorted(cum, 0.9) + 1)
        ax.plot(np.arange(1, len(cum) + 1), cum, color=color, ls=ls, lw=2, label=f"{enc}_* and unsided features")
        ax.plot(n90, cum[n90 - 1], mk, color=color, ms=8)
        ax.annotate(f"{n90} components reach 90%", (n90, cum[n90 - 1]), xytext=(8, -16) if enc == "diff" else (-8, 9), textcoords="offset points", ha="left" if enc == "diff" else "right", fontsize=8, color="#222222")
    ax.axhline(0.9, color=C["ref"], lw=0.8)
    ax.set(xlim=(1, 120), ylim=(0, 1.01), xlabel="principal components", ylabel="cumulative share of variance")
    ax.grid(axis="y", color=C["grid"], lw=0.6); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("Effective dimension of the feature table, 2013+", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIGURES / "features_redundancy.png"); plt.close(fig)


def fig_drift(drift, means, k=6):
    # Season-to-date league averages, one window per statistic, so the panels are six different things.
    d = describe_features(drift.index)
    pick = drift[(d.encoding == "avg") & (d.window == "std")].head(k)
    fig, axes = plt.subplots(2, 3, figsize=(11, 5), sharex=True)
    for ax, name in zip(axes.ravel(), pick.index):
        s = means.loc[name].dropna()
        ax.plot(s.index, s.values, color=C["a"], lw=2)
        ax.set_title(f"{name[len('avg_std_'):]}: {pick.shift_sd[name]:+.1f} SD", loc="left", fontsize=9)
        ax.grid(axis="y", color=C["grid"], lw=0.6); ax.set_axisbelow(True)
    fig.suptitle("Largest level shifts: league-mean season-to-date form by season", x=0.01, ha="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIGURES / "features_drift.png"); plt.close(fig)


def fig_value(value):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, (target, v) in zip(axes, value.groupby("target", sort=False)):
        v = v.set_index("model")
        y = np.arange(len(GROUPS))[::-1]
        ax.plot([v.mae[f"{g} only"] for g in GROUPS], y, "o", ms=7, color=C["a"], label="group alone", ls="")
        ax.plot([v.mae[f"all minus {g}"] for g in GROUPS], y, "s", ms=7, color=C["b"], label="all but this group", ls="")
        ax.set_yticks(y, GROUPS)
        top = len(GROUPS) - 0.45
        for name, ls in [("all groups", "-"), ("closing line", "--"), ("league average", ":")]:
            ax.axvline(v.mae[name], color=C["ref"], lw=1, ls=ls)
            ax.text(v.mae[name], top, f"{name}\n{v.mae[name]:.2f}", fontsize=7, ha="center", va="bottom", color="#222222", bbox=dict(fc="white", ec="none", pad=1))
        ax.margins(x=0.09); ax.set_ylim(-0.6, len(GROUPS) + 0.1); ax.set_xlabel("walk-forward MAE, points, 2010–2025", fontsize=8)
        ax.grid(axis="x", color=C["grid"], lw=0.6); ax.set_axisbelow(True)
        ax.set_title(TITLES[target], loc="left", fontsize=10, pad=14); ax.legend(frameon=False, fontsize=7.5, loc="center right")
    fig.tight_layout(); fig.savefig(FIGURES / "features_group_value.png"); plt.close(fig)


def write_report(s, checks, signals, clusters, windows, drift, value):
    L = ["# Analysis of the pre-game feature table", "",
         f"*Generated by `scripts/analyze_features.py`; do not edit by hand. {s['games']:,} games ({s['played']:,} played, {s['unplayed']} unplayed), "
         f"{s['columns']} columns, {s['first_season']}–{s['last_season']}. Analysed as {s['view_features']} matchup features: `diff_x` and `avg_x` for each home/away pair, plus unsided ones.*", ""]

    L += ["## A. Integrity", "", f"{s['checks']['pass']} of {len(checks)} checks pass; warnings: {s['checks']['warn']}, failures: {s['checks']['fail']}.", ""]
    flagged = checks[checks.status != "pass"]
    L += [md_table(flagged[["status", "check", "n_bad", "detail"]]) if len(flagged) else "Nothing flagged.", ""]
    L += ["Checks passed: " + "; ".join(checks.check[checks.status == "pass"]) + ".", ""]

    L += ["## B. Coverage", "", "![coverage](figures/features_coverage.png)", "", "Unplayed games, by week:", "",
          "![forecast coverage](figures/features_forecast_coverage.png)", "",
          "A window is computed over a team's row sequence, including unplayed rows, so `l4` and `l8` empty out as the horizon grows. `ewm`, `std` and `prev` hold the last known value. "
          "`injury report` counts games with at least one non-zero count, because an absent report is stored as zeros.", ""]

    L += ["## C. Signal", "", "Mean within-season Spearman ρ, t across seasons, Benjamini-Hochberg q across the features tested. Margin targets use `diff_*`, total targets `avg_*`; unsided features enter both. "
          "Net-of-line targets ask whether a feature knows something the close does not; there are no costs here and a correlation is not a bet.", "",
          "![signal](figures/features_signal.png)", ""]
    for target, t in signals.items():
        top = t.head(8).reset_index()[["feature", "n_seasons", "rho_mean", "rho_se", "t", "q", "same_sign", "rho_early", "rho_late"]]
        L += [f"**{TITLES[target]}**: {int((t.q < 0.05).sum())} of {len(t)} features pass q < 5%.", "", md_table(top), ""]

    L += ["## D. Redundancy", ""]
    for enc, r in s["redundancy"].items():
        L += [f"* `{enc}_*` and unsided, 2013+: {r['features']} features fall into {r['clusters']} clusters at |r| ≥ 0.8; {r['components_90']} principal components reach 90% of variance, {r['components_95']} reach 95%."]
    big = clusters["diff"][clusters["diff"].representative].sort_values("cluster_size", ascending=False).head(10).reset_index()[["feature", "cluster_size", "rho"]]
    L += ["", "![redundancy](figures/features_redundancy.png)", "", "Largest `diff_*` clusters, named by the member most correlated with the margin:", "", md_table(big),
          "", "Full list, with a representative per cluster: `data/processed/features_analysis_clusters_{diff,avg}.csv`.", "", "Windows compared:", "", "![windows](figures/features_windows.png)", ""]
    best = {t: m.idxmax(axis=1).value_counts().to_dict() for t, m in windows.items()}
    L += ["Strongest window per statistic: " + "; ".join(f"{TITLES[t].lower()}: " + ", ".join(f"{k} {v}" for k, v in b.items()) for t, b in best.items()) + ".", ""]

    L += ["## E. Drift", "", "![drift](figures/features_drift.png)", "", "`diff_*` is close to level-free by construction; level shifts land in `avg_*`, and so in the total. A model fitted on old seasons inherits them.", "",
          md_table(drift.head(10).reset_index()[["feature", "eta2", "first_mean", "last_mean", "shift_sd"]]), ""]

    L += ["## F. Value of each group", "", "Ridge as in `scripts/baseline_models.py`, trained on seasons < t from 2000, tested on t in 2010–2025. `diff_vs_all` > 0 means the model errs by more than all-groups. "
          "Standard errors are of the paired difference, clustered by week and by season.", "", "![value](figures/features_group_value.png)", ""]
    for target, v in value.groupby("target", sort=False):
        L += [f"**{TITLES[target]}** ({v.n.iloc[0]:,} games)", "", md_table(v[["model", "mae", "diff_vs_all", "se_week", "se_season", "t_week"]]), ""]
    (REPORTS / "features_analysis.md").write_text("\n".join(L))


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    g = load_table()
    p = played(g)
    X = matchup_view(g)
    Xp, targets = X.loc[p.index], target_frame(p)
    info = describe_features(X.columns)
    summary = {"games": len(g), "played": len(p), "unplayed": len(g) - len(p), "columns": g.shape[1], "first_season": int(g.season.min()),
               "last_season": int(g.season.max()), "view_features": X.shape[1]}

    # --- A. integrity ---------------------------------------------------------------------------------------------
    checks = integrity_checks(g, pd.read_csv(DICTIONARY))
    out(checks, "integrity", index=False)
    summary["checks"] = {k: int((checks.status == k).sum()) for k in ("pass", "warn", "fail")}
    print(checks[checks.status != "pass"][["status", "check", "n_bad", "detail"]].to_string(index=False))

    # --- B. coverage ----------------------------------------------------------------------------------------------
    cov = coverage_by_season(Xp, p.season)
    out(cov, "coverage")
    by_group = cov.groupby(info.group).mean().reindex(list(GROUPS))
    fig_coverage(by_group)
    fc = forecast_coverage(g)
    out(fc, "forecast_coverage")
    fig_forecast(fc)

    # --- C. signal ------------------------------------------------------------------------------------------------
    signals = {}
    for target in ENCODING_FOR:
        s = signal_table(Xp[features_for(X.columns, target)], targets[target], p.season)
        signals[target] = s
        out(s, f"signal_{target}")
        print(f"{target}: {int((s.q < 0.05).sum())}/{len(s)} at q<5%, top {s.index[0]} rho {s.rho_mean.iloc[0]:+.3f} t {s.t.iloc[0]:.1f}")
    fig_signal(signals)
    summary["signal"] = {t: {"tested": len(s), "q_below_5pct": int((s.q < 0.05).sum()), "top": s.index[0], "top_rho": round(float(s.rho_mean.iloc[0]), 4)} for t, s in signals.items()}

    # --- D. redundancy --------------------------------------------------------------------------------------------
    recent = p.season >= 2013
    clusters, spectra = {}, {}
    summary["redundancy"] = {}
    for enc, target in [("diff", "margin"), ("avg", "total_pts")]:
        names = features_for(X.columns, target)
        clusters[enc], spectra[enc] = redundancy(Xp.loc[recent, names], signals[target].rho_mean)
        out(clusters[enc], f"clusters_{enc}")
        summary["redundancy"][enc] = {"features": len(clusters[enc]), "clusters": int(clusters[enc].cluster.nunique()),
                                      "components_90": int(np.searchsorted(spectra[enc], 0.9) + 1), "components_95": int(np.searchsorted(spectra[enc], 0.95) + 1)}
    fig_redundancy(spectra)
    windows = {t: window_matrix(signals[t]) for t in ("margin", "total_pts")}
    for t, m in windows.items():
        out(m, f"windows_{t}")
    fig_windows(windows)

    # --- E. drift, complete seasons only --------------------------------------------------------------------------
    full = p.season <= 2025
    drift, means = drift_table(Xp[full], p.season[full])
    out(drift, "drift"); out(means, "season_means")
    fig_drift(drift, means)

    # --- F. value of each group -----------------------------------------------------------------------------------
    value = pd.concat([group_value(Xp, p, "margin", "spread_line", TEST_SEASONS), group_value(Xp, p, "total_pts", "total_line", TEST_SEASONS)], ignore_index=True)
    out(value, "group_value", index=False)
    fig_value(value)
    print(value[["target", "model", "mae", "diff_vs_all", "se_week", "se_season"]].round(3).to_string(index=False))

    write_report(summary, checks, signals, clusters, windows, drift, value)
    (DATA_PROCESSED / "features_analysis_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
