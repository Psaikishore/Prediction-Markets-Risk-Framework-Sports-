"""Historical distribution of moneyline (match-winner) parlays, 2010-2025.

Every pair and triple of NFL games in the same week is a potential parlay. For each, the leg probabilities come
from (a) the de-vigged closing moneyline and (b) the forest's score grid, the parlay probability is their product,
and the outcome is whether every chosen side won. This gives, before touching Kalshi:
  1. how parlay probabilities are distributed for the combinations people buy (favourites, mixed, dogs);
  2. whether the product is calibrated: hit rate by bucket of product probability, by leg count, by side mix;
  3. the realised dependence: joint hit rate minus product, pooled and by favourite size;
  4. the payout distribution of a long parlay position: variance and skew by leg count.
Outputs: data/processed/parlay_ml_history_*.csv, parlay_ml_history.json, reports/figures/parlay_ml_history.png.
"""

import itertools
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, FIGURES

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
rng = np.random.default_rng(3)
out = {}

P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv")
P = P[P.season.between(2010, 2025) & P.market_p_home.notna() & P.rf_grid_p_win.notna()].copy()
P = P[P.margin != 0]  # a tie settles a winner parlay no on Kalshi; drop the 6 ties rather than model them
P["home_win"] = (P.margin > 0).astype(float)
out["n_games"] = int(len(P))

# Leg sources besides the closing line: the forest's grid probability raw, the same recalibrated walk-forward
# (isotonic fit on the out-of-sample predictions of earlier seasons only), and Elo, which uses results alone.
from sklearn.isotonic import IsotonicRegression
P["rf_cal"] = np.nan
for t in sorted(P.season.unique()):
    tr = P[P.season < t]
    if len(tr) < 500:
        continue
    iso = IsotonicRegression(y_min=0.01, y_max=0.99, out_of_bounds="clip").fit(tr.rf_grid_p_win, tr.home_win)
    P.loc[P.season == t, "rf_cal"] = iso.predict(P.loc[P.season == t, "rf_grid_p_win"])
P = P[P.rf_cal.notna()].copy()
out["n_games_with_calibrated_model"] = int(len(P)); out["seasons"] = [int(P.season.min()), int(P.season.max())]
SOURCES = {"p_market": "market_p_home", "p_model": "rf_grid_p_win", "p_model_cal": "rf_cal", "p_elo": "elo_p_home"}


def legs_table(df: pd.DataFrame, n_legs: int, max_per_week: int | None) -> pd.DataFrame:
    """All n-leg combinations of games in a week, each with every side choice, as one row per parlay.

    Sides: for every game in the combination, home or away. With n legs that is 2^n parlays per combination.
    """
    rows = []
    cols = list(SOURCES.values())
    for (season, week), g in df.groupby(["season", "week"]):
        probs = g[cols].to_numpy(); wins = g.home_win.to_numpy()
        combos = list(itertools.combinations(range(len(g)), n_legs))
        if max_per_week is not None and len(combos) > max_per_week:
            combos = [combos[i] for i in rng.choice(len(combos), max_per_week, replace=False)]
        for c in combos:
            pr, w = probs[list(c)], wins[list(c)]
            for sides in itertools.product((1, 0), repeat=n_legs):  # 1 = home side
                h = np.array(sides, dtype=float)
                leg_p = pr * h[:, None] + (1 - pr) * (1 - h[:, None])  # probability of the chosen side, per source
                prods = leg_p.prod(axis=0)
                hit = float(np.all(w == h))
                n_fav = int((leg_p[:, 0] > 0.5).sum())
                rows.append((season, week, n_legs, *prods, hit, n_fav))
    return pd.DataFrame(rows, columns=["season", "week", "n_legs", *SOURCES, "hit", "n_favourites"])


T2 = legs_table(P, 2, None)
T3 = legs_table(P, 3, 300)
T4 = legs_table(P, 4, 150)
T = pd.concat([T2, T3, T4], ignore_index=True)
T.to_parquet(DATA_PROCESSED / "parlay_ml_history_parlays.parquet", index=False)


def brier(p, y):
    return float(((p - y) ** 2).mean())


def summarise(d: pd.DataFrame, col: str) -> dict:
    base = d.hit.mean()
    return {"n": int(len(d)), "hit_rate": round(float(d.hit.mean()), 4), "mean_p": round(float(d[col].mean()), 4),
            "hit_minus_p_cents": round(100 * float((d.hit - d[col]).mean()), 2),
            "se_cents": round(100 * float(d.hit.std() / np.sqrt(len(d))), 2),
            "brier": round(brier(d[col], d.hit), 4), "brier_base_rate": round(float(((base - d.hit) ** 2).mean()), 4),
            "slope": round(float(np.polyfit(d[col], d.hit, 1)[0]), 3) if d[col].std() > 0 else None}


# ---- 1-2. calibration of the product, by legs, side mix and bucket -----------------------------------------------
res = {"by_legs": {}, "by_favourites_2leg": {}, "by_bucket_2leg": {}}
for n, d in T.groupby("n_legs"):
    res["by_legs"][int(n)] = {src: summarise(d, src) for src in SOURCES}
for k, d in T2.groupby("n_favourites"):
    res["by_favourites_2leg"][f"{int(k)} favourites"] = {src: summarise(d, src) for src in SOURCES}
