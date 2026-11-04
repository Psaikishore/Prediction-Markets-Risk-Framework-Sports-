"""Pre-game line risk for Kalshi NFL positions: Greeks from the score grid, open-to-close line moves, VaR.

1. Line moves: sportsbook open -> close from the nfelo game file (spreads from 2009, totals from 2024).
2. Greeks: exact line deltas of every ladder contract from the tilted grid, against the normal model.
3. VaR: historical simulation of reference positions, full revaluation on a (spread, total) price lattice,
   against delta-normal, and the hold-to-settlement loss distribution for contrast.
4. Backtest on 2026 Kalshi games (out of sample: scenarios use 2015-2025 only): Kalshi-implied line by hour,
   how line variance accrues toward kickoff, how much of each contract's price change the line explains,
   and VaR exceedance rates.

Outputs: reports/figures/line_var_*.png, data/processed/line_var_*.csv and line_var_summary.json.
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, DATA_RAW, FIGURES
from pmrisk.link import kickoff_utc, link_to_schedule, parse_events
from pmrisk.nfl import completed_games, load_schedules
from pmrisk.risk import (Contract, PriceLattice, contract_from_market, line_greeks, line_moves, scenario_pnl,
                         var_es)
from pmrisk.score_model import empirical_grid, tilt

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
C = {"winner": "#4C72B0", "spread": "#DD8452", "total": "#55A868"}
LATTICE = DATA_PROCESSED / "line_lattice.npz"
SCEN_SEASONS = (2015, 2025)
EXAMPLE = {"spread": 3.0, "total": 44.5}  # home favoured by 3, total 44.5
SIGMA = {"spread": 12.73, "total": 13.24}  # closing-line residual SDs, reports/eda.md
rng = np.random.default_rng(7)


def build_prior(sched):
    hist = completed_games(sched)
    return empirical_grid(hist[hist.season <= 2025], smooth=0.02)


def get_lattice(prior, refresh=False):
    if LATTICE.exists() and not refresh:
        return PriceLattice.load(LATTICE)
    lat = PriceLattice(prior, np.arange(-24, 24.01, 0.25), np.arange(30, 65.01, 0.25))
    lat.save(LATTICE)
    return lat


def scenarios(mv):
    """Primary set: every 2015-2025 spread move, each paired with a total move drawn from 2024-2025.

    Total opens exist only from 2024; signed spread and total moves correlate at 0.08, so pairing them
    independently loses little. The joint 2024-2025 pairs are kept as a check.
    """
    lo, hi = SCEN_SEASONS
    sp = mv[mv.season.between(lo, hi)].d_spread.to_numpy()
    tot_pool = mv[mv.season.between(2024, hi)].dropna(subset=["d_total"])
    dt = rng.choice(tot_pool.d_total.to_numpy(), size=len(sp), replace=True)
    return {"primary": (sp, dt), "joint_2024_25": (tot_pool.d_spread.to_numpy(), tot_pool.d_total.to_numpy())}


# -- 1. line moves ------------------------------------------------------------------------------------------

def section_moves(mv, out):
    lo, hi = SCEN_SEASONS
    base = mv[mv.season.between(lo, hi)]
    tot = mv[mv.season.between(2024, hi)].dropna(subset=["d_total"])
    def describe(x):
        x = pd.Series(x)
        return {"n": int(len(x)), "mean": round(x.mean(), 3), "sd": round(x.std(), 3), "p_zero": round((x == 0).mean(), 3),
                "p_abs_ge_1": round((x.abs() >= 1).mean(), 3), "p_abs_ge_3": round((x.abs() >= 3).mean(), 3),
                "excess_kurtosis": round(x.kurt(), 2), "q01": float(x.quantile(0.01)), "q05": float(x.quantile(0.05)),
                "q95": float(x.quantile(0.95)), "q99": float(x.quantile(0.99))}
    out["moves"] = {"spread_2015_2025": describe(base.d_spread), "spread_2009_2025": describe(mv[mv.season <= hi].d_spread),
                    "total_2024_2025": describe(tot.d_total),
                    "corr_spread_total_2024_2025": round(float(tot[["d_spread", "d_total"]].corr().iloc[0, 1]), 3),
                    "corr_abs_moves_2024_2025": round(float(np.corrcoef(tot.d_spread.abs(), tot.d_total.abs())[0, 1]), 3)}
    by_season = mv.groupby("season").agg(sd_spread=("d_spread", "std"), p_zero_spread=("d_spread", lambda x: (x == 0).mean()),
                                         sd_total=("d_total", "std"), n=("d_spread", "size")).round(3)
    by_season.to_csv(DATA_PROCESSED / "line_var_moves_by_season.csv")
    n_tot = mv.groupby("season").d_total.count()
    by_season.loc[n_tot < 50, "sd_total"] = np.nan  # total opens are sparse before 2024
    by_line = base.groupby(
        pd.cut(base.spread_open.abs(), [-0.1, 2.5, 5.5, 8.5, 30], labels=["0-2.5", "3-5.5", "6-8.5", "9+"]), observed=True
    ).d_spread.agg(["std", "size"]).round(3)
    out["moves"]["sd_spread_by_abs_open_line"] = by_line["std"].to_dict()

    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    bins = np.arange(-8.25, 8.5, 0.5)
    axes[0].hist(base.d_spread, bins=bins, density=True, color=C["spread"], alpha=0.8, label="2015-2025")
    x = np.linspace(-8, 8, 400)
    axes[0].plot(x, stats.norm.pdf(x, base.d_spread.mean(), base.d_spread.std()), "k--", lw=1, label="normal, same SD")
    axes[0].set(yscale="log", ylim=(1e-4, 1), xlabel="spread close − open (home margin, points)", ylabel="density (log)",
                title=f"Spread moves: SD {base.d_spread.std():.2f}, excess kurtosis {base.d_spread.kurt():.1f}")
    axes[0].legend(fontsize=8)
    axes[1].hist(tot.d_total, bins=bins, density=True, color=C["total"], alpha=0.8)
    axes[1].plot(x, stats.norm.pdf(x, tot.d_total.mean(), tot.d_total.std()), "k--", lw=1)
    axes[1].set(yscale="log", ylim=(1e-4, 1), xlabel="total close − open (points)", title=f"Total moves 2024-25: SD {tot.d_total.std():.2f}")
    axes[2].plot(by_season.index, by_season.sd_spread, "o-", color=C["spread"], label="spread SD")
    axes[2].plot(by_season.index, by_season.sd_total, "o-", color=C["total"], label="total SD")
    axes[2].plot(by_season.index, by_season.p_zero_spread * 4, ":", color="grey", label="P(spread unchanged) × 4")
    axes[2].set(xlabel="season", ylabel="points", title="Open-to-close move size by season")
    axes[2].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    axes[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "line_var_moves.png"); plt.close(fig)


# -- 2. Greeks -------------------------------------------------------------------------------------------------

def section_greeks(prior, out):
    s0, t0 = EXAMPLE["spread"], EXAMPLE["total"]
    rows = []
    for k in np.arange(0.5, 21, 1.0):
        for side in ("home", "away"):
            rows.append(("spread", side, k))
    rows += [("winner", "home", 0.0)] + [("total", "over", k) for k in np.arange(t0 - 14, t0 + 14.1, 1.0)]
    tab = []
    for kind, side, k in rows:
        g = line_greeks(prior, s0, t0, Contract(kind, side, k))
        if kind == "spread":
            z = (k - s0) if side == "home" else (k + s0)  # distance of the strike from the expected margin, own-side
            normal_delta = stats.norm.pdf(z / SIGMA["spread"]) / SIGMA["spread"] * (1 if side == "home" else -1)
        elif kind == "winner":
            normal_delta = stats.norm.pdf(s0 / SIGMA["spread"]) / SIGMA["spread"]
        else:
            normal_delta = np.nan
        normal_total = stats.norm.pdf((k - t0) / SIGMA["total"]) / SIGMA["total"] if kind == "total" else np.nan
        tab.append({"kind": kind, "side": side, "strike": k, **{a: round(b, 5) for a, b in g.items()},
                    "normal_delta_spread": round(normal_delta, 5), "normal_delta_total": round(normal_total, 5)})
    tab = pd.DataFrame(tab)
    tab.to_csv(DATA_PROCESSED / "line_var_greeks_example.csv", index=False)
    home = tab[(tab.kind == "spread") & (tab.side == "home")]
    out["greeks_example"] = {
        "line": EXAMPLE,
        "winner_home": tab[tab.kind == "winner"].iloc[0][["price", "delta_spread", "delta_total", "gamma_spread"]].to_dict(),
        "max_abs_delta_spread_strike": float(home.loc[home.delta_spread.abs().idxmax(), "strike"]),
        "max_delta_spread_cents_per_point": round(100 * home.delta_spread.abs().max(), 2),
        "normal_max_delta_cents_per_point": round(100 * home.normal_delta_spread.abs().max(), 2),
        "max_abs_cross_delta_total_on_spread_contracts_cents": round(100 * tab[tab.kind == "spread"].delta_total.abs().max(), 3),
        "total_atm_delta_cents_per_point": round(100 * tab[tab.kind == "total"].delta_total.abs().max(), 2),
    }

    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    for side, mk in (("home", "o-"), ("away", "s-")):
        d = tab[(tab.kind == "spread") & (tab.side == side)]
        axes[0].plot(d.strike, 100 * d.delta_spread.abs(), mk, color=C["spread"] if side == "home" else "#8172B2", ms=3,
                     label=f"{side} wins by > k (grid)")
        axes[0].plot(d.strike, 100 * d.normal_delta_spread.abs(), "--", color="grey", lw=1)
    axes[0].plot([], [], "--", color="grey", label="normal(line, 12.73)")
    axes[0].set(xlabel="strike k", ylabel="|∂P/∂spread|, cents per point",
                title=f"Spread delta by strike, line home −{s0:g}")
    axes[0].legend(fontsize=7)
    d = tab[tab.kind == "spread"]
    axes[1].plot(d[d.side == "home"].strike, 100 * d[d.side == "home"].gamma_spread, "o-", ms=3, color=C["spread"], label="home strikes")
    axes[1].plot(d[d.side == "away"].strike, 100 * d[d.side == "away"].gamma_spread, "s-", ms=3, color="#8172B2", label="away strikes")
    axes[1].axhline(0, color="k", lw=0.6)
    axes[1].set(xlabel="strike k", ylabel="∂²P/∂spread², cents per point²", title="Spread gamma by strike")
    axes[1].legend(fontsize=7)
    d = tab[tab.kind == "total"]
    axes[2].plot(d.strike, 100 * d.delta_total, "o-", ms=3, color=C["total"], label="grid")
    axes[2].plot(d.strike, 100 * d.normal_delta_total, "--", color="grey", lw=1, label="normal(line, 13.24)")
    axes[2].set(xlabel="total strike", ylabel="∂P/∂total, cents per point", title=f"Total delta by strike, line {t0:g}")
    axes[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "line_var_greeks.png"); plt.close(fig)
    return tab


# -- 3. VaR for reference positions ---------------------------------------------------------------------------

def reference_positions(s0, t0):
    """Illustrative $-notional books on one game; qty is contracts (each pays $1)."""
    fav = "home" if s0 >= 0 else "away"
    fav_k = np.ceil(abs(s0)) - 0.5  # the favourite's strike just inside the line
    t_k = np.floor(t0) + 0.5
    return {
        "long 1,000 home winner": [Contract("winner", "home", 0, 1000)],
        f"long 1,000 {fav} wins by > {fav_k:g}": [Contract("spread", fav, fav_k, 1000)],
        f"long 1,000 over {t_k:g}": [Contract("total", "over", t_k, 1000)],
        f"key-number pin: long {fav} > 2.5, short {fav} > 3.5 (1,000 each)": [Contract("spread", fav, 2.5, 1000), Contract("spread", fav, 3.5, -1000)],
        "market-maker inventory: short 500 of each home strike 0.5-13.5": [Contract("spread", "home", k, -500) for k in np.arange(0.5, 14, 1.0)],
        "mixed: long 1,000 home winner, short 1,000 over": [Contract("winner", "home", 0, 1000), Contract("total", "over", t_k, -1000)],
    }


def settlement_pnl(prior, s0, t0, contracts, lat):
    """Loss distribution if held to the final whistle at today's model price: payoff − cost over the grid."""
    g = tilt(prior, s0, t0)[0]
    payoff = sum(c.qty * c.payoff(g) for c in contracts)
    cost = float(lat.value(contracts, s0, t0))
    flat = np.argsort((payoff - cost).ravel())
    vals, probs = (payoff - cost).ravel()[flat], g.p.ravel()[flat]
    cdf = np.cumsum(probs)
    var99 = -vals[np.searchsorted(cdf, 0.01)]
    var95 = -vals[np.searchsorted(cdf, 0.05)]
    return float(var95), float(var99)


