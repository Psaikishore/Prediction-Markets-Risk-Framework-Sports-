"""Link Kalshi NFL events to nflverse games and derive pre-kickoff prices from trades."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .nfl import KALSHI_TO_NFLVERSE

TEAM_CODES = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU", "IND",
    "JAX", "JAC", "KC", "LAC", "LAR", "LA", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT",
    "SEA", "SF", "TB", "TEN", "WAS", "WSH",
}


def split_teams(raw: str) -> tuple[str, str] | None:
    """'PHICHI' -> ('PHI', 'CHI'); tries every split whose halves are both team codes."""
    for i in range(2, len(raw) - 1):
        a, b = raw[:i], raw[i:]
        if a in TEAM_CODES and b in TEAM_CODES:
            return KALSHI_TO_NFLVERSE.get(a, a), KALSHI_TO_NFLVERSE.get(b, b)
    return None


def parse_events(markets: pd.DataFrame) -> pd.DataFrame:
    ev = markets[["event_ticker", "series", "kind"]].drop_duplicates("event_ticker").copy()
    tail = ev.event_ticker.str.split("-", n=1).str[1]
    ev["event_date"] = pd.to_datetime(tail.str[:7], format="%y%b%d")
    teams = tail.str[7:].map(split_teams)
    ev["team_a"] = teams.map(lambda t: t[0] if t else None)
    ev["team_b"] = teams.map(lambda t: t[1] if t else None)
    # The date and matchup identify the game regardless of series.
    ev["game_key"] = ev.event_date.dt.strftime("%Y%m%d") + "-" + tail.str[7:]
    return ev


def link_to_schedule(events: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """Match on date (allowing +-1 day for late kickoffs) and the unordered team pair."""
    sch = schedule.copy()
    sch["pair"] = [frozenset(t) for t in zip(sch.home_team, sch.away_team)]
    out = []
    for _, e in events.iterrows():
        if e.team_a is None:
            out.append(None)
            continue
        pair = frozenset((e.team_a, e.team_b))
        cand = sch[(sch.pair == pair) & ((sch.gameday - e.event_date).abs() <= pd.Timedelta(days=1))]
        out.append(cand.game_id.iloc[0] if len(cand) else None)
    events = events.copy()
    events["game_id"] = out
    return events


def kickoff_utc(schedule: pd.DataFrame) -> pd.Series:
    """Kickoff as UTC from nflverse gameday + gametime (US/Eastern)."""
    local = pd.to_datetime(schedule.gameday.dt.strftime("%Y-%m-%d") + " " + schedule.gametime.fillna("13:00"))
    return local.dt.tz_localize("US/Eastern", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")


def pregame_prices(trades: pd.DataFrame, markets: pd.DataFrame, kickoff: pd.Series, window_minutes: int = 60) -> pd.DataFrame:
    """Volume-weighted yes price in the last `window_minutes` before kickoff, plus the last pre-kickoff trade.

    `kickoff` is indexed by market ticker.
    """
    t = trades.drop(columns=["kickoff"], errors="ignore").merge(
        kickoff.rename("kickoff"), left_on="ticker", right_index=True, how="inner")
    pre = t[t.created_time < t.kickoff]
    last = pre.sort_values("created_time").groupby("ticker").tail(1).set_index("ticker")
    win = pre[pre.created_time >= pre.kickoff - pd.Timedelta(minutes=window_minutes)]
    vwap = win.groupby("ticker").apply(lambda g: np.average(g.yes_price, weights=g.contracts), include_groups=False)
    vol = win.groupby("ticker").contracts.sum()
    out = pd.DataFrame({"last_pre_price": last.yes_price, "last_pre_time": last.created_time,
                        "vwap_1h": vwap, "vol_1h": vol})
    out["pre_volume"] = pre.groupby("ticker").contracts.sum()
    out["pre_trades"] = pre.groupby("ticker").size()
    return out.join(markets.set_index("ticker")[["event_ticker", "kind", "floor_strike", "yes_sub_title", "result"]], how="left")
