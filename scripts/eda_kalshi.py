"""Exploratory analysis of Kalshi NFL game markets (winner, spread, total) linked to nflverse results.

Writes figures to reports/figures and tables to data/processed/kalshi_eda_*.csv.
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

from pmrisk import DATA_PROCESSED, DATA_RAW, FIGURES
from pmrisk.link import kickoff_utc, link_to_schedule, parse_events, pregame_prices
from pmrisk.nfl import KALSHI_TO_NFLVERSE, completed_games, load_schedules

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
C = {"winner": "#4C72B0", "spread": "#DD8452", "total": "#55A868"}


def main():
    summary = {}
    markets = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")
    trades = pd.read_parquet(DATA_RAW / "kalshi_trades.parquet")
    kalshi_events = pd.read_parquet(DATA_RAW / "kalshi_events.parquet")
    sched = load_schedules()
    games = completed_games(sched)

    # --- 1. Inventory ------------------------------------------------------------------
    ev = link_to_schedule(parse_events(markets), sched)
    ev = ev.merge(sched[["game_id", "season", "week", "game_type", "home_team", "away_team", "gameday", "gametime",
                         "spread_line", "total_line", "home_moneyline", "away_moneyline"]], on="game_id", how="left")
    markets = markets.merge(ev[["event_ticker", "game_id", "game_key", "home_team", "away_team", "game_type", "week"]], on="event_ticker", how="left")
    summary["n_markets"] = int(len(markets))
    summary["n_events_with_markets"] = int(markets.event_ticker.nunique())
    summary["n_games_with_markets"] = int(markets.game_key.nunique())
    summary["n_events_total_in_api"] = int(len(kalshi_events))
    summary["n_events_archived_no_markets"] = int(len(set(kalshi_events.event_ticker) - set(markets.event_ticker)))
    summary["link_rate"] = round(float(ev.game_id.notna().mean()), 3)
    summary["unlinked_events"] = ev[ev.game_id.isna()].event_ticker.tolist()[:10]
    summary["markets_by_kind"] = markets.kind.value_counts().to_dict()
    strikes = markets[markets.kind != "winner"].groupby(["kind", "event_ticker"]).size()
    summary["strikes_per_event"] = strikes.groupby("kind").agg(["mean", "min", "max"]).round(1).to_dict("index")
    summary["game_types"] = markets.drop_duplicates("game_key").game_type.value_counts(dropna=False).to_dict()

    # --- 2. Trade activity ----------------------------------------------------------------
    trades = trades.merge(markets[["ticker", "kind", "event_ticker", "game_id", "floor_strike", "result"]], on="ticker", how="left")
    trades["notional"] = trades.contracts  # $1 per contract at settlement
    summary["n_trades"] = int(len(trades))
    summary["contracts_by_kind"] = trades.groupby("kind").contracts.sum().round(0).to_dict()
    summary["trades_by_kind"] = trades.kind.value_counts().to_dict()
    summary["date_range"] = [str(trades.created_time.min().date()), str(trades.created_time.max().date())]

    kick = ev.dropna(subset=["game_id"]).set_index("event_ticker")
    kick["kickoff"] = kickoff_utc(kick)
    trades = trades.merge(kick[["kickoff"]], left_on="event_ticker", right_index=True, how="left")
    trades["mins_to_kick"] = (trades.kickoff - trades.created_time).dt.total_seconds() / 60
    trades["phase"] = np.where(trades.mins_to_kick > 0, "pre-game", "in-play")
    phase = trades.dropna(subset=["kickoff"]).groupby(["kind", "phase"]).contracts.sum().unstack()
    phase["in_play_share"] = (phase["in-play"] / phase.sum(axis=1)).round(3)
    phase.to_csv(DATA_PROCESSED / "kalshi_eda_phase_volume.csv")
    summary["in_play_share"] = phase.in_play_share.to_dict()

    # Volume by time to kickoff (log-ish buckets).
    edges = [-np.inf, -180, -60, 0, 15, 60, 180, 24 * 60, 3 * 24 * 60, 7 * 24 * 60, np.inf]
    labels = ["in-play >3h", "in-play 1-3h", "in-play <1h", "0-15m", "15-60m", "1-3h", "3-24h", "1-3d", "3-7d", ">7d"]
    trades["bucket"] = pd.cut(trades.mins_to_kick, edges, labels=labels)
    vol_b = trades.groupby(["bucket", "kind"], observed=True).contracts.sum().unstack().reindex(labels[::-1])
    vol_b.to_csv(DATA_PROCESSED / "kalshi_eda_volume_by_time.csv")
    fig, ax = plt.subplots(figsize=(9, 4))
    vol_b.plot.bar(ax=ax, color=[C[k] for k in vol_b.columns], width=0.8)
    ax.set(ylabel="contracts traded", xlabel="time before kickoff", title="Kalshi NFL volume by time to kickoff")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_volume_by_time.png"); plt.close(fig)

    # Per-game volume distribution and by week.
    per_game = trades.dropna(subset=["game_id"]).groupby(["game_id", "kind"]).contracts.sum().unstack().reindex(columns=["winner", "spread", "total"]).fillna(0)
    per_game = per_game.join(sched.set_index("game_id")[["week", "game_type", "gameday"]])
    per_game.to_csv(DATA_PROCESSED / "kalshi_eda_volume_per_game.csv")
    summary["median_contracts_per_game"] = per_game[["winner", "spread", "total"]].median().round(0).to_dict()
    wk = per_game[per_game.game_type == "REG"].groupby("week")[["winner", "spread", "total"]].sum()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    wk.plot.bar(ax=ax, color=[C[k] for k in wk.columns], width=0.8)
    ax.set(ylabel="contracts", xlabel="2026 regular-season week", title="Volume by week")
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_volume_by_week.png"); plt.close(fig)

    # --- 3. Pre-kickoff prices and calibration ------------------------------------------------
    mk = markets.dropna(subset=["game_id"]).set_index("ticker")
    kick_by_ticker = mk.event_ticker.map(kick.kickoff)
    pre = pregame_prices(trades, markets, kick_by_ticker)
    pre = pre.join(mk[["game_id", "home_team", "away_team"]], how="left")
    pre["won"] = pre.result.map({"yes": 1.0, "no": 0.0})
    pre = pre.dropna(subset=["won", "last_pre_price"])
    pre["price"] = pre.vwap_1h.fillna(pre.last_pre_price)
    pre.to_csv(DATA_PROCESSED / "kalshi_eda_pregame_prices.csv")

    def scores(df):
        p = df.price.clip(0.01, 0.99)
        return {"n": int(len(df)), "brier": round(float(((p - df.won) ** 2).mean()), 4),
                "logloss": round(float(-(df.won * np.log(p) + (1 - df.won) * np.log(1 - p)).mean()), 4)}

    summary["kalshi_pregame_scores"] = {k: scores(d) for k, d in pre.groupby("kind")}

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    bins = np.arange(0, 1.01, 0.1)
    cal_rows = []
    for ax, kind in zip(axes, ["winner", "spread", "total"]):
        d = pre[pre.kind == kind].copy()
        d["bin"] = pd.cut(d.price, bins, include_lowest=True)
        cal = d.groupby("bin", observed=True).agg(p=("price", "mean"), y=("won", "mean"), n=("won", "size"))
        cal["se"] = np.sqrt(cal.p * (1 - cal.p) / cal.n)
        cal["kind"] = kind
        cal_rows.append(cal)
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.errorbar(cal.p, cal.y, yerr=1.96 * cal.se, fmt="o", color=C[kind], ms=5, capsize=2)
        for _, r in cal.iterrows():
            ax.annotate(int(r.n), (r.p, r.y), textcoords="offset points", xytext=(5, -10), fontsize=7)
        s = summary["kalshi_pregame_scores"][kind]
        ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="pre-kickoff price (1h VWAP)", ylabel="settled YES rate",
               title=f"{kind}  n={s['n']}  Brier={s['brier']}")
    fig.suptitle("Kalshi pre-kickoff calibration, 2026 season", y=1.02)
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_calibration.png", bbox_inches="tight"); plt.close(fig)
    pd.concat(cal_rows).to_csv(DATA_PROCESSED / "kalshi_eda_calibration.csv")

    # Favourite-longshot: average return to buying YES at price p.
    pre["ret"] = (pre.won - pre.price) / pre.price
    fl = pre.groupby(pd.cut(pre.price, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]), observed=True).agg(n=("ret", "size"), mean_ret=("ret", "mean"), p=("price", "mean"), y=("won", "mean")).round(3)
    fl.to_csv(DATA_PROCESSED / "kalshi_eda_favlong.csv")
    summary["yes_return_by_price_bucket"] = {str(k): v for k, v in fl.mean_ret.to_dict().items()}

    # --- 4. Kalshi winner price vs sportsbook closing moneyline -------------------------------------
    w = pre[pre.kind == "winner"].copy()
    w["is_home"] = w.yes_sub_title.str.upper().str[:3]  # city name; match via team below
    g = games.set_index("game_id")
    w = w.join(g[["home_moneyline", "away_moneyline", "spread_line", "margin"]], on="game_id")
    # Kalshi winner tickers end in the team code; home if it equals the schedule's home team.
    w["team"] = w.index.str.rsplit("-", n=1).str[-1].map(lambda t: KALSHI_TO_NFLVERSE.get(t, t))
    w["is_home"] = w.team == w.home_team
    def implied(m):
        m = np.asarray(m, dtype=float)
        return np.where(m < 0, -m / (-m + 100), 100 / (m + 100))
    ph, pa = implied(w.home_moneyline), implied(w.away_moneyline)
    w["book_fair"] = np.where(w.is_home, ph / (ph + pa), pa / (ph + pa))
    w["stern_p"] = np.where(w.is_home, stats.norm.cdf(w.spread_line / 13.86), stats.norm.cdf(-w.spread_line / 13.86))
    w = w.dropna(subset=["book_fair"])
    summary["winner_vs_book"] = {
        "n": int(len(w)),
        "corr": round(float(np.corrcoef(w.price, w.book_fair)[0, 1]), 4),
        "mean_diff_kalshi_minus_book": round(float((w.price - w.book_fair).mean()), 4),
        "mad": round(float((w.price - w.book_fair).abs().mean()), 4),
        "book_brier": round(float(((w.book_fair - w.won) ** 2).mean()), 4),
        "kalshi_brier": round(float(((w.price - w.won) ** 2).mean()), 4),
        "stern_brier": round(float(((w.stern_p - w.won) ** 2).mean()), 4),
    }
    # Overround: sum of both teams' YES prices per event.
    over = w.groupby("event_ticker").price.sum()
    summary["winner_overround_mean"] = round(float((over - 1).mean()), 4)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.3))
    axes[0].plot([0, 1], [0, 1], "k--", lw=0.8)
    axes[0].scatter(w.book_fair, w.price, s=12, alpha=0.6, color=C["winner"])
    axes[0].set(xlabel="de-vigged sportsbook closing P(win)", ylabel="Kalshi pre-kickoff price", title=f"Winner: Kalshi vs book  (corr={summary['winner_vs_book']['corr']:.3f})")
    axes[1].hist(w.price - w.book_fair, bins=np.arange(-0.15, 0.151, 0.01), color=C["winner"], alpha=0.8)
    axes[1].axvline(0, color="k", lw=0.8)
    axes[1].set(xlabel="Kalshi − book", title="Price difference")
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_vs_book.png"); plt.close(fig)
    w[["event_ticker", "team", "is_home", "price", "book_fair", "stern_p", "won", "pre_volume"]].to_csv(DATA_PROCESSED / "kalshi_eda_winner_vs_book.csv")

    # --- 5. Spread and total ladders: market-implied distribution ---------------------------------------
    lad = pre[pre.kind.isin(["spread", "total"])].dropna(subset=["floor_strike"]).copy()
    lad = lad.join(g[["spread_line", "total_line", "margin", "total_pts"]], on="game_id")
    # For spreads, the ticker names the team that must win by more than the strike.
    lad["team"] = [KALSHI_TO_NFLVERSE.get(m, m) for m in pd.Series(lad.index).str.rsplit("-", n=1).str[-1].str.replace(r"\d+$", "", regex=True)]
    lad["is_home"] = lad.team == lad.home_team
    # Convert every strike to the home-margin axis: P(home margin > k) or P(total > k).
    def implied_cdf_point(r):
        if r.kind == "total":
            return r.floor_strike, 1 - r.price, r.total_pts  # P(total <= k) = 1 - price
        if r.is_home:
            return r.floor_strike, 1 - r.price, r.margin  # P(margin <= k)
        return -r.floor_strike, r.price, r.margin        # away wins by > k  <=> margin < -k
    pts = lad.apply(implied_cdf_point, axis=1, result_type="expand")
    pts.columns = ["x", "cdf", "realised"]
    lad = lad.join(pts)
    lad.to_csv(DATA_PROCESSED / "kalshi_eda_ladders.csv")

    # Monotonicity violations within a ladder (a cheap arbitrage check on pre-kick VWAPs).
    def viol(d):
        d = d.sort_values("x")
        return int((d.cdf.diff() < -0.02).sum())
    mono = lad.groupby(["kind", "event_ticker"]).apply(viol, include_groups=False)
    summary["ladder_monotonicity_violations_gt2c"] = {k: int(v.sum()) for k, v in mono.groupby(level=0)}
    summary["ladder_points"] = lad.kind.value_counts().to_dict()

    # Compare the market-implied CDF at each strike with the Stern normal from the closing spread/total.
    lad["model_cdf"] = np.where(lad.kind == "total", stats.norm.cdf((lad.x + 0.0 - lad.total_line) / 13.24),
                                stats.norm.cdf((lad.x - lad.spread_line) / 12.73))
    lad["cdf_diff"] = lad.cdf - lad.model_cdf
    summary["ladder_vs_normal_mad"] = lad.cdf_diff.abs().groupby(lad.kind).mean().round(4).to_dict()

    # Example ladders: the two highest-volume spread and total events.
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for ax, kind in zip(axes, ["spread", "total"]):
        d = lad[lad.kind == kind]
        top_ev = d.groupby("event_ticker").vol_1h.sum().nlargest(3).index
        for e in top_ev:
            dd = d[d.event_ticker == e].sort_values("x")
            line = dd.spread_line.iloc[0] if kind == "spread" else dd.total_line.iloc[0]
            sd = 12.73 if kind == "spread" else 13.24
            xs = np.linspace(dd.x.min() - 3, dd.x.max() + 3, 200)
            l, = ax.plot(dd.x, dd.cdf, "o-", ms=4, label=f"{e.split('-')[1][7:]} (line {line:+.1f})")
            ax.plot(xs, stats.norm.cdf((xs - line) / sd), "--", lw=0.9, color=l.get_color())
            ax.axvline(dd.realised.iloc[0], color=l.get_color(), lw=0.6, alpha=0.5)
        ax.set(xlabel="home margin k" if kind == "spread" else "total points k", ylabel="market-implied P(X ≤ k)",
               title=f"{kind} ladder: Kalshi (solid) vs normal from closing line (dashed)")
        ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_ladders.png"); plt.close(fig)

    # Implied density from the spread ladder pooled across games, on the (k - spread) axis, vs empirical.
    sp = lad[lad.kind == "spread"].copy()
    sp["rel"] = sp.x - sp.spread_line
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(sp.rel, sp.cdf, s=6, alpha=0.4, color=C["spread"], label="Kalshi strikes (all games)")
    xs = np.linspace(-30, 30, 300)
    ax.plot(xs, stats.norm.cdf(xs / 12.73), "k--", label="N(0, 12.73²)")
    emp = games.dropna(subset=["spread_line"]).ats_error
    ax.plot(np.sort(emp), np.arange(1, len(emp) + 1) / len(emp), color="#4C72B0", lw=1.2, label="empirical CDF of margin − spread, 2015–26")
    ax.set(xlim=(-30, 30), xlabel="strike − closing spread (home-margin axis)", ylabel="P(margin ≤ strike)", title="Spread ladders pooled relative to the closing spread")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_spread_ladder_pooled.png"); plt.close(fig)

    # --- 6. In-play price paths for one game ----------------------------------------------------------------
    top_game = trades[trades.kind == "winner"].groupby("event_ticker").contracts.sum().idxmax()
    tg = trades[(trades.event_ticker == top_game)].sort_values("created_time")
    fig, ax = plt.subplots(figsize=(10, 4))
    for t, d in tg.groupby("ticker"):
        d = d[d.mins_to_kick < 240]
        ax.plot(-d.mins_to_kick, d.yes_price, lw=0.8, label=t.rsplit("-", 1)[-1])
    ax.axvline(0, color="k", lw=0.8); ax.set(xlabel="minutes after kickoff", ylabel="YES trade price", title=f"Winner market trade prices: {top_game}")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "kalshi_inplay_example.png"); plt.close(fig)
    summary["inplay_example_event"] = top_game

    (DATA_PROCESSED / "kalshi_eda_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(phase); print(fl)


if __name__ == "__main__":
    main()
