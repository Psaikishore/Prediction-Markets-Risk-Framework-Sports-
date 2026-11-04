"""Parlays on Kalshi: are they priced as the product of their legs, and what does the joint grid say?

A. Inventory of NFL parlay markets (legs, games, volume, timing).
B. Cross-game parlays: fill price against the product of the leg mids at the fill hour (market independence) and
   against the grid fair value (model), with the sportsbook product of de-vigged closing probabilities.
C. Independence across games: correlation of the forest's out-of-sample margin and total residuals between games on
   the same date and in the same week, 2010-2025, and the joint frequency of two events against the product.
D. Same-game legs: grid joint probability against the product of marginals, on the fills and on a lattice of lines;
   the grid's dependence checked against historical joint frequencies.
E. Settlement: Brier scores of fill price, product of mids and grid fair value on settled parlays.
F. A small book of parlays and single legs netted on the joint grid: exact settlement P&L distribution.

Inputs: scripts/pull_kalshi_parlays.py outputs, kalshi_markets/candles, nflverse schedules,
data/processed/line_var_implied_lines.csv (scripts/line_var.py), model_rf_predictions.csv (scripts/model_rf.py).
Outputs: data/processed/parlay_*.csv, parlay_summary.json, reports/figures/parlay_*.png.
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

from pmrisk import DATA_PROCESSED, DATA_RAW, FIGURES
from pmrisk.link import kickoff_utc, link_to_schedule, parse_events
from pmrisk.nfl import completed_games, load_schedules
from pmrisk.parlay import ParlayLeg, legs_from_market, parlay_fair_value, product_of_marginals
from pmrisk.risk import Contract
from pmrisk.score_model import ScoreGrid, empirical_grid, tilt

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
C = {"winner": "#4C72B0", "spread": "#DD8452", "total": "#55A868"}
rng = np.random.default_rng(11)
out = {}


def implied(m):
    m = np.asarray(m, dtype=float)
    return np.where(m < 0, -m / (-m + 100), 100 / (m + 100))


def brier(p, y):
    m = pd.notna(p) & pd.notna(y)
    return float(((p[m] - y[m]) ** 2).mean())


# ---- data ---------------------------------------------------------------------------------------------------
sched = load_schedules()
hist = completed_games(sched)
prior = empirical_grid(hist[hist.season.between(2015, 2025)], smooth=0.02)
markets = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")
ev = link_to_schedule(parse_events(markets), sched)
ev = ev.merge(sched[["game_id", "gameday", "gametime", "game_type", "home_team", "away_team", "home_score", "away_score",
                     "spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds",
                     "over_odds", "under_odds"]], on="game_id", how="left")
ev["kickoff"] = kickoff_utc(ev.dropna(subset=["gameday"]).assign(gameday=lambda d: d.gameday))
game_by_event = ev.dropna(subset=["game_id"]).set_index("event_ticker").game_id.to_dict()
games = ev.dropna(subset=["game_id"]).drop_duplicates("game_id").set_index("game_id")
home_by_game = games.home_team.to_dict()

pm = pd.read_parquet(DATA_RAW / "kalshi_parlays.parquet")
pl = pd.read_parquet(DATA_RAW / "kalshi_parlay_legs.parquet")
if "--sample" in sys.argv:  # debugging: a random subset of markets
    pm = pm.sample(int(sys.argv[sys.argv.index("--sample") + 1]), random_state=0)
    pl = pl[pl.ticker.isin(pm.ticker)]
# Fill time and price: the candle fill where pulled, else the creation hour and last price (see pull_kalshi_parlays.py).
cfills = pd.read_parquet(DATA_RAW / "kalshi_parlay_fills.parquet")
approx = pm[~pm.ticker.isin(cfills.ticker) & pm.last_price_dollars.notna() & (pm.volume_fp > 0)]
fills = pd.concat([cfills[["ticker", "end_time", "price", "volume"]].assign(source="candle"),
                   pd.DataFrame({"ticker": approx.ticker, "end_time": pd.to_datetime(approx.created_time, utc=True, format="ISO8601").dt.ceil("h"),
                                 "price": approx.last_price_dollars, "volume": approx.volume_fp, "source": "created+last"})], ignore_index=True)
fills["end_time"] = pd.to_datetime(fills.end_time, utc=True).astype("datetime64[ns, UTC]")
pl["game_id"] = pl.leg_event.map(game_by_event)
pl["kind"] = pl.leg_market.str.split("-").str[0].map({"KXNFLGAME": "winner", "KXNFLSPREAD": "spread", "KXNFLTOTAL": "total"})
pl["unlinked"] = pl.game_id.isna()
for k in ("spread", "total", "winner"):
    pl[f"has_{k}"] = pl.kind == k
per = pl.groupby("ticker").agg(n_legs=("leg", "size"), n_games=("game_id", "nunique"), n_unlinked=("unlinked", "sum"),
                               has_spread=("has_spread", "max"), has_total=("has_total", "max"), has_winner=("has_winner", "max"))
per["kinds"] = pd.Series(np.where(per.has_spread, "spread+", "") + np.where(per.has_total, "total+", "") + np.where(per.has_winner, "winner+", ""),
                         index=per.index).str.rstrip("+")
per = per.drop(columns=["has_spread", "has_total", "has_winner"])
pm = pm.drop(columns=["n_legs"], errors="ignore").merge(per, left_on="ticker", right_index=True, how="left")
pm["linked"] = pm.n_unlinked == 0
pm["structure"] = np.select([pm.n_games == 1, pm.n_games == pm.n_legs], ["same-game", "cross-game"], "mixed")
WINNER_ONLY = "--all-kinds" not in sys.argv  # this week: match-winner legs only; spread/total legs are kept out
if WINNER_ONLY:
    pm = pm[pm.kinds == "winner"].copy()
pm["settled_yes"] = pm.result.map({"yes": 1.0, "no": 0.0})
leg_games = pl.dropna(subset=["game_id"]).merge(games[["game_type", "kickoff"]], left_on="game_id", right_index=True)
first_kick = leg_games.groupby("ticker").kickoff.min()
pm["first_kickoff"] = first_kick.reindex(pm.ticker).to_numpy()
pm["phase"] = pm.ticker.map(leg_games.groupby("ticker").game_type.agg(lambda s: "REG" if (s == "REG").all() else "PRE/other"))

# ---- A. inventory ---------------------------------------------------------------------------------------------
inv = {"n_markets": int(len(pm)), "n_linked_to_schedule": int(pm.linked.sum()), "n_with_fills": int(pm.ticker.isin(fills.ticker).sum()),
       "contracts_total": float(pm.volume_fp.sum()), "by_structure": pm.groupby("structure").agg(n=("ticker", "size"), contracts=("volume_fp", "sum")).round(0).to_dict(orient="index"),
       "by_n_legs": pm.groupby("n_legs").agg(n=("ticker", "size"), contracts=("volume_fp", "sum")).round(0).to_dict(orient="index"),
       "by_kinds": pm.kinds.value_counts().head(8).to_dict(), "by_phase": pm.phase.value_counts(dropna=False).to_dict(),
       "by_result": pm.result.value_counts(dropna=False).to_dict(), "by_series": pm.series.value_counts().to_dict()}
out["inventory"] = inv
pm.to_csv(DATA_PROCESSED / "parlay_markets.csv", index=False)

# ---- leg prices and grids at each fill hour -------------------------------------------------------------------
cd = pd.read_parquet(DATA_RAW / "kalshi_candles.parquet")[["ticker", "end_time", "bid_close", "ask_close", "close"]]
cd = cd[(cd.bid_close > 0) & (cd.ask_close < 1) & cd.bid_close.notna() & cd.ask_close.notna()].copy()
cd["mid"] = (cd.bid_close + cd.ask_close) / 2
cd["end_time"] = pd.to_datetime(cd.end_time, utc=True).astype("datetime64[ns, UTC]")
mid_lookup = cd.set_index(["ticker", "end_time"]).mid
il = pd.read_csv(DATA_PROCESSED / "line_var_implied_lines.csv")
il_lookup = {(r.game_id, int(r.h)): (r.spread, r.total) for r in il.itertuples()}
grid_cache: dict[tuple, ScoreGrid] = {}


def grid_at(game_id: str, when: pd.Timestamp) -> tuple[ScoreGrid, str]:
    """Grid tilted to the Kalshi-implied line nearest the fill hour (±3h), else to the closing line."""
    g = games.loc[game_id]
    h = int(round((g.kickoff - when).total_seconds() / 3600)) if pd.notna(g.kickoff) else None
    key, src = None, "none"
    if h is not None:
        for d in (0, 1, -1, 2, -2, 3, -3):
            if (game_id, h + d) in il_lookup:
                key, src = il_lookup[(game_id, h + d)], "kalshi_implied"
                break
    if key is None and pd.notna(g.spread_line) and pd.notna(g.total_line):
        key, src = (float(g.spread_line), float(g.total_line)), "closing_line"
    if key is None:
        return None, src
    if key not in grid_cache:
        grid_cache[key] = tilt(prior, key[0], key[1])[0]
    return grid_cache[key], src


def book_leg_prob(leg_row, g) -> float:
    """Sportsbook de-vigged probability of a leg from the closing line (multiplicative de-vig)."""
    k = leg_row.kind
    if k == "winner":
        ph, pa = implied(g.home_moneyline), implied(g.away_moneyline)
        p = ph / (ph + pa)
        p = p if leg_row.contract.side == "home" else 1 - p
    elif k == "spread":
        if pd.isna(g.home_spread_odds):
            return np.nan
        ph, pa = implied(g.home_spread_odds), implied(g.away_spread_odds)
        # the closing spread's own strike; our leg may sit elsewhere, in which case the book has no quote
        if abs(leg_row.contract.strike - (g.spread_line if leg_row.contract.side == "home" else -g.spread_line)) > 0.26:
            return np.nan
        p = ph / (ph + pa) if leg_row.contract.side == "home" else pa / (ph + pa)
    else:
        if pd.isna(g.over_odds) or abs(leg_row.contract.strike - g.total_line) > 0.26:
            return np.nan
        po, pu = implied(g.over_odds), implied(g.under_odds)
        p = po / (po + pu)
    return 1 - p if leg_row.side == "no" else p


def price_fills_loop(pm_sel: pd.DataFrame) -> pd.DataFrame:
    """Generic per-market pricing of every fill (any leg kind): slow Python loop over markets."""
    global book_ticker
    legs_by_ticker = {t: g.sort_values("leg") for t, g in pl[pl.ticker.isin(pm_sel.ticker)].groupby("ticker")}
    fills_by_ticker = {t: g for t, g in fills[fills.ticker.isin(pm_sel.ticker)].groupby("ticker")}
    rows, skipped, book_ticker = [], {"unlinked": 0, "no_grid": 0, "no_leg_mid": 0}, None
    for r in pm_sel[pm_sel.linked].itertuples():
        legs_raw = json.loads(r.legs_json)
        try:
            legs = legs_from_market(legs_raw, mk_idx, home_by_game, game_by_event)
        except KeyError:
            skipped["unlinked"] += 1
            continue
        leg_rows = legs_by_ticker[r.ticker]
        f = fills_by_ticker.get(r.ticker)
        if f is None:
            continue
        for fr in f.itertuples():
            grids, src = {}, set()
            for l in legs:
                if l.game_id not in grids:
                    gr, s = grid_at(l.game_id, fr.end_time)
                    grids[l.game_id], src = gr, src | {s}
            if any(v is None for v in grids.values()):
                skipped["no_grid"] += 1
                continue
            mids = []
            for l, lr in zip(legs, leg_rows.itertuples()):
                m = mid_lookup.get((lr.leg_market, fr.end_time), np.nan)
                mids.append((1 - m if l.side == "no" else m) if pd.notna(m) else np.nan)
            if book_ticker != r.ticker:
                book = [book_leg_prob(type("L", (), {"kind": lr.kind, "contract": l.contract, "side": l.side})(), games.loc[l.game_id])
                        for l, lr in zip(legs, leg_rows.itertuples())]
                book_ticker = r.ticker
            rows.append({"ticker": r.ticker, "structure": r.structure, "n_legs": r.n_legs, "n_games": r.n_games, "kinds": r.kinds, "phase": r.phase,
                         "fill_time": fr.end_time, "hours_to_kickoff": (r.first_kickoff - fr.end_time).total_seconds() / 3600 if pd.notna(r.first_kickoff) else np.nan,
                         "price": fr.price, "volume": fr.volume, "settled_yes": r.settled_yes, "line_source": "+".join(sorted(src)), "fill_source": fr.source,
                         "fair_grid": parlay_fair_value(legs, grids), "product_grid": product_of_marginals(legs, grids),
                         "product_mids": float(np.prod(mids)) if not any(pd.isna(mids)) else np.nan, "n_legs_with_mid": int(sum(pd.notna(mids))),
                         "product_book": float(np.prod(book)) if not any(pd.isna(book)) else np.nan})
    F = pd.DataFrame(rows, columns=["ticker", "structure", "n_legs", "n_games", "kinds", "phase", "fill_time", "hours_to_kickoff", "price", "volume", "settled_yes",
                                    "line_source", "fill_source", "fair_grid", "product_grid", "product_mids", "n_legs_with_mid", "product_book"])
    out["fills_skipped_loop"] = skipped
    return F

def price_fills_winner(pm_sel: pd.DataFrame) -> pd.DataFrame:
    """Vectorised pricing of every fill when every leg is a match-winner contract.

    A winner leg's probability is a scalar per game and hour (home or away win on the grid tilted to the line at
    that hour), so the product over legs is a group-by, which prices ~1M parlays in minutes instead of hours.
    Two winner legs on one game are either the same outcome (joint = that probability) or contradictory (joint = 0).
    """
    from pmrisk.nfl import KALSHI_TO_NFLVERSE
    L = pl[pl.ticker.isin(pm_sel.ticker[pm_sel.linked])].merge(fills, on="ticker")
    L["game_id"] = L.leg_event.map(game_by_event)
    team = L.leg_market.str.rsplit("-", n=1).str[-1].str.rstrip("0123456789").map(lambda t: KALSHI_TO_NFLVERSE.get(t, t))
    L["yes_is_home"] = team.to_numpy() == L.game_id.map(home_by_game).to_numpy()
    L["want_home"] = L.yes_is_home ^ (L.side == "no")  # the parlay needs the home team to win iff (yes, home) or (no, away)
    # grid win probabilities per (game, fill hour): same line choice as grid_at
    gk = L[["game_id", "end_time"]].drop_duplicates().reset_index(drop=True)
    keys, srcs = [], []
    for r in gk.itertuples():
        g = games.loc[r.game_id]
        h = int(round((g.kickoff - r.end_time).total_seconds() / 3600)) if pd.notna(g.kickoff) else None
        key, src = None, "none"
        if h is not None:
            for d in (0, 1, -1, 2, -2, 3, -3):
                if (r.game_id, h + d) in il_lookup:
                    key, src = il_lookup[(r.game_id, h + d)], "kalshi_implied"
                    break
        if key is None and pd.notna(g.spread_line) and pd.notna(g.total_line):
            key, src = (float(g.spread_line), float(g.total_line)), "closing_line"
        keys.append(key); srcs.append(src)
    gk["key"], gk["line_source"] = keys, srcs
    p_home_by_key, p_away_by_key = {}, {}
    for key in set(k for k in keys if k is not None):
        if key not in grid_cache:
            grid_cache[key] = tilt(prior, key[0], key[1])[0]
        p_home_by_key[key] = grid_cache[key].p_home_win(tie_value=0.0)      # strict home win (a tie settles no)
        p_away_by_key[key] = 1 - grid_cache[key].p_home_win(tie_value=1.0)  # strict away win
    gk["p_home_grid"] = gk.key.map(p_home_by_key)
    gk["p_away_grid"] = gk.key.map(p_away_by_key)
    L = L.merge(gk.drop(columns="key"), on=["game_id", "end_time"], how="left")
    L["p_grid"] = np.where(L.want_home, L.p_home_grid, L.p_away_grid)
    # Kalshi leg mid at the fill hour, and the de-vigged closing moneyline
    L = L.merge(mid_lookup.rename("mid").reset_index().rename(columns={"ticker": "leg_market"}), on=["leg_market", "end_time"], how="left")
    L["p_mid"] = np.where(L.side == "no", 1 - L.mid, L.mid)
    gb = games[["home_moneyline", "away_moneyline"]].copy()
    ph, pa = implied(gb.home_moneyline), implied(gb.away_moneyline)
    gb["p_home_book"] = ph / (ph + pa)
    L["p_home_book"] = L.game_id.map(gb.p_home_book)
    L["p_book"] = np.where(L.want_home, L.p_home_book, 1 - L.p_home_book)
    # per (parlay, fill, game): joint of the legs on that game; then product across games
    G = L.groupby(["ticker", "end_time", "game_id"], sort=False).agg(n=("want_home", "size"), n_home=("want_home", "sum"),
                                                                     p_grid=("p_grid", "first"), line_source=("line_source", "first"))
    G["joint_grid"] = np.where((G.n_home > 0) & (G.n_home < G.n), 0.0, G.p_grid)
    per_fill_games = G.groupby(["ticker", "end_time"], sort=False).agg(fair_grid=("joint_grid", "prod"), n_games=("n", "size"),
                                                                       line_source=("line_source", lambda s: "+".join(sorted(set(s)))))
    per_fill = L.groupby(["ticker", "end_time"], sort=False).agg(n_legs=("leg", "size"), product_grid=("p_grid", "prod"),
                                                                 n_legs_with_mid=("p_mid", "count"), product_mids=("p_mid", "prod"),
                                                                 n_book=("p_book", "count"), product_book=("p_book", "prod"),
                                                                 price=("price", "first"), volume=("volume", "first"), fill_source=("source", "first"),
                                                                 any_no_grid=("p_grid", lambda s: s.isna().any()))
    F = per_fill.join(per_fill_games).reset_index().rename(columns={"end_time": "fill_time"})
    F.loc[F.n_legs_with_mid < F.n_legs, "product_mids"] = np.nan
    F.loc[F.n_book < F.n_legs, "product_book"] = np.nan
    skipped["no_grid"] = int(F.any_no_grid.sum())
    F = F[~F.any_no_grid].drop(columns=["any_no_grid", "n_book"])
    m = pm_sel.set_index("ticker")
    F["structure"] = F.ticker.map(m.structure); F["kinds"] = F.ticker.map(m.kinds); F["phase"] = F.ticker.map(m.phase)
    F["settled_yes"] = F.ticker.map(m.settled_yes)
    F["hours_to_kickoff"] = (F.ticker.map(m.first_kickoff) - F.fill_time).dt.total_seconds() / 3600
    cols = ["ticker", "structure", "n_legs", "n_games", "kinds", "phase", "fill_time", "hours_to_kickoff", "price", "volume", "settled_yes",
            "line_source", "fill_source", "fair_grid", "product_grid", "product_mids", "n_legs_with_mid", "product_book"]
    return F[cols]


mk_idx = markets.set_index("ticker")
skipped, book_ticker = {"unlinked": 0, "no_grid": 0, "no_leg_mid": 0}, None
if WINNER_ONLY:
    F = price_fills_winner(pm)
    if "--check" in sys.argv:  # the fast path against the generic loop on a random subsample
        sub = pm[pm.linked & pm.ticker.isin(fills.ticker)].sample(min(300, int(pm.linked.sum())), random_state=0)
        Fl = price_fills_loop(sub).set_index(["ticker", "fill_time"]); Ff = F.set_index(["ticker", "fill_time"]).loc[Fl.index]
        for c in ["fair_grid", "product_grid", "product_mids", "product_book"]:
            print(f"check {c}: n={Fl[c].notna().sum()} max|loop-fast|={np.nanmax(np.abs(Fl[c] - Ff[c])):.2e} nan-agree={(Fl[c].isna() == Ff[c].isna()).mean():.3f}")
else:
    F = price_fills_loop(pm)

F["premium_vs_mids"] = F.price - F.product_mids
F["premium_vs_grid"] = F.price - F.fair_grid
F["corr_premium_grid"] = F.fair_grid - F.product_grid
F["pregame"] = F.hours_to_kickoff > 0  # fill before the earliest kickoff among the legs; later fills see part of a game
F.to_csv(DATA_PROCESSED / "parlay_fills_priced.csv", index=False)
out["fills"] = {"n_fill_hours": int(len(F)), "n_markets": int(F.ticker.nunique()), "skipped": skipped, "line_source": F.line_source.value_counts().to_dict(), "fill_source": F.fill_source.value_counts().to_dict(),
                "n_with_all_leg_mids": int(F.product_mids.notna().sum())}

# ---- B. cross-game: price vs product of leg mids --------------------------------------------------------------
Xall = F[(F.structure == "cross-game") & F.product_mids.notna()].copy()
X = Xall[Xall.pregame].copy()  # pre-game fills only: the leg mids and the grid are pre-game quantities
X["ratio_mids"] = X.price / X.product_mids
X["ratio_grid"] = X.price / X.fair_grid


def summarise(d, col):
    w = d.volume
    return {"n": int(len(d)), "mean_cents": round(100 * d[col].mean(), 2), "vw_mean_cents": round(100 * np.average(d[col], weights=w), 2) if len(d) else None,
            "median_cents": round(100 * d[col].median(), 2), "sd_cents": round(100 * d[col].std(), 2),
            "q10_cents": round(100 * d[col].quantile(0.1), 2), "q90_cents": round(100 * d[col].quantile(0.9), 2),
            "share_within_2c": round(float((d[col].abs() <= 0.02).mean()), 3)}


B = {"all": summarise(X, "premium_vs_mids") if len(X) else None, "vs_grid": summarise(X, "premium_vs_grid") if len(X) else None,
     "by_n_legs": {int(k): summarise(d, "premium_vs_mids") for k, d in X.groupby("n_legs")},
     "by_product_level": {str(k): summarise(d, "premium_vs_mids") for k, d in X.groupby(pd.cut(X.product_mids, [0, .05, .1, .2, .35, .5, 1]), observed=True)},
     "by_phase": {k: summarise(d, "premium_vs_mids") for k, d in X.groupby("phase")},
     "ratio_price_over_product": {"mean": round(float(X.ratio_mids.mean()), 3), "median": round(float(X.ratio_mids.median()), 3)} if len(X) else None,
     "corr_price_product": round(float(X[["price", "product_mids"]].corr().iloc[0, 1]), 3) if len(X) > 2 else None}
if len(X) > 10:
    A = np.column_stack([np.ones(len(X)), X.product_mids, X.n_legs])
    coef = np.linalg.lstsq(A, X.premium_vs_mids, rcond=None)[0]
    B["regression_premium_on_product_and_legs"] = {"intercept_cents": round(100 * coef[0], 2), "slope_product": round(float(coef[1]), 3), "per_leg_cents": round(100 * coef[2], 2)}
Xb = X.dropna(subset=["product_book"])
B["vs_book_product"] = {"n": int(len(Xb)), "mean_price_minus_book_cents": round(100 * (Xb.price - Xb.product_book).mean(), 2) if len(Xb) else None,
                        "mean_mids_minus_book_cents": round(100 * (Xb.product_mids - Xb.product_book).mean(), 2) if len(Xb) else None}
B["in_game_fills"] = summarise(Xall[~Xall.pregame], "premium_vs_mids") if (~Xall.pregame).any() else None
B["in_game_fills_vs_grid"] = summarise(Xall[~Xall.pregame], "premium_vs_grid") if (~Xall.pregame).any() else None
B["share_pregame"] = round(float(Xall.pregame.mean()), 3) if len(Xall) else None
out["cross_game"] = B

# ---- C. independence across games ------------------------------------------------------------------------------
P = pd.read_csv(DATA_PROCESSED / "model_rf_predictions.csv").merge(sched[["game_id", "gameday"]], on="game_id")
P["res_m"], P["res_t"] = P.margin - P.rf_margin, P.total_pts - P.rf_total
P["res_line_m"], P["res_line_t"] = P.margin - P.spread_line, P.total_pts - P.total_line


def pair_corr(df, group, col):
    """Average correlation between games in the same group: mean over pairs of r_i r_j / var(r)."""
    v = df[col].var(); num, n = 0.0, 0
    for _, g in df.groupby(group):
        r = g[col].to_numpy()
        if len(r) < 2:
            continue
        s = r.sum(); num += (s * s - (r * r).sum()) / 2; n += len(r) * (len(r) - 1) // 2
    return float(num / n / v), int(n)


ind = {}
for col, lab in [("res_m", "margin residual (forest)"), ("res_t", "total residual (forest)"), ("res_line_m", "margin vs closing line"), ("res_line_t", "total vs closing total")]:
    for grp, glab in [("gameday", "same date"), (["season", "week"], "same week")]:
        rho, npairs = pair_corr(P, grp, col)
        ind[f"{lab} | {glab}"] = {"corr": round(rho, 4), "n_pairs": npairs, "se_approx": round(1 / np.sqrt(npairs), 4)}
# joint frequency of two events vs product, same-week pairs
P["home_cover"] = np.where(P.margin == P.spread_line, np.nan, (P.margin > P.spread_line).astype(float))
P["over"] = np.where(P.total_pts == P.total_line, np.nan, (P.total_pts > P.total_line).astype(float))
P["home_win"] = (P.margin > 0).astype(float)
joint = {}
for col in ["home_win", "home_cover", "over"]:
    both, prod_, n = 0.0, 0.0, 0
    for _, g in P.dropna(subset=[col]).groupby(["season", "week"]):
        y = g[col].to_numpy()
        for i, j in itertools.combinations(range(len(y)), 2):
            both += y[i] * y[j]; n += 1
    p1 = P[col].mean()
    joint[col] = {"joint_freq_both": round(both / n, 4), "product_of_marginals": round(p1 * p1, 4), "n_pairs": n}
out["independence"] = {"pairwise_correlations": ind, "same_week_pairs": joint}

# ---- D. same-game: grid joint vs product --------------------------------------------------------------------
S = F[F.structure == "same-game"].copy()
D = {"fills": {"n": int(len(S)), "mean_corr_premium_cents": round(100 * S.corr_premium_grid.mean(), 2) if len(S) else None,
               "mean_price_minus_product_mids_cents": round(100 * S.premium_vs_mids.mean(), 2) if S.premium_vs_mids.notna().any() else None,
               "mean_price_minus_fair_grid_cents": round(100 * S.premium_vs_grid.mean(), 2) if len(S) else None,
               "share_price_closer_to_fair_than_product": round(float(((S.price - S.fair_grid).abs() < (S.price - S.product_grid).abs()).mean()), 3) if len(S) else None}}
combos = {
    "home ML & over": lambda s, t: [Contract("winner", "home"), Contract("total", "over", t)],
    "home ML & under": lambda s, t: [Contract("winner", "home"), Contract("total", "over", t, -1)],  # qty unused; side handled below
    "home covers & over": lambda s, t: [Contract("spread", "home", s - 0.5 if s % 1 == 0 else s), Contract("total", "over", t)],
    "home covers & under": lambda s, t: [Contract("spread", "home", s - 0.5 if s % 1 == 0 else s), Contract("total", "over", t, -1)],
    "home ML & home covers": lambda s, t: [Contract("winner", "home"), Contract("spread", "home", s - 0.5 if s % 1 == 0 else s)],
    "home -3.5 & home -10.5": lambda s, t: [Contract("spread", "home", 3.5), Contract("spread", "home", 10.5)],
}
lat_rows = []
for s0 in [-10, -7, -3, 0, 3, 7, 10]:
    for t0 in [40.5, 44.5, 49.5]:
        g = tilt(prior, s0, t0)[0]
        for name, fn in combos.items():
            legs = [ParlayLeg("g", c if c.qty > 0 else Contract(c.kind, c.side, c.strike, 1.0), "yes" if c.qty > 0 else "no") for c in fn(s0, t0)]
            fair, prod_ = parlay_fair_value(legs, {"g": g}), product_of_marginals(legs, {"g": g})
            lat_rows.append({"spread": s0, "total": t0, "combo": name, "fair": fair, "product": prod_, "premium_cents": 100 * (fair - prod_), "ratio": fair / prod_ if prod_ else np.nan})
L = pd.DataFrame(lat_rows)
L.to_csv(DATA_PROCESSED / "parlay_sgp_lattice.csv", index=False)
D["lattice_premium_cents_at_total_44.5"] = L[L.total == 44.5].pivot(index="combo", columns="spread", values="premium_cents").round(2).to_dict(orient="index")
# historical check: joint frequency vs product in 2015-2025 games, by favourite size, for home win & over
H = hist[hist.season.between(2015, 2025)].dropna(subset=["spread_line", "total_line"]).copy()
H["home_win"] = (H.margin > 0).astype(float); H["over"] = (H.total_pts > H.total_line).astype(float)
H["home_cover"] = np.where(H.margin == H.spread_line, np.nan, (H.margin > H.spread_line).astype(float))
H["bucket"] = pd.cut(H.spread_line, [-30, -3.5, -0.5, 0.5, 3.5, 30], labels=["home dog >3", "home dog <=3", "pick", "home fav <=3", "home fav >3"])
hc = []
for b, g in H.groupby("bucket", observed=True):
    for a, c in [("home_win", "over"), ("home_cover", "over")]:
        gg = g.dropna(subset=[a, c])
        both = (gg[a] * gg[c]).mean(); pr = gg[a].mean() * gg[c].mean()
        # grid at the bucket's mean line
        gr = tilt(prior, float(g.spread_line.mean()), float(g.total_line.mean()))[0]
        legs = [ParlayLeg("g", Contract("winner" if a == "home_win" else "spread", "home", 0 if a == "home_win" else float(g.spread_line.mean()) - 0.5)),
                ParlayLeg("g", Contract("total", "over", float(g.total_line.mean())))]
        hc.append({"bucket": str(b), "events": f"{a} & {c}", "n": len(gg), "joint_freq": round(both, 4), "product": round(pr, 4), "hist_premium_cents": round(100 * (both - pr), 2),
                   "grid_premium_cents": round(100 * (parlay_fair_value(legs, {"g": gr}) - product_of_marginals(legs, {"g": gr})), 2)})
HC = pd.DataFrame(hc)
HC.to_csv(DATA_PROCESSED / "parlay_sgp_historical_check.csv", index=False)
D["historical_check"] = HC.to_dict(orient="records")
out["same_game"] = D

# ---- E. settlement --------------------------------------------------------------------------------------------
E_ = F.dropna(subset=["settled_yes"]).copy()
E_["last_fill"] = E_.groupby("ticker").fill_time.transform("max") == E_.fill_time
E1 = E_[E_.last_fill & E_.pregame]
Es = {"n_settled_markets": int(len(E1)), "n_settled_markets_in_game": int((E_.last_fill & ~E_.pregame).sum())}
Ein = E_[E_.last_fill & ~E_.pregame]
if len(Ein):
    Es["in_game"] = {"hit_rate": round(float(Ein.settled_yes.mean()), 4), "mean_price": round(float(Ein.price.mean()), 4),
                     "mean_fair_grid": round(float(Ein.fair_grid.mean()), 4), "brier_price": round(brier(Ein.price, Ein.settled_yes), 4),
                     "brier_fair_grid": round(brier(Ein.fair_grid, Ein.settled_yes), 4)}
rel = pd.DataFrame(columns=["n", "mean_price", "hit", "mean_fair"])
if len(E1):
    Es.update({"hit_rate": round(float(E1.settled_yes.mean()), 4), "mean_price": round(float(E1.price.mean()), 4),
               "mean_fair_grid": round(float(E1.fair_grid.mean()), 4), "mean_product_mids": round(float(E1.product_mids.mean()), 4) if E1.product_mids.notna().any() else None,
               "brier_price": round(brier(E1.price, E1.settled_yes), 4), "brier_fair_grid": round(brier(E1.fair_grid, E1.settled_yes), 4),
               "brier_product_mids": round(brier(E1.product_mids, E1.settled_yes), 4) if E1.product_mids.notna().any() else None,
               "brier_climatology": round(float(((E1.settled_yes.mean() - E1.settled_yes) ** 2).mean()), 4)})
    bins = pd.cut(E1.price, [0, .05, .1, .2, .35, .5, 1])
    rel = E1.groupby(bins, observed=True).agg(n=("settled_yes", "size"), mean_price=("price", "mean"), hit=("settled_yes", "mean"), mean_fair=("fair_grid", "mean")).round(4)
    Es["reliability_by_price"] = {str(k): v for k, v in rel.to_dict(orient="index").items()}
    rel_by = {}
    for col in ("fair_grid", "product_mids", "price"):
        g = E1.dropna(subset=[col]).groupby(pd.cut(E1[col], [0, .005, .01, .02, .05, .1, .2, .35, .5, 1]), observed=True).agg(n=("settled_yes", "size"), mean_p=(col, "mean"), hit=("settled_yes", "mean"), mean_price=("price", "mean")).round(4)
        rel_by[col] = g
        if col != "price":
            Es[f"reliability_by_{col}"] = {str(k): v for k, v in g.to_dict(orient="index").items()}
    by_legs = E1.groupby(pd.cut(E1.n_legs, [1, 2, 3, 4, 6, 8, 12, 40]), observed=True).agg(n=("settled_yes", "size"), price=("price", "mean"), hit=("settled_yes", "mean"), fair_grid=("fair_grid", "mean"), product_mids=("product_mids", "mean")).round(4)
    Es["by_n_legs"] = {str(k): v for k, v in by_legs.to_dict(orient="index").items()}
# block bootstrap over first-kickoff dates for the mean(price - outcome)
if len(E1) > 20:
    E1 = E1.assign(block=pm.set_index("ticker").first_kickoff.reindex(E1.ticker).dt.date.values)
    per = E1.groupby("block").apply(lambda d: pd.Series({"d": (d.price - d.settled_yes).sum(), "n": len(d)}), include_groups=False)
    idx = rng.integers(0, len(per), size=(2000, len(per)))
    bs = per.d.to_numpy()[idx].sum(1) / per.n.to_numpy()[idx].sum(1)
    Es["mean_price_minus_outcome_cents"] = round(100 * float((E1.price - E1.settled_yes).mean()), 2)
    Es["block_ci_cents"] = [round(100 * float(x), 2) for x in np.quantile(bs, [0.025, 0.975])]

    def block_ci(d, col):
        """Mean of (col - outcome) in cents with a 95% block-bootstrap interval over first-kickoff dates."""
        d = d.dropna(subset=[col])
        per = d.assign(x=d[col] - d.settled_yes).groupby("block").agg(d=("x", "sum"), n=("x", "size"))
        idx = rng.integers(0, len(per), size=(2000, len(per)))
        bs = per.d.to_numpy()[idx].sum(1) / per.n.to_numpy()[idx].sum(1)
        return {"n": int(len(d)), "mean_cents": round(100 * float((d[col] - d.settled_yes).mean()), 3), "ci_cents": [round(100 * float(x), 3) for x in np.quantile(bs, [0.025, 0.975])]}

    Es["minus_outcome"] = {c: block_ci(E1, c) for c in ("price", "fair_grid", "product_mids", "product_book")}
    Es["minus_outcome_by_legs"] = {str(k): {c: block_ci(d, c) for c in ("price", "fair_grid", "product_mids")}
                                   for k, d in E1.groupby(pd.cut(E1.n_legs, [1, 2, 3, 4, 6, 8, 12, 40]), observed=True)}
    wk = E1.assign(week=pd.to_datetime(E1.block).dt.to_period("W").astype(str)).groupby("week").agg(
        n=("settled_yes", "size"), hit=("settled_yes", "mean"), price=("price", "mean"), fair_grid=("fair_grid", "mean"), product_mids=("product_mids", "mean"), legs=("n_legs", "mean")).round(4)
    Es["by_week"] = {str(k): v for k, v in wk.to_dict(orient="index").items()}
    Ec = E1[E1.fill_source == "candle"]  # markets whose fill hours come from the candles: the last fill is known to be pre-game
    if len(Ec) > 20:
        Es["candle_timed_only"] = {"n": int(len(Ec)), "hit_rate": round(float(Ec.settled_yes.mean()), 4), "mean_price": round(float(Ec.price.mean()), 4),
                                   "mean_fair_grid": round(float(Ec.fair_grid.mean()), 4), "mean_product_mids": round(float(Ec.product_mids.mean()), 4),
                                   "brier_price": round(brier(Ec.price, Ec.settled_yes), 4), "brier_fair_grid": round(brier(Ec.fair_grid, Ec.settled_yes), 4)}
    # markets created pre-game whose recorded last price is far above the pre-game fair value: in-play last trades
    Es["share_price_over_2x_fair_and_above_30c"] = round(float(((E1.price > 2 * E1.fair_grid) & (E1.price > 0.3)).mean()), 4)
out["settlement"] = Es

# ---- F. a book netted on the grid ------------------------------------------------------------------------------
gA, gB = tilt(prior, -3.0, 44.5)[0], tilt(prior, 7.0, 48.5)[0]
book = [  # (legs, qty): positive qty = long YES contracts. Parlays hedged with their own legs.
    ([ParlayLeg("A", Contract("winner", "away")), ParlayLeg("B", Contract("winner", "home"))], 1000),
    ([ParlayLeg("A", Contract("winner", "away")), ParlayLeg("A", Contract("total", "over", 44.5))], 1000),
    ([ParlayLeg("B", Contract("spread", "home", 6.5)), ParlayLeg("B", Contract("total", "over", 48.5))], 500),
    ([ParlayLeg("A", Contract("winner", "away"))], -700),
    ([ParlayLeg("B", Contract("winner", "home"))], -400),
    ([ParlayLeg("A", Contract("total", "over", 44.5))], -500),
    ([ParlayLeg("B", Contract("total", "over", 48.5))], -300),
]
grids = {"A": gA, "B": gB}
# exact settlement distribution: enumerate the joint classes defined by all leg masks per game
classes = {}
for gid, g in grids.items():
    masks = [l.mask(g) for legs, _ in book for l in legs if l.game_id == gid]
    code = np.zeros(g.p.shape, dtype=np.int64)
    for i, m in enumerate(masks):
        code |= m.astype(np.int64) << i
    cls = {}
    for c in np.unique(code):
        cls[int(c)] = float(g.p[code == c].sum())
    classes[gid] = (cls, masks)
cost = sum(q * parlay_fair_value(legs, grids) for legs, q in book)
# Classes are products of per-game regions on which every leg mask is constant, so each book line's payoff is
# deterministic on a class; one representative cell per class evaluates it.
pnl, probs = [], []
line_masks = [[(l.game_id, l.mask(grids[l.game_id])) for l in legs] for legs, _ in book]
cellsA = {c: (np.zeros(gA.p.shape, bool) | (sum((m.astype(np.int64) << i) for i, m in enumerate(classes["A"][1])) == c)) for c in classes["A"][0]}
cellsB = {c: (np.zeros(gB.p.shape, bool) | (sum((m.astype(np.int64) << i) for i, m in enumerate(classes["B"][1])) == c)) for c in classes["B"][0]}
for ca, pa in classes["A"][0].items():
    for cb, pb in classes["B"][0].items():
        rep = {"A": tuple(np.argwhere(cellsA[ca])[0]), "B": tuple(np.argwhere(cellsB[cb])[0])}
        pay = 0.0
        for (legs, q), lm in zip(book, line_masks):
            pay += q * float(all(m[rep[gid]] for gid, m in lm))
        pnl.append(pay - cost); probs.append(pa * pb)
pnl, probs = np.array(pnl), np.array(probs)
o = np.argsort(pnl); pnl, probs = pnl[o], probs[o]; cdf = np.cumsum(probs)
def q_at(a): return float(pnl[np.searchsorted(cdf, a)])
k = int(np.searchsorted(cdf, 0.01)); tail = probs[:k + 1].copy(); tail[-1] -= cdf[k] - 0.01
es99 = float(-(pnl[:k + 1] * tail).sum() / 0.01)
out["book_example"] = {"lines": [{"legs": [f"{l.game_id}:{l.contract.kind}:{l.contract.side}:{l.contract.strike}" for l in legs], "qty": q, "fair": round(parlay_fair_value(legs, grids), 4)} for legs, q in book],
                       "cost": round(cost, 1), "n_joint_classes": int(len(pnl)), "expected_pnl": round(float((pnl * probs).sum()), 2),
                       "VaR95": round(-q_at(0.05), 1), "VaR99": round(-q_at(0.01), 1), "ES99": round(es99, 1), "worst": round(float(-pnl[0]), 1), "best": round(float(pnl[-1]), 1),
                       "sum_of_standalone_ES99": None}
# standalone ES99 per line for the netting comparison
stand = 0.0
for legs, q in book:
    p = parlay_fair_value(legs, grids); v = np.array([q * (1 - p), -q * p]) if q > 0 else np.array([q * (1 - p), -q * p])
    pr = np.array([p, 1 - p]); oo = np.argsort(v); v, pr = v[oo], pr[oo]; c = np.cumsum(pr)
    k = np.searchsorted(c, 0.01); tail = pr[:k + 1].copy(); tail[-1] -= c[k] - 0.01
    stand += float(-(v[:k + 1] * tail).sum() / 0.01)
out["book_example"]["sum_of_standalone_ES99"] = round(stand, 1)

# ---- figures ----------------------------------------------------------------------------------------------------
def draw_pricing(ax):
    Xs = X[(X.price <= 0.6) & (X.product_mids <= 0.6)]
    ax.hexbin(100 * Xs.product_mids, 100 * Xs.price, gridsize=45, bins="log", cmap="Blues", mincnt=1)
    bn = X.groupby(pd.cut(X.product_mids, np.arange(0, 0.62, 0.02)), observed=True).agg(p=("product_mids", "mean"), mean=("price", "mean"), med=("price", "median"))
    ax.plot(100 * bn.p, 100 * bn.med, "-", color=C["spread"], lw=1.5, label="median fill price")
    ax.plot(100 * bn.p, 100 * bn["mean"], ":", color=C["spread"], lw=1.5, label="mean fill price")
    ax.plot([0, 60], [0, 60], "k--", lw=0.8, label="price = product"); ax.legend(fontsize=7, loc="upper left")
    ax.set(xlabel="product of leg mids at creation hour, cents", ylabel="parlay fill price, cents", title=f"Cross-game winner parlays, pre-game (n={len(X):,})", xlim=(0, 60), ylim=(0, 60))


def draw_reliability(ax):
    for col, c, mk, lab in [("price", C["winner"], "o-", "fill price"), ("product_mids", C["spread"], "^-", "product of Kalshi leg mids"), ("fair_grid", C["total"], "s--", "grid (our model)")]:
        r_ = rel_by[col]; r_ = r_[r_.hit > 0]
        ax.errorbar(r_.mean_p, r_.hit, yerr=np.sqrt(r_.hit * (1 - r_.hit) / r_.n.clip(lower=1)), fmt=mk, ms=4, color=c, label=lab)
    ax.plot([0.002, 1], [0.002, 1], "k--", lw=0.8)
    ax.set(xscale="log", yscale="log", xlabel="stated probability (bucket mean)", ylabel="share settled yes", title=f"Settled pre-game winner parlays (n={len(E1):,})"); ax.legend(fontsize=7)


fig, axes = plt.subplots(1, 3, figsize=(14, 4))
if len(X):
    draw_pricing(axes[0])
    axes[1].hist(100 * X.premium_vs_mids.clip(-20, 20), bins=80, color=C["spread"], alpha=0.85)
    axes[1].axvline(0, color="k", lw=0.8)
    axes[1].set(xlabel="fill price − product of leg mids, cents", ylabel="fills", title=f"Premium: mean {100 * X.premium_vs_mids.mean():.1f}¢, median {100 * X.premium_vs_mids.median():.1f}¢")
else:
    axes[0].set(title="Cross-game parlays: no linked fills yet"); axes[1].set(title="")
piv = L[L.total == 44.5].pivot(index="combo", columns="spread", values="premium_cents")
im = axes[2].imshow(piv.values, cmap="RdBu_r", vmin=-8, vmax=8, aspect="auto")
axes[2].set_xticks(range(len(piv.columns)), [f"{int(s):+d}" if s else "0" for s in piv.columns]); axes[2].set_yticks(range(len(piv.index)), piv.index, fontsize=7)
axes[2].set(xlabel="home spread (positive = home favoured)", title="Same-game correlation premium, total 44.5 (cents)")
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        axes[2].text(j, i, f"{piv.values[i, j]:.1f}", ha="center", va="center", fontsize=6)
fig.colorbar(im, ax=axes[2], fraction=0.04)
fig.tight_layout(); fig.savefig(FIGURES / "parlay_pricing.png"); plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
if len(E1):
    draw_reliability(axes[0])
axes[1].bar(pnl, probs, width=max(1.0, (pnl.max() - pnl.min()) / 60), color=C["spread"])
axes[1].axvline(-out["book_example"]["VaR99"], color="k", ls=":", lw=1, label=f"VaR99 \\${out['book_example']['VaR99']:.0f}")
axes[1].set(xlabel="settlement P&L of the example book, \\$", ylabel="probability", title=f"Book on two grids: ES99 \\${out['book_example']['ES99']:.0f} netted vs \\${stand:.0f} unnetted", fontsize=9)
axes[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(FIGURES / "parlay_settlement.png"); plt.close(fig)

if len(X) and len(E1):  # the two Kalshi panels together, for the report
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    draw_pricing(axes[0]); draw_reliability(axes[1])
    fig.tight_layout(); fig.savefig(FIGURES / "parlay_kalshi.png"); plt.close(fig)

json.dump(out, open(DATA_PROCESSED / "parlay_summary.json", "w"), indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