def section_var(prior, lat, scen, out):
    s0, t0 = EXAMPLE["spread"], EXAMPLE["total"]
    ds, dt = scen["primary"]
    cov = np.cov(np.vstack([ds, dt]))
    rows, pnls = [], {}
    for name, pos in reference_positions(s0, t0).items():
        pnl = scenario_pnl(lat, pos, s0, t0, ds, dt)
        pnl_j = scenario_pnl(lat, pos, s0, t0, *scen["joint_2024_25"])
        pnls[name] = pnl
        delta = np.zeros(2)
        for c in pos:
            g = line_greeks(prior, s0, t0, Contract(c.kind, c.side, c.strike, 1.0))
            delta += c.qty * np.array([g["delta_spread"], g["delta_total"]])
        dn_sd = float(np.sqrt(delta @ cov @ delta))
        v95, e95 = var_es(pnl, 0.95)
        v99, e99 = var_es(pnl, 0.99)
        sv95, sv99 = settlement_pnl(prior, s0, t0, pos, lat)
        rows.append({"position": name, "value": round(float(lat.value(pos, s0, t0)), 1),
                     "delta_spread_$": round(delta[0], 1), "delta_total_$": round(delta[1], 1),
                     "VaR95": round(v95, 1), "ES95": round(e95, 1), "VaR99": round(v99, 1), "ES99": round(e99, 1),
                     "VaR99_joint_2024_25": round(var_es(pnl_j, 0.99)[0], 1),
                     "deltaNormal_VaR95": round(1.645 * dn_sd, 1), "deltaNormal_VaR99": round(2.326 * dn_sd, 1),
                     "settlement_VaR95": round(sv95, 1), "settlement_VaR99": round(sv99, 1)})
    tab = pd.DataFrame(rows)
    tab.to_csv(DATA_PROCESSED / "line_var_reference_positions.csv", index=False)
    out["var_example"] = {"line": EXAMPLE, "n_scenarios": int(len(ds)), "positions": tab.to_dict(orient="records")}

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    name = list(pnls)[0]
    p = pnls[name]
    axes[0].hist(p, bins=60, color=C["winner"], alpha=0.85)
    for a, ls in ((0.95, "--"), (0.99, ":")):
        axes[0].axvline(-var_es(p, a)[0], color="k", ls=ls, lw=1, label=f"VaR{int(a * 100)} ${var_es(p, a)[0]:.0f}")
    axes[0].set(xlabel="P&L open→close, $", ylabel="scenarios", title=f"{name}, line home −{s0:g}")
    axes[0].legend(fontsize=8)
    t = tab.set_index("position")
    y = np.arange(len(t))
    axes[1].barh(y + 0.2, t.VaR99, height=0.4, color="#4C72B0", label="historical VaR99 (line moves)")
    axes[1].barh(y - 0.2, t.deltaNormal_VaR99, height=0.4, color="#BBBBBB", label="delta-normal VaR99")
    axes[1].set_yticks(y, [s if len(s) < 42 else s[:40] + "…" for s in t.index], fontsize=7)
    axes[1].set(xlabel="$ at risk, open→close", title="Line VaR99 by position")
    axes[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "line_var_positions.png"); plt.close(fig)
    return tab


