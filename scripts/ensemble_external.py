"""Ensemble test: do our models, or external public forecasts, add anything beyond the closing line?

Components (all pre-game, home-margin convention, positive = home favoured):
  rf, ridge, elo          our walk-forward out-of-sample predictions (model_rf_predictions.csv)
  nfelo                   greerreNFL nfelo model line before market regression (nfelo_home_line_open)
  fte                     FiveThirtyEight Elo win probability converted to a spread (to 2020)
  open_line, close_line   sportsbook opening line (from the nfelo file) and closing line (nflverse)
Stacking weights are fit by least squares on earlier seasons' out-of-sample predictions, tested on season t.
"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pmrisk import DATA_PROCESSED, DATA_RAW, FIGURES
from pmrisk.features import franchise
from pmrisk.nfl import nfelo_game_id
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
EXT = DATA_RAW / "external"

P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv")
n = pd.read_csv(EXT / "nfelo_games.csv", index_col=0)
n["game_id"] = n.game_id.map(nfelo_game_id)  # nfelo writes OAK/LAR in every season
# nfelo publishes three variants: dif_base (pure rating difference incl. home field and QB/bye mods),
# "open" (regressed toward the market opening line) and "close" (regressed toward the closing line).
# Only the base variant is a model that has not seen the market. Their elo-to-points ratio:
ratio = (-n.nfelo_home_line_open / n.nfelo_dif_open).replace([np.inf, -np.inf], np.nan).median()
n["nfelo"] = n.nfelo_dif_base * ratio; n["nfelo_mkt"] = -n.nfelo_home_line_open; n["nfelo_close"] = -n.nfelo_home_line_close
print(f"nfelo points per rating point {ratio:.4f}")
n["open_line"] = -n.home_line_open; n["open_total"] = n.total_line_open
P = P.merge(n[["game_id", "nfelo", "nfelo_mkt", "nfelo_close", "open_line", "open_total", "home_538_qb_adj", "away_538_qb_adj"]], on="game_id", how="left")
f = pd.read_csv(EXT / "fte_nfl_games.csv"); f = f[f.season >= 2009].copy()
f["home_team"] = f.team1.map(franchise); f["gameday"] = pd.to_datetime(f.date)
f["fte"] = 400 * np.log10(f.elo_prob1 / (1 - f.elo_prob1)) / 25
sched = pd.read_parquet(DATA_RAW / "nflverse_schedules.parquet")[["game_id", "gameday"]]
sched = pd.read_parquet(DATA_PROCESSED / "features" / "games_features.parquet")[["game_id", "gameday", "home_team"]]
sched["gameday"] = pd.to_datetime(sched.gameday)
fm = sched.merge(f[["gameday", "home_team", "fte"]], on=["gameday", "home_team"], how="inner")
P = P.merge(fm[["game_id", "fte"]], on="game_id", how="left")
P["close_line"] = P.spread_line
print("coverage:", {c: int(P[c].notna().sum()) for c in ["rf_margin", "nfelo", "fte", "open_line", "close_line"]})

def mae(a, b): return float((a - b).abs().mean())
def walk(cols, data, target, start=2013, end=2025):
    rows, weights = [], []
    for t in range(start, end + 1):
        tr, te = data[(data.season < t) & (data.season >= 2010)], data[data.season == t]
        tr, te = tr.dropna(subset=cols + [target]), te.dropna(subset=cols + [target])
        if len(tr) < 200 or len(te) == 0: continue
        m = LinearRegression().fit(tr[cols], tr[target])
        rows.append((t, mae(m.predict(te[cols]), te[target]), len(te))); weights.append(m.coef_)
    r = pd.DataFrame(rows, columns=["season", "mae", "n"])
    return float(np.average(r.mae, weights=r.n)), np.round(np.mean(weights, axis=0), 2), f"{r.season.min()}-{r.season.max()}"

results = {}
base = P[P.season.between(2013, 2025)]
for name, cols in {
    "rf": ["rf_margin"], "ridge": ["ridge_margin"], "elo": ["elo_spread"], "nfelo": ["nfelo"], "fte_538": ["fte"],
    "nfelo_market_regressed": ["nfelo_mkt"], "open_line": ["open_line"], "close_line": ["close_line"],
    "stack: rf+ridge+elo": ["rf_margin", "ridge_margin", "elo_spread"],
    "stack: rf+ridge+elo+nfelo": ["rf_margin", "ridge_margin", "elo_spread", "nfelo"],
    "stack: rf+ridge+elo+nfelo+fte (to 2020)": ["rf_margin", "ridge_margin", "elo_spread", "nfelo", "fte"],
    "stack: ours+nfelo+open_line": ["rf_margin", "ridge_margin", "elo_spread", "nfelo", "open_line"],
    "stack: ours+nfelo+close_line": ["rf_margin", "ridge_margin", "elo_spread", "nfelo", "close_line"],
    "stack: open_line+close_line": ["open_line", "close_line"],
    "stack: everything": ["rf_margin", "ridge_margin", "elo_spread", "nfelo", "open_line", "close_line"],
}.items():
    m, w, span = walk(cols, P, "margin")
    results[name] = {"mae": round(m, 3), "weights": dict(zip(cols, w.tolist())), "seasons": span}
    print(f"{name:<42} MAE {m:.3f}  {span}  weights {dict(zip(cols, w.tolist()))}")

# single-model MAE on the common sample for a fair table (2013-2025, nfelo available everywhere)
common = base.dropna(subset=["rf_margin", "nfelo", "open_line", "close_line"])
single = {k: round(mae(common[c], common.margin), 3) for k, c in [("rf", "rf_margin"), ("ridge", "ridge_margin"), ("elo", "elo_spread"), ("nfelo", "nfelo"), ("open_line", "open_line"), ("close_line", "close_line")]}
single["nfelo_market_regressed"] = round(mae(common.nfelo_mkt, common.margin), 3)
single["simple avg rf+ridge+elo+nfelo"] = round(mae(common[["rf_margin", "ridge_margin", "elo_spread", "nfelo"]].mean(axis=1), common.margin), 3)
single["n_games"] = int(len(common))
print("\nsingle components on common sample:", single)
# totals
tot = {}
for name, cols in {"rf": ["rf_total"], "ridge": ["ridge_total"], "open_total": ["open_total"], "close_total": ["total_line"],
                   "stack: rf+ridge+open": ["rf_total", "ridge_total", "open_total"], "stack: rf+ridge+close": ["rf_total", "ridge_total", "total_line"]}.items():
    m, w, span = walk(cols, P, "total_pts"); tot[name] = {"mae": round(m, 3), "weights": dict(zip(cols, w.tolist()))}
    print(f"total {name:<30} MAE {m:.3f} weights {dict(zip(cols, w.tolist()))}")
# correlations
corr = common[["rf_margin", "ridge_margin", "elo_spread", "nfelo", "nfelo_mkt", "open_line", "close_line", "margin"]].corr().round(3)
corr.to_csv(DATA_PROCESSED / "ensemble_corr.csv")
json.dump({"margin": results, "margin_single_common": single, "total": tot}, open(DATA_PROCESSED / "ensemble_results.json", "w"), indent=2)

# figure: MAE bars + stacking weights
fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
names = ["rf", "ridge", "elo", "nfelo", "simple avg rf+ridge+elo+nfelo", "nfelo_market_regressed", "open_line", "close_line"]
vals = [single[k] for k in names]; cols_ = ["#4C72B0", "#55A868", "#8172B2", "#64B5CD", "#937860", "#8C8C8C", "#F0B05A", "#DD8452"]
axes[0].barh(names[::-1], vals[::-1], color=cols_[::-1]); axes[0].set(xlim=(9.5, 10.6), xlabel="MAE of home margin, 2013-2025", title="Single forecasts vs the lines")
for i, v in enumerate(vals[::-1]): axes[0].text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)
w = results["stack: everything"]["weights"]; axes[1].bar(list(w.keys()), list(w.values()), color="#4C72B0")
axes[1].axhline(0, color="k", lw=0.8); axes[1].set(ylabel="stacking weight", title=f"Weights when stacked with the lines (MAE {results['stack: everything']['mae']:.2f})")
plt.setp(axes[1].get_xticklabels(), rotation=30, ha="right"); fig.tight_layout(); fig.savefig(FIGURES / "ensemble_external.png"); plt.close(fig)
print(corr.to_string())