bins = [0, .05, .1, .15, .2, .3, .4, .5, .6, 1]
for col in SOURCES:
    g = T2.groupby(pd.cut(T2[col], bins), observed=True).agg(n=("hit", "size"), mean_p=(col, "mean"), hit=("hit", "mean")).round(4)
    res["by_bucket_2leg"][col] = {str(k): v for k, v in g.to_dict(orient="index").items()}
    g.to_csv(DATA_PROCESSED / f"parlay_ml_history_reliability_{col}.csv")
out["calibration"] = res

# ---- 3. hit rate minus product by bucket, and dependence for a fixed side choice ---------------------------------
# Over all 2^n side choices of a combination the products sum to one and exactly one parlay hits, so the pooled
# hit rate equals the pooled product by construction; what is informative is the split by bucket (leg-level
# favourite-longshot bias compounding) and the dependence test for a fixed side choice (both favourites).
dep = {}
sel = T2.copy()
sel["fav_bucket"] = pd.cut(sel.p_market, [0, .1, .2, .3, .4, .5, 1])
g = sel.groupby("fav_bucket", observed=True).agg(n=("hit", "size"), hit=("hit", "mean"), p=("p_market", "mean"))
g["hit_minus_p_cents"] = 100 * (g.hit - g.p)
dep["by_product_bucket"] = {str(k): v for k, v in g.round(4).to_dict(orient="index").items()}


def clustered(d, col):
    """Mean of hit - p with a season-clustered standard error (parlays in a season share games)."""
    x = d.hit - d[col]
    per = pd.DataFrame({"d": x, "season": d.season}).groupby("season").d.agg(["sum", "size"])
    u = per["sum"] - x.mean() * per["size"]
    return {"n": int(len(d)), "hit_minus_p_cents": round(100 * float(x.mean()), 3),
            "se_cents": round(100 * float(np.sqrt((u ** 2).sum()) / len(d) * np.sqrt(len(per) / (len(per) - 1))), 3)}


both_fav = T2[T2.n_favourites == 2]
for src in SOURCES:
    dep[f"both_favourites_{src}"] = clustered(both_fav, src)
    dep[f"both_dogs_{src}"] = clustered(T2[T2.n_favourites == 0], src)
out["dependence"] = dep

# ---- 4. payout distribution of a long parlay by leg count -----------------------------------------------------------
pay = {}
for n, d in T.groupby("n_legs"):
    # $1 of parlay bought at the market product: P&L = (hit - p)/p per dollar
    r = (d.hit - d.p_market) / d.p_market
    pay[int(n)] = {"mean_return": round(float(r.mean()), 4), "sd_return": round(float(r.std()), 3), "skew": round(float(r.skew()), 2),
                   "p_loss": round(float((d.hit == 0).mean()), 4), "median_p": round(float(d.p_market.median()), 4)}
out["payout_by_legs"] = pay

# ---- what people buy: favourites-only parlays ----------------------------------------------------------------------
fav = T[T.n_favourites == T.n_legs]
out["favourites_only"] = {int(n): summarise(d, "p_market") for n, d in fav.groupby("n_legs")}

# ---- figure -----------------------------------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for col, c, lab in [("p_market", "#DD8452", "closing moneyline, de-vigged"), ("p_model", "#4C72B0", "score grid (forest), raw"), ("p_model_cal", "#55A868", "score grid, recalibrated"), ("p_elo", "#8172B2", "Elo (results only)")]:
    g = T2.groupby(pd.cut(T2[col], bins), observed=True).agg(n=("hit", "size"), mean_p=(col, "mean"), hit=("hit", "mean"))
    axes[0].errorbar(g.mean_p, g.hit, yerr=np.sqrt(g.hit * (1 - g.hit) / g.n), fmt="o-", ms=3, color=c, label=lab)
axes[0].plot([0, 0.7], [0, 0.7], "k--", lw=0.8); axes[0].set(xlabel="product of leg probabilities", ylabel="share of 2-leg parlays that hit", title="2-leg ML parlays: product vs realised, 2010-2025"); axes[0].legend(fontsize=7)
for n, c in [(2, "#DD8452"), (3, "#55A868"), (4, "#8172B2")]:
    d = T[T.n_legs == n]
    axes[1].hist(d.p_market, bins=40, range=(0, 0.6), density=True, histtype="step", color=c, label=f"{n} legs (fav-only median {fav[fav.n_legs == n].p_market.median():.2f})")
axes[1].set(xlabel="parlay probability (product of de-vigged legs)", ylabel="density", title="Distribution of ML parlay probabilities"); axes[1].legend(fontsize=7)
gg = pd.DataFrame(dep["by_product_bucket"]).T
axes[2].bar(range(len(gg)), gg.hit_minus_p_cents, color="#4C72B0")
axes[2].axhline(0, color="k", lw=0.8); axes[2].set_xticks(range(len(gg)), gg.index, rotation=30, fontsize=7)
axes[2].set(xlabel="product probability bucket", ylabel="hit rate − product, cents", title="Hit rate − product by bucket (leg bias compounding)")
fig.tight_layout(); fig.savefig(FIGURES / "parlay_ml_history.png"); plt.close(fig)

json.dump(out, open(DATA_PROCESSED / "parlay_ml_history.json", "w"), indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