# -- 4. backtest on 2026 Kalshi games -----------------------------------------------------------------------------

HORIZONS = [6, 12, 24, 48, 72, 96, 120, 144]
START_H = 144  # ladders are fit-able ~6 days out in ~80% of games, about when the book opener is taken


def kalshi_hourly(sched):
    """Hourly two-sided mids for every 2026 regular-season market of a completed game, h = hours to kickoff."""
    cd = pd.read_parquet(DATA_RAW / "kalshi_candles.parquet")
    markets = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")
    ev = link_to_schedule(parse_events(markets), sched).dropna(subset=["game_id"])
    ev = ev.merge(sched[["game_id", "gameday", "gametime", "game_type", "home_team", "home_score"]], on="game_id")
    ev["kickoff"] = kickoff_utc(ev)
    ev = ev[(ev.game_type == "REG") & ev.home_score.notna()]
    mk = markets.merge(ev[["event_ticker", "game_id", "kickoff", "home_team"]], on="event_ticker")
    cd = cd.merge(mk[["ticker", "kind", "game_id", "kickoff", "home_team", "floor_strike"]], on="ticker")
    cd = cd.dropna(subset=["bid_close", "ask_close"])
    cd = cd[(cd.bid_close > 0) & (cd.ask_close < 1)].copy()
    cd["mid"] = (cd.bid_close + cd.ask_close) / 2
    cd["spread_c"] = (100 * (cd.ask_close - cd.bid_close)).round(1)
    cd["h"] = ((cd.kickoff - cd.end_time).dt.total_seconds() / 3600).round().astype(int)
    cd = cd[(cd.h >= 1) & (cd.spread_c <= 6) & cd.mid.between(0.03, 0.97)]
    return cd


