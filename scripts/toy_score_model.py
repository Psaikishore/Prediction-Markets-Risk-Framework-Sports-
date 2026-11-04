"""Toy example: build p(home, away) for one upcoming game and price its Kalshi contracts.

Game: Pittsburgh at Cleveland, Thu 2026-10-01. Inputs:
  * data/raw/nflverse_schedules.parquet      historical scores 2015-2026 (prior) and this game's closing lines
  * data/processed/toy_live_quotes_PITCLE.csv Kalshi order-book snapshot taken 2026-09-30 (bid/ask per contract)
Outputs: reports/figures/toy_*.png and data/processed/toy_*.csv
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_PROCESSED, FIGURES
from pmrisk.nfl import completed_games, load_schedules
from pmrisk.score_model import ScoreGrid, empirical_grid, price_ladder, tilt, tilt_features

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
GAME_ID, HOME, AWAY = "2026_04_PIT_CLE", "CLE", "PIT"


def main():
    out = {}
    sched = load_schedules()
    hist = completed_games(sched)
    hist = hist[hist.game_id != GAME_ID]
    game = sched.set_index("game_id").loc[GAME_ID]
    quotes = pd.read_csv(DATA_PROCESSED / "toy_live_quotes_PITCLE.csv")
    spread, total = float(game.spread_line), float(game.total_line)
    out["game"] = {"home": HOME, "away": AWAY, "kickoff": f"{game.gameday:%Y-%m-%d} {game.gametime}",
                   "book_spread_home": spread, "book_total": total,
                   "kalshi_home_win_mid": float(quotes.loc[quotes.ticker.str.endswith(f"-{HOME}"), "mid"].iloc[0])}

    # ---- 1. Prior: empirical score grid, 2015-2026 ----------------------------------------------------
    prior = empirical_grid(hist, smooth=0.02)
    out["prior"] = {"n_games": int(len(hist)), "mean_margin": round(prior.mean_margin(), 3), "mean_total": round(prior.mean_total(), 3),
                    "p_home_win": round(prior.p_home_win(), 4), "nonzero_cells": int((prior.p > 1e-6).sum())}

    # ---- 2a. Tilt to the sportsbook closing line -----------------------------------------------------------
    book_grid, lam_book = tilt(prior, spread, total)
    out["tilt_book"] = {"lambda_margin": round(float(lam_book[0]), 5), "lambda_total": round(float(lam_book[1]), 5),
                        "mean_margin": round(book_grid.mean_margin(), 3), "mean_total": round(book_grid.mean_total(), 3),
                        "p_home_win": round(book_grid.p_home_win(), 4)}

    # ---- 2b. Calibrate the same two parameters to Kalshi mids instead ----------------------------------------
    def ladder_loss(x):
        g, _ = tilt(prior, x[0], x[1])
        pr = price_ladder(g, quotes, HOME)
        w = np.where(pr.kind == "winner", 3.0, 1.0)  # winner market is the deepest
        return float((w * (pr.model - pr.mid) ** 2).sum())

    sol = optimize.minimize(ladder_loss, x0=[spread, total], method="Nelder-Mead", options={"xatol": 0.01, "fatol": 1e-7})
    mkt_grid, lam_mkt = tilt(prior, sol.x[0], sol.x[1])
    out["tilt_market"] = {"implied_spread_home": round(float(sol.x[0]), 3), "implied_total": round(float(sol.x[1]), 3),
                          "p_home_win": round(mkt_grid.p_home_win(), 4), "rmse_vs_mids_cents": round(100 * np.sqrt(sol.fun / len(quotes)), 2)}

    # ---- 2c. Three-parameter tilt (margin, total, margin²) calibrated to Kalshi mids ------------------------------
    def ladder_loss3(lam):
        pr = price_ladder(tilt_features(prior, lam), quotes, HOME)
        w = np.where(pr.kind == "winner", 3.0, 1.0)
        return float((w * (pr.model - pr.mid) ** 2).sum())

    sol3 = optimize.minimize(ladder_loss3, x0=[lam_book[0], lam_book[1], 0.0], method="Nelder-Mead",
                             options={"xatol": 1e-5, "fatol": 1e-9, "maxiter": 4000})
    mkt3_grid = tilt_features(prior, sol3.x)
    out["tilt_market3"] = {"lambda": [round(float(v), 5) for v in sol3.x], "mean_margin": round(mkt3_grid.mean_margin(), 3),
                           "mean_total": round(mkt3_grid.mean_total(), 3), "sd_margin": round(float(np.sqrt((mkt3_grid.p * (mkt3_grid.margin - mkt3_grid.mean_margin()) ** 2).sum())), 2),
                           "p_home_win": round(mkt3_grid.p_home_win(), 4), "rmse_vs_mids_cents": round(100 * np.sqrt(sol3.fun / len(quotes)), 2)}
    for name, g in [("prior", prior), ("book_tilt", book_grid)]:
        out[f"sd_margin_{name}"] = round(float(np.sqrt((g.p * (g.margin - g.mean_margin()) ** 2).sum())), 2)

    # ---- 3. Price every contract under prior / book-tilt / market-tilt / normal ----------------------------------------
    pr = price_ladder(book_grid, quotes, HOME).rename(columns={"model": "book_tilt"})
    pr["prior"] = price_ladder(prior, quotes, HOME).model
    pr["market_tilt"] = price_ladder(mkt_grid, quotes, HOME).model
    pr["market_tilt3"] = price_ladder(mkt3_grid, quotes, HOME).model
    sd = 12.73

    def normal_price(r):
        team = r.ticker.rsplit("-", 1)[-1].rstrip("0123456789")
        if r.kind == "winner":
            p = stats.norm.cdf(spread / sd)
            return p if team == HOME else 1 - p
        if r.kind == "spread":
            return 1 - stats.norm.cdf((r.floor_strike - spread) / sd) if team == HOME else stats.norm.cdf((-r.floor_strike - spread) / sd)
        return 1 - stats.norm.cdf((r.floor_strike - total) / 13.24)

    pr["normal"] = pr.apply(normal_price, axis=1)
    pr["edge_book_tilt_c"] = 100 * (pr.book_tilt - pr.mid)
    pr["outside_spread"] = (pr.book_tilt > pr.ask) | (pr.book_tilt < pr.bid)
    cols = ["ticker", "kind", "title", "floor_strike", "bid", "ask", "mid", "prior", "book_tilt", "market_tilt", "market_tilt3", "normal", "edge_book_tilt_c", "outside_spread"]
    pr = pr[cols].sort_values(["kind", "floor_strike"])
    pr.round(4).to_csv(DATA_PROCESSED / "toy_prices_PITCLE.csv", index=False)
    for m in ["prior", "book_tilt", "market_tilt", "market_tilt3", "normal"]:
        out[f"mae_vs_mid_cents_{m}"] = round(float(100 * (pr[m] - pr.mid).abs().mean()), 2)
        out[f"mae_vs_mid_cents_{m}_by_kind"] = (100 * (pr[m] - pr.mid).abs()).groupby(pr.kind).mean().round(2).to_dict()
    out["n_contracts"] = int(len(pr))
    out["n_book_tilt_outside_bid_ask"] = int(pr.outside_spread.sum())
    out["contracts_outside_bid_ask"] = pr[pr.outside_spread][["title", "bid", "ask", "book_tilt"]].round(3).to_dict("records")

    # ---- 4. Figures --------------------------------------------------------------------------------------
    # 4a margin pmf: prior vs tilted vs normal
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    ks = np.arange(-35, 36)
    pm_prior, pm_book = prior.margin_pmf().reindex(ks, fill_value=0), book_grid.margin_pmf().reindex(ks, fill_value=0)
    axes[0].bar(ks - 0.2, pm_prior.values, width=0.4, color="#BBBBBB", label="prior (all games 2015–26)")
    axes[0].bar(ks + 0.2, pm_book.values, width=0.4, color="#4C72B0", label=f"tilted to spread {spread:+.1f}, total {total}")
    axes[0].plot(ks, mkt3_grid.margin_pmf().reindex(ks, fill_value=0).values, "o-", ms=2.5, lw=0.8, color="#C44E52", label="3-param tilt to Kalshi")
    axes[0].plot(ks, stats.norm.pdf(ks, spread, sd), "k--", lw=1.2, label=f"N({spread:+.1f}, {sd}²)")
    axes[0].axvline(0, color="k", lw=0.6)
    axes[0].set(xlabel=f"margin  ({HOME} − {AWAY})", ylabel="probability", title="Margin distribution"); axes[0].legend(fontsize=8)
    ts = np.arange(10, 80)
    axes[1].bar(ts - 0.2, prior.total_pmf().reindex(ts, fill_value=0).values, width=0.4, color="#BBBBBB", label="prior")
    axes[1].bar(ts + 0.2, book_grid.total_pmf().reindex(ts, fill_value=0).values, width=0.4, color="#55A868", label="tilted")
    axes[1].plot(ts, stats.norm.pdf(ts, total, 13.24), "k--", lw=1.2, label=f"N({total}, 13.24²)")
    axes[1].set(xlabel="total points", title="Total distribution"); axes[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "toy_margin_total.png"); plt.close(fig)

    # 4b joint grid heatmap (tilted) with the main contract boundaries
    fig, ax = plt.subplots(figsize=(6.2, 5.5))
    lim = 55
    im = ax.imshow(book_grid.p[:lim, :lim], origin="lower", cmap="viridis", vmax=np.quantile(book_grid.p[:lim, :lim], 0.999))
    ax.plot([0, lim], [0, lim], "w-", lw=0.8, label="tie")
    ax.plot([0, lim], [-2.5, lim - 2.5], "w--", lw=0.8, label=f"{HOME} −2.5 (book spread)")
    ax.plot([0, total], [total, 0], "r--", lw=0.8, label=f"total {total}")
    ax.set(xlabel=f"{AWAY} points", ylabel=f"{HOME} points", title=f"Tilted joint p({HOME}, {AWAY})"); ax.legend(fontsize=7, loc="upper left")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout(); fig.savefig(FIGURES / "toy_joint_grid.png"); plt.close(fig)

    # 4c ladder comparison: model vs Kalshi bid/ask
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for ax, kind in zip(axes, ["spread", "total"]):
        d = pr[pr.kind == kind].copy()
        if kind == "spread":
            team = d.ticker.str.rsplit("-", n=1).str[-1].str.rstrip("0123456789")
            d["x"] = np.where(team == HOME, d.floor_strike, -d.floor_strike)
            d["mkt_cdf"] = np.where(team == HOME, 1 - d.mid, d.mid)
            d["bid_cdf"] = np.where(team == HOME, 1 - d.ask, d.bid); d["ask_cdf"] = np.where(team == HOME, 1 - d.bid, d.ask)
            for m in ["book_tilt", "market_tilt", "market_tilt3", "normal", "prior"]:
                d[m + "_cdf"] = np.where(team == HOME, 1 - d[m], d[m])
            xlabel = f"k  (P[{HOME} margin ≤ k])"
        else:
            d["x"] = d.floor_strike
            d["mkt_cdf"], d["bid_cdf"], d["ask_cdf"] = 1 - d.mid, 1 - d.ask, 1 - d.bid
            for m in ["book_tilt", "market_tilt", "market_tilt3", "normal", "prior"]:
                d[m + "_cdf"] = 1 - d[m]
            xlabel = "k  (P[total ≤ k])"
        d = d.sort_values("x")
        ax.fill_between(d.x, d.bid_cdf, d.ask_cdf, color="#DD8452", alpha=0.35, label="Kalshi bid–ask")
        ax.plot(d.x, d.mkt_cdf, "o", color="#DD8452", ms=3, label="Kalshi mid")
        ax.plot(d.x, d.prior_cdf, ":", color="#999999", label="prior")
        ax.plot(d.x, d.book_tilt_cdf, "-", color="#4C72B0", label="tilted to book line")
        ax.plot(d.x, d.market_tilt_cdf, "-", color="#55A868", label="2-param tilt to Kalshi mids")
        ax.plot(d.x, d.market_tilt3_cdf, "-", color="#C44E52", label="3-param tilt (+margin²) to Kalshi mids")
        ax.plot(d.x, d.normal_cdf, "k--", lw=1, label="normal")
        ax.set(xlabel=xlabel, ylabel="implied CDF", title=f"{kind} ladder: model vs market"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "toy_ladders.png"); plt.close(fig)

    # 4d pricing error per contract, in cents
    fig, ax = plt.subplots(figsize=(11, 4))
    d = pr.reset_index(drop=True)
    for m, c in [("normal", "k"), ("book_tilt", "#4C72B0"), ("market_tilt", "#55A868"), ("market_tilt3", "#C44E52")]:
        ax.plot(d.index, 100 * (d[m] - d.mid), "o-", ms=3, lw=0.8, color=c, label=m, alpha=0.85)
    ax.fill_between(d.index, 100 * (d.bid - d.mid), 100 * (d.ask - d.mid), color="#DD8452", alpha=0.3, label="bid–ask")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(d.index); ax.set_xticklabels(d.title.str.replace(" Steelers| Browns| points|Full Game: ", "", regex=True), rotation=90, fontsize=6)
    ax.set(ylabel="model − Kalshi mid (cents)", title="Pricing error per contract"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "toy_pricing_error.png"); plt.close(fig)

    # ---- 5. Key-number and in-play illustrations ------------------------------------------------------------
    out["p_margin_exact"] = {str(k): round(float(pm_book.get(k, 0)), 4) for k in [-7, -3, -1, 0, 1, 3, 6, 7, 10]}
    out["push_risk_if_line_were_-3"] = round(float(pm_book.get(-3, 0)), 4)
    # Conditioning example: CLE leads 10-7. The grid can only condition on the final score being
    # consistent with that; a real in-play model also needs the clock. Shown here as the
    # "final score dominates (h>=10, a>=7)" restriction to illustrate the mechanics.
    cond = book_grid.condition((book_grid.h >= 10) & (book_grid.a >= 7))
    out["conditioning_demo"] = {"restriction": "final CLE>=10 and PIT>=7", "p_home_win": round(cond.p_home_win(), 4),
                                "mean_total": round(cond.mean_total(), 2)}

    (DATA_PROCESSED / "toy_summary_PITCLE.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(pr.drop(columns=["ticker"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
