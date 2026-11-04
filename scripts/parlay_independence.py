"""Are the legs of a cross-game parlay independent? Four tests, written up in reports/parlay_independence/README.md.

1. Correlation of residuals (outcome minus closing line) between games in the same week and the same kickoff slot,
   2015-2025, against a permutation null that shuffles games across weeks within a season.
2. Do upsets bunch? Variance of the weekly number of favourites that lose, against independent simulation.
3. Two-leg parlays scored against what happened: cross-game pairs (should multiply) and same-game pairs (should not,
   the positive control that shows the tests can see dependence when it is there).
4. Kalshi 2026: hit rate of real cross-game winner parlays against independent simulation of the games, with the
   closing probabilities and with probabilities refitted to how single games went; and how much correlation it
   would take to explain the gap.

Inputs: nflverse schedules, Kalshi markets and parlay legs (scripts/pull_kalshi.py, pull_kalshi_parlays.py), and
data/processed/parlay_markets.csv (scripts/parlay_analysis.py).
Outputs: reports/parlay_independence/{figures,results}/.
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, DATA_RAW, REPORTS
from pmrisk.independence import (copula_hit_ratio, devig, dispersion, dispersion_null, leg_matrices, pair_corr,
                                 pair_corr_null, parlay_hit_rates)
from pmrisk.link import link_to_schedule, parse_events
from pmrisk.nfl import KALSHI_TO_NFLVERSE, completed_games, load_schedules

OUT = REPORTS / "parlay_independence"
(OUT / "figures").mkdir(parents=True, exist_ok=True)
(OUT / "results").mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
N_PERM, N_SIM = 2000, 2000
summary = {}


def band(x):
    return [round(float(np.percentile(x, 2.5)), 4), round(float(np.percentile(x, 97.5)), 4)]


# ---- games and their closing probabilities ----------------------------------------------------------------------
sched = load_schedules()
g = completed_games(sched[sched.game_type == "REG"])
g = g[g.spread_line != 0].dropna(subset=["home_moneyline", "away_moneyline", "spread_line", "total_line"]).copy()
g["wk"] = g.season * 100 + g.week
g["slot"] = g.gameday.dt.strftime("%Y-%m-%d") + " " + g.gametime.fillna("")
g["p_home"] = devig(g.home_moneyline, g.away_moneyline)
fav_home = g.spread_line > 0  # favourite = the team the spread favours
g["p_win"] = np.where(fav_home, g.p_home, 1 - g.p_home)
g["win"] = np.where(g.margin == 0, np.nan, np.where(fav_home, g.margin > 0, g.margin < 0))
g["margin_res"] = np.where(fav_home, 1, -1) * (g.margin - g.spread_line)  # favourite's margin minus its spread
g["total_res"] = g.total_pts - g.total_line
p_home_cover = devig(g.home_spread_odds, g.away_spread_odds)
g["p_cover"] = np.where(fav_home, p_home_cover, 1 - p_home_cover)
g["cover"] = np.where(g.margin == g.spread_line, np.nan, np.where(fav_home, g.margin > g.spread_line, g.margin < g.spread_line))
g["p_over"] = devig(g.over_odds, g.under_odds)
g["over"] = np.where(g.total_pts == g.total_line, np.nan, g.total_pts > g.total_line)
hist = g[g.season.between(2015, 2025)].copy()
now = g[g.season == 2026].copy()
summary["sample"] = {"history_games": int(len(hist)), "history_weeks": int(hist.wk.nunique()),
                     "games_2026": int(len(now)), "weeks_2026": sorted(now.week.unique().tolist())}

# ---- 1. residual correlation between games ----------------------------------------------------------------------
corr_rows = []
h = hist.dropna(subset=["win"])
for col, lab in [("win", "favourite wins (1/0 minus its probability)"), ("margin_res", "favourite's margin minus spread"),
                 ("total_res", "total points minus total line")]:
    r = (h[col] - h.p_win).to_numpy() if col == "win" else h[col].to_numpy()
    for grp, glab in [("wk", "same week"), ("slot", "same kickoff slot")]:
        rho, npairs = pair_corr(r, h[grp].to_numpy())
        null = pair_corr_null(r, h[grp].to_numpy(), h.season.to_numpy(), N_PERM, seed=1)
        corr_rows.append({"residual": lab, "pairs": glab, "corr": round(rho, 4), "n_pairs": npairs,
                          "null_95_lo": band(null)[0], "null_95_hi": band(null)[1],
                          "p_value": round(float((np.abs(null) >= abs(rho)).mean()), 3)})
corr = pd.DataFrame(corr_rows)
# The same statistic within a game: correlation of two legs' residuals across games (the positive control).
s = hist.dropna(subset=["win", "cover", "over"])
res = {"win": s.win - s.p_win, "cover": s.cover - s.p_cover, "over": s.over - s.p_over}
within = pd.DataFrame([{"pair": lab, "corr": round(float(np.corrcoef(res[a], res[b])[0, 1]), 3), "n_games": len(s),
                        "se": round(1 / np.sqrt(len(s)), 3)}
                       for a, b, lab in [("win", "cover", "favourite wins & favourite covers"), ("win", "over", "favourite wins & over"),
                                         ("cover", "over", "favourite covers & over")]])
corr.to_csv(OUT / "results/cross_game_correlation.csv", index=False)
within.to_csv(OUT / "results/same_game_correlation.csv", index=False)
summary["cross_game_correlation"] = corr.to_dict(orient="records")
summary["same_game_correlation"] = within.to_dict(orient="records")

# ---- 2. do upsets bunch? ----------------------------------------------------------------------------------------
disp_rows, disp_sims = [], {}
hc, ho, nw = hist.dropna(subset=["cover"]), hist.dropna(subset=["over"]), now.dropna(subset=["win"])
for name, d, y, p in [("favourite loses, 2015-2025", h, 1 - h.win, 1 - h.p_win),
                      ("favourite fails to cover, 2015-2025", hc, 1 - hc.cover, 1 - hc.p_cover),
                      ("game goes over, 2015-2025", ho, ho.over, ho.p_over),
                      ("favourite loses, 2026", nw, 1 - nw.win, 1 - nw.p_win)]:
    y, p, wk = np.asarray(y, float), np.asarray(p, float), d.wk.to_numpy()
    null = dispersion_null(p, wk, N_SIM, seed=2)
    obs = dispersion(y, p, wk)
    disp_rows.append({"event": name, "weeks": int(len(np.unique(wk))), "dispersion": round(obs, 3),
                      "null_95_lo": band(null)[0], "null_95_hi": band(null)[1],
                      "p_value_bunching": round(float((null >= obs).mean()), 3)})
    disp_sims[name] = (y, p, wk)
disp = pd.DataFrame(disp_rows)
disp.to_csv(OUT / "results/weekly_dispersion.csv", index=False)
summary["weekly_dispersion"] = disp.to_dict(orient="records")

# ---- 3. two-leg parlays against what happened -------------------------------------------------------------------
WEEKS = np.sort(hist.wk.unique())


def cross_pairs(y, p):
    """Per week: sum over pairs of different games of y_i*y_j (hit both) and p_i*p_j (price), and the pair count."""
    d = pd.DataFrame({"wk": hist.wk, "y": y, "p": p}).dropna()
    a = d.assign(y2=d.y ** 2, p2=d.p ** 2).groupby("wk").agg(sy=("y", "sum"), sy2=("y2", "sum"), sp=("p", "sum"),
                                                              sp2=("p2", "sum"), n=("y", "size")).reindex(WEEKS, fill_value=0)
    return ((a.sy ** 2 - a.sy2) / 2).to_numpy(), ((a.sp ** 2 - a.sp2) / 2).to_numpy(), (a.n * (a.n - 1) / 2).to_numpy()


def same_pairs(y1, p1, y2, p2):
    """Per week: sum over games of y1*y2 (both legs hit) and p1*p2 (price as a product), and the game count."""
    d = pd.DataFrame({"wk": hist.wk, "y": y1 * y2, "p": p1 * p2}).dropna()
    a = d.groupby("wk").agg(y=("y", "sum"), p=("p", "sum"), n=("y", "size")).reindex(WEEKS, fill_value=0)
    return a.y.to_numpy(), a.p.to_numpy(), a.n.to_numpy().astype(float)


# Week bootstrap: games in a week share parlays, so whole weeks are resampled.
C = np.random.default_rng(6).multinomial(len(WEEKS), np.full(len(WEEKS), 1 / len(WEEKS)), size=2000)
parlay_rows = []
H = hist
specs = [("cross-game", "favourite A wins & favourite B wins", cross_pairs(H.win, H.p_win)),
         ("cross-game", "favourite A covers & favourite B covers", cross_pairs(H.cover, H.p_cover)),
         ("cross-game", "game A over & game B over", cross_pairs(H.over, H.p_over)),
         ("same-game", "favourite wins & favourite covers", same_pairs(H.win, H.p_win, H.cover, H.p_cover)),
         ("same-game", "favourite wins & over", same_pairs(H.win, H.p_win, H.over, H.p_over)),
         ("same-game", "favourite covers & over", same_pairs(H.cover, H.p_cover, H.over, H.p_over))]
for kind, lab, (hw, pw, nw_) in specs:
    hit, prod = hw.sum() / nw_.sum(), pw.sum() / nw_.sum()
    boot = 100 * (C @ hw - C @ pw) / (C @ nw_)
    parlay_rows.append({"type": kind, "parlay": lab, "n_parlays": int(nw_.sum()), "price_as_product_pct": round(100 * prod, 1),
                        "hit_rate_pct": round(100 * hit, 1), "gap_cents": round(100 * (hit - prod), 1),
                        "gap_95_lo": round(band(boot)[0], 1), "gap_95_hi": round(band(boot)[1], 1)})
parl = pd.DataFrame(parlay_rows)
parl.to_csv(OUT / "results/two_leg_parlays_2015_2025.csv", index=False)
summary["two_leg_parlays"] = parl.to_dict(orient="records")
# Single legs on their own: a cross-game gap that comes from here is mispricing of one leg, not dependence.
summary["single_legs_2015_2025"] = {lab: {"priced_pct": round(100 * float(H.loc[H[y].notna(), pc].mean()), 1),
                                          "hit_pct": round(100 * float(H[y].mean()), 1)}
                                    for lab, y, pc in [("favourite wins", "win", "p_win"), ("favourite covers", "cover", "p_cover"),
                                                       ("over", "over", "p_over")]}

# ---- 4. Kalshi 2026 cross-game winner parlays -------------------------------------------------------------------
markets = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")
ev = link_to_schedule(parse_events(markets), sched)
game_by_event = ev.dropna(subset=["game_id"]).set_index("event_ticker").game_id.to_dict()
pm = pd.read_csv(DATA_PROCESSED / "parlay_markets.csv", usecols=["ticker", "result", "created_time", "first_kickoff", "phase", "structure", "n_legs"])
pm = pm[pm.result.isin(["yes", "no"]) & (pm.phase == "REG") & (pm.structure == "cross-game")]
pm = pm[pd.to_datetime(pm.created_time, utc=True, format="ISO8601") < pd.to_datetime(pm.first_kickoff, utc=True, format="ISO8601")]
pl = pd.read_parquet(DATA_RAW / "kalshi_parlay_legs.parquet")
pl = pl[pl.ticker.isin(pm.ticker)].copy()
pl["game_id"] = pl.leg_event.map(game_by_event)
games26 = now.dropna(subset=["win"]).set_index("game_id")
team = pl.leg_market.str.rsplit("-", n=1).str[1].map(lambda t: KALSHI_TO_NFLVERSE.get(t, t))
pl["needs_home"] = (team.to_numpy() == pl.game_id.map(games26.home_team).to_numpy()) ^ (pl.side == "no").to_numpy()
ok = pl.game_id.isin(games26.index).groupby(pl.ticker).all()
pm = pm[pm.ticker.isin(ok[ok].index)].reset_index(drop=True)
pl = pl[pl.ticker.isin(pm.ticker)]
gidx = {gid: i for i, gid in enumerate(games26.index)}
pidx = pd.Series(np.arange(len(pm)), index=pm.ticker)
A_home, A_away = leg_matrices(pidx[pl.ticker].to_numpy(), pl.game_id.map(gidx).to_numpy(), pl.needs_home.to_numpy(), len(pm), len(gidx))
home_won = (games26.margin > 0).to_numpy().astype(float)
q = games26.p_home.to_numpy()
pm["hit"] = ((A_home @ (1 - home_won) + A_away @ home_won) == 0).astype(float)
pm["product"] = np.exp(A_home @ np.log(q) + A_away @ np.log(1 - q))
summary["kalshi_sample"] = {"parlays": int(len(pm)), "games": int(len(gidx)), "weeks_2026": sorted(now.week.unique().tolist()),
                            "agree_with_kalshi_settlement": round(float((pm.hit == (pm.result == "yes")).mean()), 4)}

# Refit the single-game probabilities to how 2026 games went: logit(q') = b * logit(q), b by maximum likelihood.
nll = lambda b: -np.sum(home_won * np.log(expit(b * logit(q))) + (1 - home_won) * np.log(1 - expit(b * logit(q))))
b_hat = float(minimize_scalar(nll, bounds=(0.2, 2.0), method="bounded").x)
q_refit = expit(b_hat * logit(q))
pm["product_refit"] = np.exp(A_home @ np.log(q_refit) + A_away @ np.log(1 - q_refit))
fav = np.where(q >= 0.5, q, 1 - q)
summary["refit"] = {"b": round(b_hat, 3), "favourites_priced": round(float(fav.mean()), 3),
                    "favourites_won": round(float(np.where(q >= 0.5, home_won, 1 - home_won).mean()), 3),
                    "favourites_refit": round(float(np.where(q >= 0.5, q_refit, 1 - q_refit).mean()), 3)}

edges = [(2, 2), (3, 3), (4, 4), (5, 6), (7, 8), (9, 12), (13, 99)]
lab_of = lambda n: next(f"{a}" if a == b else (f"{a}+" if b == 99 else f"{a}-{b}") for a, b in edges if a <= n <= b)
pm["bucket"] = pm.n_legs.map(lab_of)
order = [lab_of(a) for a, _ in edges]
sims = {k: pd.DataFrame(parlay_hit_rates(A_home, A_away, qq, pm.bucket.to_numpy(), n_sim=1000, seed=3), columns=sorted(order))[order]
        for k, qq in [("closing", q), ("refit", q_refit)]}
krows = []
for bkt in order:
    d = pm[pm.bucket == bkt]
    row = {"legs": bkt, "parlays": len(d), "hit_rate_pct": round(100 * d.hit.mean(), 2),
           "product_closing_pct": round(100 * d["product"].mean(), 2), "product_refit_pct": round(100 * d.product_refit.mean(), 2)}
    for k in sims:
        ratio = sims[k][bkt] / (d["product"] if k == "closing" else d.product_refit).mean()
        row[f"ratio_vs_{k}"] = round(d.hit.mean() / (d["product"] if k == "closing" else d.product_refit).mean(), 2)
        row[f"ratio_{k}_95_lo"], row[f"ratio_{k}_95_hi"] = [round(v, 2) for v in band(ratio)]
        row[f"p_low_{k}"] = round(float((ratio <= row[f"ratio_vs_{k}"]).mean()), 3)  # share of independent seasons this low
    krows.append(row)
kal = pd.DataFrame(krows)
kal.to_csv(OUT / "results/kalshi_2026_parlays.csv", index=False)
summary["kalshi_2026"] = kal.to_dict(orient="records")

# How much correlation between legs would it take? Gaussian copula, legs at the typical favourite price.
leg_p = np.where(pl.needs_home, pl.game_id.map(games26.p_home), 1 - pl.game_id.map(games26.p_home))
p_typ = round(float(np.median(leg_p)), 2)
curves = {}
for n in (2, 4, 8):
    lo = -1 / (n - 1) + 0.01
    pts = [copula_hit_ratio(p_typ, n, r, n_sim=200_000, seed=4) for r in np.linspace(max(lo, -0.3), 0.15, 19)]
    curves[n] = pd.DataFrame(pts, columns=["ratio", "rho"])
need = {}
for n, bkt in [(2, "2"), (4, "4"), (8, "7-8")]:
    c = curves[n].sort_values("rho")
    need[bkt] = round(float(np.interp(kal.set_index("legs").loc[bkt, "ratio_vs_closing"], c.ratio, c.rho)), 3)
summary["correlation_needed"] = {"typical_leg_probability": p_typ, "outcome_corr_needed_by_legs": need,
                                 "measured_same_week_corr": corr_rows[0]["corr"],
                                 # Interval for the true correlation: the measured value minus the null's spread.
                                 "measured_95_interval": [round(corr_rows[0]["corr"] - corr_rows[0]["null_95_hi"], 4),
                                                          round(corr_rows[0]["corr"] - corr_rows[0]["null_95_lo"], 4)]}

# ---- figures ----------------------------------------------------------------------------------------------------
# Figure 1: correlation across games (with the permutation band) next to correlation within a game.
fig, ax = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"width_ratios": [1.25, 1]})
y = np.arange(len(corr))[::-1]
ax[0].hlines(y, corr.null_95_lo, corr.null_95_hi, color="#BBBBBB", lw=6, label="95% range if games were independent")
ax[0].plot(corr["corr"], y, "o", color="#4C72B0", label="measured")
ax[0].axvline(0, color="k", lw=0.6)
ax[0].set_yticks(y, [f"{r.residual.split(' (')[0]}\n{r.pairs}" for r in corr.itertuples()], fontsize=7.5)
ax[0].set(xlim=(-0.06, 0.06), xlabel="correlation between two games", title="Across games, 2015-2025")
ax[0].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
y2 = np.arange(len(within))[::-1]
ax[1].hlines(y2, within["corr"] - 2 * within.se, within["corr"] + 2 * within.se, color="#DD8452", lw=6, alpha=0.4)
ax[1].plot(within["corr"], y2, "o", color="#DD8452")
ax[1].axvline(0, color="k", lw=0.6)
ax[1].set_yticks(y2, within.pair, fontsize=7.5)
ax[1].set(xlim=(-0.2, 1.0), xlabel="correlation between two legs", title="Within one game (positive control)")
fig.tight_layout()
fig.savefig(OUT / "figures/correlation.png")

# Figure 2: weekly number of upsets, observed against independent simulation.
y_, p_, wk_ = disp_sims["favourite loses, 2015-2025"]
codes = pd.factorize(wk_)[0]
obs_counts = np.bincount(codes, weights=y_)
rng = np.random.default_rng(5)
sim_counts = np.concatenate([np.bincount(codes, weights=(rng.random(len(p_)) < p_).astype(float)) for _ in range(500)])
fig, ax = plt.subplots(figsize=(6, 3.2))
bins = np.arange(-0.5, 12.5)
ax.hist(sim_counts, bins=bins, density=True, color="#BBBBBB", label="if games were independent (simulated)")
ax.hist(obs_counts, bins=bins, density=True, histtype="step", lw=2, color="#4C72B0", label="what happened")
r0 = disp.iloc[0]
ax.set(xlabel="favourites that lost in a week", ylabel="share of weeks",
       title=f"Upsets per week, 2015-2025 ({r0.weeks} weeks): dispersion {r0.dispersion:.2f}, independence range {r0.null_95_lo:.2f}-{r0.null_95_hi:.2f}")
ax.title.set_fontsize(8.5)
ax.legend(fontsize=7.5, frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "figures/weekly_upsets.png")

# Figure 3: Kalshi 2026 parlays against independence, and the correlation it would take.
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
x = np.arange(len(kal))
for k, col, off, lab in [("closing", "#4C72B0", -0.12, "legs at closing probability"), ("refit", "#55A868", 0.12, "legs refitted to 2026 single games")]:
    ax[0].vlines(x + off, kal[f"ratio_{k}_95_lo"], kal[f"ratio_{k}_95_hi"], color=col, lw=5, alpha=0.3)
    ax[0].plot(x + off, kal[f"ratio_vs_{k}"], "o", color=col, label=lab)
ax[0].axhline(1, color="k", lw=0.6)
ax[0].set_xticks(x, kal.legs)
ax[0].set(xlabel="legs in the parlay", ylabel="hit rate / product of legs",
          title="Kalshi winner parlays, 2026 (bars: 95% range if independent)")
ax[0].set_yscale("log")
ax[0].legend(fontsize=7.5, frameon=False, loc="lower left")
for n, col in zip(curves, ["#999999", "#666666", "#222222"]):
    c = curves[n]
    ax[1].plot(c.rho, c.ratio, color=col, label=f"{n} legs")
lo_b, hi_b = summary["correlation_needed"]["measured_95_interval"]
ax[1].axvspan(lo_b, hi_b, color="#4C72B0", alpha=0.2, label="measured, 2015-2025 (95%)")
for (n, bkt), col in zip([(2, "2"), (4, "4"), (8, "7-8")], ["#999999", "#666666", "#222222"]):
    ax[1].plot(need[bkt], kal.set_index("legs").loc[bkt, "ratio_vs_closing"], "o", mfc="white", mec=col, mew=1.5)
ax[1].plot([], [], "o", mfc="white", mec="k", label="2026 Kalshi result")
ax[1].axhline(1, color="k", lw=0.6)
ax[1].set(xlabel="correlation between two legs", ylabel="hit rate / product of legs", yscale="log",
          title=f"Correlation it would take (legs at {p_typ:.2f})")
ax[1].legend(fontsize=7.5, frameon=False)
fig.tight_layout()
fig.savefig(OUT / "figures/kalshi_2026.png")

(OUT / "results/summary.json").write_text(json.dumps(summary, indent=1, default=float))
print(json.dumps(summary, indent=1, default=float))