def implied_lines(lat, cd, close_total):
    """Kalshi-implied (spread, total) per game-hour from the ladder mids; needs >= 4 spread and >= 4 total strikes.

    The winner market is used when quoted (weight 3) but not required: its hourly candles are truncated for
    long-listed markets, and the spread ladder pins the line on its own.
    """
    rows, contracts = [], {}
    for gid, g in cd.groupby("game_id"):
        tick = g.drop_duplicates("ticker").set_index("ticker")
        cs = {t: contract_from_market(t, r.kind, r.floor_strike, r.home_team) for t, r in tick.iterrows()}
        contracts.update(cs)
        surf = {t: lat.surface(c) for t, c in cs.items()}
        t0 = close_total.get(gid, 45.0)
        for h, x in g.groupby("h"):
            k = x.kind.value_counts()
            if k.get("spread", 0) < 4 or k.get("total", 0) < 4:
                continue
            S = np.stack([surf[t] for t in x.ticker])
            w = np.where(x.kind == "winner", 3.0, 1.0)
            s, t, rmse = lat.implied_line(S, x.mid.to_numpy(), w, total0=t0)
            rows.append((gid, h, s, t, rmse, len(x)))
    return pd.DataFrame(rows, columns=["game_id", "h", "spread", "total", "rmse", "n"]), contracts


