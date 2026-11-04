"""Quoted spread, depth-proxy and open-interest analysis from hourly Kalshi candlesticks.

Writes figures to reports/figures and tables to data/processed/candles_eda_*.csv.
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

from pmrisk import DATA_PROCESSED, DATA_RAW, FIGURES
from pmrisk.link import kickoff_utc, link_to_schedule, parse_events
from pmrisk.nfl import load_schedules

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
C = {"winner": "#4C72B0", "spread": "#DD8452", "total": "#55A868"}
BUCKETS = [-np.inf, -180, -60, 0, 60, 180, 24 * 60, 3 * 24 * 60, 7 * 24 * 60, np.inf]
LABELS = ["in-play >3h", "in-play 1-3h", "in-play <1h", "0-1h", "1-3h", "3-24h", "1-3d", "3-7d", ">7d"]


def main():
    summary = {}
    cd = pd.read_parquet(DATA_RAW / "kalshi_candles.parquet")
    markets = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")
    sched = load_schedules()
    ev = link_to_schedule(parse_events(markets), sched).dropna(subset=["game_id"])
    ev = ev.merge(sched[["game_id", "gameday", "gametime", "game_type", "spread_line", "total_line"]], on="game_id")
    ev["kickoff"] = kickoff_utc(ev)
    mk = markets.merge(ev[["event_ticker", "game_id", "kickoff", "spread_line", "total_line"]], on="event_ticker", how="inner")
    cd = cd.merge(mk[["ticker", "kind", "event_ticker", "game_id", "kickoff", "floor_strike", "spread_line", "total_line", "result"]], on="ticker", how="inner")

    # Quoted spread at the hourly close; both quotes must exist. Prices are in dollars, spread in cents.
    cd = cd.dropna(subset=["bid_close", "ask_close"])
    cd = cd[(cd.bid_close > 0) & (cd.ask_close < 1)]
    cd["spread_c"] = (100 * (cd.ask_close - cd.bid_close)).round(1)
    cd["mid"] = (cd.ask_close + cd.bid_close) / 2
    cd["mins_to_kick"] = (cd.kickoff - cd.end_time).dt.total_seconds() / 60
    cd["bucket"] = pd.cut(cd.mins_to_kick, BUCKETS, labels=LABELS)
    cd["hourly_return"] = cd.groupby("ticker").mid.diff()
    summary["n_candles"] = int(len(cd))
    summary["n_markets"] = int(cd.ticker.nunique())
    summary["n_games"] = int(cd.game_id.nunique())

    # --- 1. Spread by time to kickoff and market type ----------------------------------------
    sp = cd.groupby(["bucket", "kind"], observed=True).spread_c.agg(median="median", mean="mean", p90=lambda s: s.quantile(0.9), n="size")
    sp.round(2).to_csv(DATA_PROCESSED / "candles_eda_spread_by_time.csv")
    mean_ = sp["mean"].unstack().reindex(LABELS[::-1])
    p90 = sp["p90"].unstack().reindex(LABELS[::-1])
    tick = cd.groupby(["bucket", "kind"], observed=True).spread_c.apply(lambda s: (s <= 1.0).mean()).unstack().reindex(LABELS[::-1])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for k in mean_.columns:
        axes[0].plot(mean_.index, mean_[k], "o-", color=C[k], label=f"{k} mean")
        axes[0].plot(p90.index, p90[k], "--", color=C[k], alpha=0.7, label=f"{k} p90")
    axes[0].set(ylabel="quoted spread (cents)", xlabel="time before kickoff", title="Bid–ask spread at hourly close (tick = 1¢)"); axes[0].legend(fontsize=7, ncol=3)
    tick.plot(ax=axes[1], marker="o", color=[C[k] for k in tick.columns])
    axes[1].set(ylabel="share of hours quoted at 1¢", xlabel="time before kickoff", title="How often the book is at the minimum tick", ylim=(0, 1.02))
    for ax in axes: plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
    fig.tight_layout(); fig.savefig(FIGURES / "candles_spread_by_time.png"); plt.close(fig)
    summary["mean_spread_cents"] = {k: {b: round(float(v), 2) for b, v in mean_[k].dropna().items()} for k in mean_.columns}
    summary["share_at_1c"] = {k: {b: round(float(v), 3) for b, v in tick[k].dropna().items()} for k in tick.columns}

    # --- 2. Spread vs price level (moneyness) and vs distance from the line ----------------------
    cd["mid_bin"] = pd.cut(cd.mid, np.arange(0, 1.01, 0.1))
    pre = cd[cd.mins_to_kick > 0]
    by_mid = pre.groupby(["kind", "mid_bin"], observed=True).spread_c.agg(median="median", mean="mean", n="size").round(2)
    by_mid.to_csv(DATA_PROCESSED / "candles_eda_spread_by_mid.csv")
    lad = pre[pre.kind.isin(["spread", "total"])].copy()
    lad["dist"] = np.where(lad.kind == "total", (lad.floor_strike - lad.total_line).abs(), (lad.floor_strike - lad.spread_line.abs()).abs())
    lad["dist_bin"] = pd.cut(lad.dist, [-0.1, 3, 7, 14, 40])
    by_dist = lad.groupby(["kind", "dist_bin"], observed=True).agg(spread_median=("spread_c", "median"), spread_mean=("spread_c", "mean"), volume=("volume", "sum"), n=("spread_c", "size")).round(2)
    by_dist.to_csv(DATA_PROCESSED / "candles_eda_spread_by_distance.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for k in ["winner", "spread", "total"]:
        d = by_mid.loc[k]["mean"]
        axes[0].plot([iv.mid for iv in d.index], d.values, "o-", color=C[k], label=k)
    axes[0].set(xlabel="mid price", ylabel="mean spread (cents)", title="Pre-game spread by price level"); axes[0].legend()
    for k in ["spread", "total"]:
        d = by_dist.loc[k]
        axes[1].bar(np.arange(len(d)) + (0 if k == "spread" else 0.4), d.spread_mean, width=0.4, color=C[k], label=k)
    axes[1].set_xticks(np.arange(len(d)) + 0.2); axes[1].set_xticklabels(["0–3", "3–7", "7–14", "14+"])
    axes[1].set(xlabel="|strike − closing line| (points)", ylabel="mean spread (cents)", title="Pre-game spread by distance from the line"); axes[1].legend()
    fig.tight_layout(); fig.savefig(FIGURES / "candles_spread_by_level.png"); plt.close(fig)

    # --- 3. Open interest: build-up and per-game exposure ---------------------------------------------
    oi = cd.groupby(["bucket", "kind"], observed=True).open_interest.median().unstack().reindex(LABELS[::-1])
    oi.round(0).to_csv(DATA_PROCESSED / "candles_eda_oi_by_time.csv")
    last_oi = cd.sort_values("end_time").groupby("ticker").open_interest.last()
    game_oi = mk.set_index("ticker").join(last_oi).groupby(["game_id", "kind"]).open_interest.sum().unstack()
    game_oi.round(0).to_csv(DATA_PROCESSED / "candles_eda_oi_per_game.csv")
    summary["peak_oi_per_game_median"] = game_oi.median().round(0).to_dict()
    summary["peak_oi_per_game_max"] = game_oi.max().round(0).to_dict()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    oi.plot(ax=axes[0], marker="o", color=[C[k] for k in oi.columns], logy=True)
    axes[0].set(ylabel="median open interest per market (contracts)", xlabel="time before kickoff", title="Open-interest build-up")
    plt.setp(axes[0].get_xticklabels(), rotation=40, ha="right")
    game_oi.plot.box(ax=axes[1], color="k"); axes[1].set_yscale("log")
    axes[1].set(ylabel="final open interest per game (contracts)", title="Open interest per game by market type")
    fig.tight_layout(); fig.savefig(FIGURES / "candles_open_interest.png"); plt.close(fig)

    # --- 4. Hourly mid volatility pre-game vs in-play -----------------------------------------------------
    vol = cd.dropna(subset=["hourly_return"]).groupby(["kind", cd.mins_to_kick > 0]).hourly_return.agg(sd=lambda s: 100 * s.std(), mad=lambda s: 100 * s.abs().mean(), n="size").round(3)
    vol.index = vol.index.set_names(["kind", "pre_game"])
    vol.to_csv(DATA_PROCESSED / "candles_eda_hourly_vol.csv")
    summary["hourly_mid_sd_cents"] = {f"{k}_{'pre' if p else 'inplay'}": float(v) for (k, p), v in vol.sd.items()}

    # --- 5. Spread-adjusted calibration: does buying at the ask still break even? --------------------------
    last_pre = pre.sort_values("end_time").groupby("ticker").tail(1).set_index("ticker")
    last_pre["won"] = last_pre.result.map({"yes": 1.0, "no": 0.0})
    last_pre = last_pre.dropna(subset=["won"])
    summary["last_pregame_quote_cost"] = {
        k: {"n": int(len(d)), "mean_spread_c": round(float(d.spread_c.mean()), 2),
            "brier_mid": round(float(((d.mid - d.won) ** 2).mean()), 4),
            "ret_buy_yes_at_ask": round(float(((d.won - d.ask_close) / d.ask_close).mean()), 4),
            "ret_buy_no_at_ask": round(float(((1 - d.won - (1 - d.bid_close)) / (1 - d.bid_close)).mean()), 4)}
        for k, d in last_pre.groupby("kind")}

    (DATA_PROCESSED / "candles_eda_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(sp["mean"].unstack().reindex(LABELS[::-1]).round(2)); print(tick.round(3))
    print(by_dist)
    print(vol)


if __name__ == "__main__":
    main()