def nearest(il, h, tol=3):
    """Implied line at the fitted hour closest to h (within tol hours) for each game."""
    x = il[(il.h - h).abs() <= tol].assign(d=lambda d: (d.h - h).abs()).sort_values("d")
    return x.drop_duplicates("game_id").set_index("game_id")


def section_backtest(lat, mv, scen, sched, out):
    cd = kalshi_hourly(sched)
    mv26 = mv[mv.season == 2026].set_index("game_id")
    il, contracts = implied_lines(lat, cd, mv26.total_close.to_dict())
    il.to_csv(DATA_PROCESSED / "line_var_implied_lines.csv", index=False)
    bt = {"n_games_with_candles": int(cd.game_id.nunique()), "n_games_fitted": int(il.game_id.nunique())}

    # (a) fit quality and agreement with the book close
    end = nearest(il, 1)
    j = end.join(mv26[["spread_close", "total_close", "spread_open", "total_open"]], how="inner")
    bt["fit"] = {"n_games": int(len(j)), "median_rmse_cents_last_hour": round(100 * float(end.rmse.median()), 2),
                 "median_rmse_cents_all_hours": round(100 * float(il.rmse.median()), 2),
                 "kalshi_minus_book_close_spread_mean": round(float((j.spread - j.spread_close).mean()), 3),
                 "kalshi_minus_book_close_spread_mae": round(float((j.spread - j.spread_close).abs().mean()), 3),
                 "kalshi_minus_book_close_total_mean": round(float((j.total - j.total_close).mean()), 3),
                 "kalshi_minus_book_close_total_mae": round(float((j.total - j.total_close).abs().mean()), 3)}

    # (b) how line variance accrues toward kickoff
    curve, moves_h = [], {}
    for H in HORIZONS:
        st = nearest(il, H).join(end[["spread", "total"]], rsuffix="_end", how="inner")
        ds, dt = st.spread_end - st.spread, st.total_end - st.total
        moves_h[H] = pd.DataFrame({"ds": ds, "dt": dt, "week": [int(g.split("_")[1]) for g in st.index]})
        curve.append({"hours_before": H, "n": len(st), "sd_spread": ds.std(), "sd_total": dt.std(),
                      "var_share_spread": ds.var(), "var_share_total": dt.var(),
                      "p_abs_spread_ge_1": (ds.abs() >= 1).mean(), "kurt_spread": ds.kurt()})
    curve = pd.DataFrame(curve)
    for k in ("spread", "total"):  # share of the 6-day line variance still to come at each horizon
        curve[f"var_share_{k}"] = curve[f"var_share_{k}"] / curve.loc[curve.hours_before == START_H, f"var_share_{k}"].iloc[0]
    curve = curve.round(3)
    curve.to_csv(DATA_PROCESSED / "line_var_horizon_curve.csv", index=False)
    bt["horizon_curve"] = curve.to_dict(orient="records")
    bt["book_open_close_2026"] = {"n": int(len(mv26)), "sd_spread": round(float(mv26.d_spread.std()), 3),
                                  "sd_total": round(float(mv26.d_total.std()), 3)}
    bt["scenario_sd_spread_2015_2025"] = round(float(np.std(scen["primary"][0], ddof=1)), 3)

    def horizon_scale(H, week):
        """SD of the Kalshi-implied line change from H hours out, relative to 6 days out, leaving out `week`."""
        a, b = moves_h[H], moves_h[START_H]
        a, b = a[a.week != week], b[b.week != week]
        return a.ds.std() / b.ds.std(), a.dt.std() / b.dt.std()

    # (c) every contract quoted at the start hour and in the last pre-kickoff hours: realised vs line-implied change
    ds_scen, dt_scen = scen["primary"]
    pairs = []
    for H in (START_H, 72, 24):
        st = nearest(il, H)
        a = cd.assign(dh=(cd.h - H).abs()).query("dh <= 3").sort_values("dh").drop_duplicates("ticker")
        b = cd.assign(dh=(cd.h - 1).abs()).query("dh <= 3").sort_values("dh").drop_duplicates("ticker")
        pair = a[["ticker", "game_id", "kind", "mid"]].merge(b[["ticker", "mid"]], on="ticker", suffixes=("_0", "_1"))
        pair = pair[pair.game_id.isin(st.index) & pair.game_id.isin(end.index) & pair.mid_0.between(0.05, 0.95)].copy()
        pair["H"] = H
        pair["week"] = [int(g.split("_")[1]) for g in pair.game_id]
        pair[["s0", "t0"]] = st.loc[pair.game_id, ["spread", "total"]].to_numpy()
        pair[["s1", "t1"]] = end.loc[pair.game_id, ["spread", "total"]].to_numpy()
        pairs.append(pair)
    d = pd.concat(pairs, ignore_index=True)
    d["realised"] = d.mid_1 - d.mid_0
    model0, line_pred, book_pred = [], [], []
    for r in d.itertuples():
        surf = lat.surface(contracts[r.ticker])
        m0 = float(lat.interp(surf, r.s0, r.t0))
        model0.append(m0)
        line_pred.append(float(lat.interp(surf, r.s1, r.t1)) - m0)
        if r.game_id in mv26.index:
            bk = mv26.loc[r.game_id]
            book_pred.append(float(lat.interp(surf, r.s0 + bk.d_spread, r.t0 + np.nan_to_num(bk.d_total))) - m0)
        else:
            book_pred.append(np.nan)
    d["model0"], d["line_pred"], d["book_pred"] = model0, line_pred, book_pred
    d["resid"] = d.realised - d.line_pred

    # (d) VaR exceedances, long and short one contract, under three VaR models:
    #   book      scenarios = book open->close moves 2015-2025, unscaled
    #   scaled    moves scaled by the Kalshi horizon curve (leave-one-week-out)
    #   scaled+ε  plus a non-line residual drawn from other weeks' residuals of the same kind and horizon
    q = {}
    for r in d.itertuples():
        surf = lat.surface(contracts[r.ticker])
        ks, kt = (1.0, 1.0) if r.H == START_H else horizon_scale(r.H, r.week)
        pnl_book = lat.interp(surf, r.s0 + ds_scen, r.t0 + dt_scen) - r.model0
        pnl_sc = pnl_book if r.H == START_H else lat.interp(surf, r.s0 + ks * ds_scen, r.t0 + kt * dt_scen) - r.model0
        pool = d.resid[(d.H == r.H) & (d.kind == r.kind) & (d.week != r.week)].to_numpy()
        pnl_eps = pnl_sc + rng.choice(pool, size=len(pnl_sc))
        for name, pnl in (("book", pnl_book), ("scaled", pnl_sc), ("scaled+resid", pnl_eps)):
            lo95, lo99, hi95, hi99 = np.quantile(pnl, [0.05, 0.01, 0.95, 0.99])
            q.setdefault(name, []).append((lo95, lo99, hi95, hi99))
    for name, v in q.items():
        v = np.array(v)
        d[f"{name}:exc95"] = 0.5 * ((d.realised < v[:, 0]).astype(float) + (d.realised > v[:, 2]))
        d[f"{name}:exc99"] = 0.5 * ((d.realised < v[:, 1]).astype(float) + (d.realised > v[:, 3]))
        d[f"{name}:VaR95"] = 0.5 * (v[:, 2] - v[:, 0])
    d.to_csv(DATA_PROCESSED / "line_var_backtest_contracts.csv", index=False)

    def r2(y, yhat):
        return float(1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum())

    def block_ci(g, col, n_boot=2000):
        """95% interval of an exceedance rate, resampling whole games (contracts in a game are correlated)."""
        per = g.groupby("game_id")[col].agg(["sum", "size"])
        idx = rng.integers(0, len(per), size=(n_boot, len(per)))
        rates = per["sum"].to_numpy()[idx].sum(1) / per["size"].to_numpy()[idx].sum(1)
        return [round(float(x), 3) for x in np.quantile(rates, [0.025, 0.975])]

    res, tidy = {}, []
    for H, dh in d.groupby("H"):
        by = {}
        for kind, g in list(dh.groupby("kind")) + [("all", dh)]:
            gb = g.dropna(subset=["book_pred"])
            e = {"n": int(len(g)), "n_games": int(g.game_id.nunique()), "sd_realised_cents": round(100 * g.realised.std(), 2),
                 "r2_kalshi_line": round(r2(g.realised, g.line_pred), 3), "resid_sd_cents": round(100 * g.resid.std(), 2),
                 "r2_book_move": round(r2(gb.realised, gb.book_pred), 3)}
            for name in q:
                e[f"{name}:exc95"] = round(float(g[f"{name}:exc95"].mean()), 3)
                e[f"{name}:exc99"] = round(float(g[f"{name}:exc99"].mean()), 3)
                e[f"{name}:VaR95_cents"] = round(100 * float(g[f"{name}:VaR95"].mean()), 2)
                tidy.append({"H": H, "kind": kind, "model": name, "exc95": e[f"{name}:exc95"], "exc99": e[f"{name}:exc99"],
                             "mean_VaR95_cents": e[f"{name}:VaR95_cents"]})
            if kind == "all":
                for name in q:
                    e[f"{name}:exc95_game_block_ci"] = block_ci(g, f"{name}:exc95")
            by[kind] = e
        res[f"{H}h"] = by
    pd.DataFrame(tidy).to_csv(DATA_PROCESSED / "line_var_backtest_exceedances.csv", index=False)
    bt["contracts"] = res
    allc = d
    out["backtest_2026"] = bt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    gid = j.assign(mv=(j.spread_close - j.spread_open).abs()).sort_values("mv").index[-1]
    path = il[il.game_id == gid].sort_values("h")
    axes[0].plot(-path.h, path.spread, color=C["spread"], label="Kalshi-implied spread")
    axes[0].axhline(j.loc[gid, "spread_open"], color="grey", ls=":", label="book open")
    axes[0].axhline(j.loc[gid, "spread_close"], color="k", ls="--", lw=1, label="book close")
    ax2 = axes[0].twinx()
    ax2.plot(-path.h, path.total, color=C["total"], alpha=0.6)
    ax2.set_ylabel("implied total", color=C["total"])
    axes[0].set(xlabel="hours to kickoff", ylabel="home margin", title=f"{gid}: implied line path")
    axes[0].legend(fontsize=7, loc="lower left")
    axes[1].plot(curve.hours_before, curve.sd_spread, "o-", color=C["spread"], label="Kalshi-implied spread")
    axes[1].plot(curve.hours_before, curve.sd_total, "o-", color=C["total"], label="Kalshi-implied total")
    axes[1].axhline(bt["scenario_sd_spread_2015_2025"], color=C["spread"], ls="--", lw=1, label="book open→close 2015-25")
    axes[1].axhline(bt["book_open_close_2026"]["sd_spread"], color=C["spread"], ls=":", lw=1, label="book open→close 2026")
    axes[1].set(xlabel="hours before kickoff (start of hold)", ylabel="SD of line change to kickoff, points",
                title="Line variance still to come", xlim=(0, 150))
    axes[1].legend(fontsize=7)
    d = allc[allc.H == START_H]
    for kind in ("spread", "total", "winner"):
        g = d[d.kind == kind]
        axes[2].scatter(100 * g.line_pred, 100 * g.realised, s=5, alpha=0.4, color=C[kind], label=kind)
    lim = 100 * d.realised.abs().quantile(0.995)
    axes[2].plot([-lim, lim], [-lim, lim], "k--", lw=0.8)
    axes[2].set(xlim=(-lim, lim), ylim=(-lim, lim), xlabel="line-implied change, cents", ylabel="realised mid change, cents",
                title=f"Price change {START_H}h→kickoff vs line move (R² {res[f'{START_H}h']['all']['r2_kalshi_line']:.2f})")
    axes[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "line_var_backtest.png"); plt.close(fig)

    tidy = pd.DataFrame(tidy)
    tidy = tidy[tidy.kind == "all"]
    models = list(q)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    for ax, col, target in ((axes[0], "exc95", 0.05), (axes[1], "exc99", 0.01)):
        x = np.arange(3)
        for i, name in enumerate(models):
            v = tidy[tidy.model == name].set_index("H").reindex([START_H, 72, 24])[col]
            ax.bar(x + (i - 1) * 0.27, 100 * v, width=0.27, label=name, color=["#BBBBBB", "#4C72B0", "#DD8452"][i])
        ax.axhline(100 * target, color="k", ls="--", lw=1)
        ax.set_xticks(x, [f"{START_H}h", "72h", "24h"])
        ax.set(xlabel="hold from H hours before kickoff to kickoff", ylabel="exceedance rate, %",
               title=f"VaR{int(100 * (1 - target))} exceedances, all 2026 contracts (target {100 * target:g}%)")
        ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "line_var_coverage.png"); plt.close(fig)


def main():
    out = {}
    sched = load_schedules()
    prior = build_prior(sched)
    lat = get_lattice(prior, refresh="--refresh" in sys.argv)
    nf = pd.read_csv(DATA_RAW / "external" / "nfelo_games.csv", index_col=0)
    mv = line_moves(nf)
    scen = scenarios(mv)
    section_moves(mv, out)
    section_greeks(prior, out)
    section_var(prior, lat, scen, out)
    if "--no-backtest" not in sys.argv:
        section_backtest(lat, mv, scen, sched, out)
    json.dump(out, open(DATA_PROCESSED / "line_var_summary.json", "w"), indent=2, default=float)
    print(json.dumps(out, indent=2, default=float))


if __name__ == "__main__":
    main()
