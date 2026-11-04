"""Pull Kalshi parlay (multivariate-event) markets whose legs are all NFL winner/spread/total markets, with trades.

Kalshi builds parlays on request as MVE markets; each market lists its legs in `mve_selected_legs`
(event_ticker, market_ticker, side). We page the series that carry them, keep the markets whose every leg is in
one of our three game series, and fetch their trade tapes (cached per market like scripts/pull_kalshi.py).

Writes data/raw/kalshi_parlays.parquet (one row per market), kalshi_parlay_legs.parquet (one row per leg) and
kalshi_parlay_fills.parquet (candle fills for a sample). Flags: --cached-only (build from cached windows, no
paging), --candles N (size of the candle sample, default 2000).
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_RAW
from pmrisk.kalshi import GAME_SERIES, KalshiClient

TRADES_DIR = DATA_RAW / "kalshi_parlay_trades"
MVE_SERIES = [
    "KXMVESPORTSMULTIGAMEEXTENDED", "KXMVECROSSCATEGORY", "KXMVECROSSCATEGORY-SHARD1", "KXMVECROSSCATEGORY-SHARD-1",
    "KXMVECROSSCATEGORY0", "KXMVECROSSCATEGORY0-SHARD1", "KXMVENFLSINGLEGAME", "KXMVENFLMULTIGAME", "KXMVENFLMULTIGAMEEXTENDED",
    "KXNFLPREPACKSGP",
]
STATUSES = ["settled", "closed", "open"]
LEG_PREFIXES = tuple(f"{s}-" for s in GAME_SERIES.values())
FIELDS = ["ticker", "event_ticker", "series_ticker", "title", "yes_sub_title", "status", "result", "created_time", "open_time",
          "close_time", "expiration_time", "last_price_dollars", "yes_bid_dollars", "yes_ask_dollars",
          "volume_fp", "open_interest_fp", "mve_collection_ticker"]


MARKETS_DIR = DATA_RAW / "kalshi_parlay_markets"
MIN_CLOSE = datetime(2026, 8, 1, tzinfo=timezone.utc)  # NFL legs exist only from the 2026 preseason on


def fetch_series(client: KalshiClient, series: str, status: str) -> tuple[list[dict], int]:
    """NFL-leg markets of one series/status, cached per (series, status); open markets are always re-fetched."""
    out = MARKETS_DIR / f"{series}_{status}.json"
    if out.exists() and status != "open":
        cached = json.loads(out.read_text())
        return cached["markets"], cached["n_all"]
    if "--cached-only" in sys.argv and not out.exists():
        return [], 0
    kept, n_all = [], 0
    for m in client.paginate("/markets", "markets", series_ticker=series, status=status, mve_filter="only",
                             min_close_ts=int(MIN_CLOSE.timestamp())):
        n_all += 1
        ml = m.get("mve_selected_legs") or []
        if ml and all(str(l.get("market_ticker", "")).startswith(LEG_PREFIXES) for l in ml):
            kept.append(m)
        if n_all % 25000 == 0:
            print(f"  {series} {status}: {n_all:,} markets so far, at close {m.get('close_time', '')[:10]}, {len(kept)} NFL", flush=True)
    out.write_text(json.dumps({"markets": kept, "n_all": n_all}))
    return kept, n_all


CROSS_SERIES = [s for s in MVE_SERIES if s.startswith("KXMVECROSSCATEGORY")]
WINDOW_BEFORE, WINDOW_AFTER = timedelta(minutes=10), timedelta(minutes=30)


def settlement_windows() -> list[tuple[datetime, datetime]]:
    """Merged [close-10min, close+30min] windows around every finalized NFL winner market's close.

    The cross-category series closes thousands of (mostly untraded) parlay quotes a minute, so it cannot be
    paged in full. A parlay closes when its last leg settles, within minutes of that game's winner market, so
    paging only these windows finds every parlay whose last leg is an NFL game.
    """
    mk = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")
    closes = pd.to_datetime(mk[(mk.kind == "winner") & (mk.status == "finalized")].close_time, utc=True)
    closes = sorted(c.to_pydatetime() for c in closes.drop_duplicates() if c.to_pydatetime() >= MIN_CLOSE)
    out: list[list[datetime]] = []
    for c in closes:
        lo, hi = c - WINDOW_BEFORE, c + WINDOW_AFTER
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


def fetch_window(client: KalshiClient, series: str, lo: datetime, hi: datetime) -> tuple[list[dict], int]:
    out = MARKETS_DIR / f"{series}_w{int(lo.timestamp())}.json"
    if out.exists():
        cached = json.loads(out.read_text())
        return cached["markets"], cached["n_all"]
    if "--cached-only" in sys.argv:
        return [], 0
    wk, n = [], 0
    for m in client.paginate("/markets", "markets", series_ticker=series, status="settled", mve_filter="only",
                             min_close_ts=int(lo.timestamp()), max_close_ts=int(hi.timestamp())):
        n += 1
        ml = m.get("mve_selected_legs") or []
        if ml and all(str(l.get("market_ticker", "")).startswith(LEG_PREFIXES) for l in ml):
            wk.append(m)
    out.write_text(json.dumps({"markets": wk, "n_all": n}))
    print(f"  {series} {lo:%m-%d %H:%M}-{hi:%H:%M}: {n:,} markets, {len(wk)} NFL", flush=True)
    return wk, n


def fetch_windows(client: KalshiClient, series: str, windows, workers: int = 10) -> tuple[list[dict], int]:
    """Settled NFL-leg markets of a cross-category series inside the settlement windows, cached per window.
    Windows are paged in parallel; the client's shared token bucket keeps the total under the rate limit."""
    kept, n_all = [], 0
    with ThreadPoolExecutor(workers) as ex:
        for wk, n in ex.map(lambda w: fetch_window(client, series, *w), windows):
            kept += wk; n_all += n
    return kept, n_all


def pull_markets(client: KalshiClient) -> tuple[pd.DataFrame, pd.DataFrame]:
    MARKETS_DIR.mkdir(parents=True, exist_ok=True)
    rows, legs = [], []
    windows = settlement_windows()
    print(f"{len(windows)} settlement windows from {windows[0][0]:%Y-%m-%d} to {windows[-1][1]:%Y-%m-%d}", flush=True)
    for series in MVE_SERIES:
        n_all = n_nfl = 0
        for status in STATUSES:
            if series in CROSS_SERIES:
                if status != "settled":
                    continue
                kept, n = fetch_windows(client, series, windows)
            else:
                kept, n = fetch_series(client, series, status)
            n_all += n
            for m in kept:
                ml = m["mve_selected_legs"]
                n_nfl += 1
                row = {k: m.get(k) for k in FIELDS}
                row.update(series=series, pulled_status=status, n_legs=len(ml), legs_json=json.dumps(ml))
                rows.append(row)
                for i, l in enumerate(ml):
                    legs.append({"ticker": m["ticker"], "leg": i, "leg_event": l.get("event_ticker"),
                                 "leg_market": l.get("market_ticker"), "side": l.get("side")})
            print(f"{series:<34} {status:<8} {n:>6} markets", flush=True)
        print(f"{series:<34} {n_all:>6} markets, {n_nfl:>5} with all-NFL game legs", flush=True)
    mk = pd.DataFrame(rows).drop_duplicates("ticker")
    lg = pd.DataFrame(legs).drop_duplicates(["ticker", "leg"])
    lg = lg[lg.ticker.isin(mk.ticker)]
    for c in ("last_price_dollars", "yes_bid_dollars", "yes_ask_dollars", "volume_fp", "open_interest_fp"):
        mk[c] = pd.to_numeric(mk[c], errors="coerce")
    mk.to_parquet(DATA_RAW / "kalshi_parlays.parquet", index=False)
    lg.to_parquet(DATA_RAW / "kalshi_parlay_legs.parquet", index=False)
    return mk, lg


def fetch_trades(client: KalshiClient, ticker: str, refetch: bool) -> int:
    out = TRADES_DIR / f"{ticker}.json"
    if out.exists() and not refetch:
        return -1
    trades = client.trades(ticker)
    out.write_text(json.dumps(trades))
    return len(trades)


def pull_trades(mk: pd.DataFrame, workers: int = 4) -> pd.DataFrame:
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    client = KalshiClient()
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch_trades, client, r.ticker, r.status not in ("settled", "finalized")): r.ticker
                for r in mk.itertuples()}
        for _ in tqdm(as_completed(futs), total=len(futs), desc="parlay trades"):
            pass
    frames = []
    for t in mk.ticker:
        trades = json.loads((TRADES_DIR / f"{t}.json").read_text())
        if trades:
            frames.append(pd.DataFrame(trades))
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["ticker"])
    if len(df):
        df["created_time"] = pd.to_datetime(df.created_time, utc=True)
        for c in ("yes_price_dollars", "no_price_dollars", "count_fp"):
            if c in df:
                df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_parquet(DATA_RAW / "kalshi_parlay_trades.parquet", index=False)
    return df


CANDLE_DIR = DATA_RAW / "kalshi_parlay_candles"


def fetch_candles(client: KalshiClient, row, refetch: bool) -> int:
    out = CANDLE_DIR / f"{row.ticker}.json"
    if out.exists() and not refetch:
        return -1
    start = pd.Timestamp(row.open_time).to_pydatetime() - timedelta(hours=1)
    end = min(pd.Timestamp(row.close_time).to_pydatetime() + timedelta(hours=1), datetime.now(timezone.utc))
    candles = client.candlesticks(row.series, row.ticker, start, end, minutes=60)
    out.write_text(json.dumps(candles))
    return len(candles)


def pull_fills(mk: pd.DataFrame, workers: int = 4) -> pd.DataFrame:
    """Hourly candles of the given parlay markets; an hour with volume carries a fill. One row per market-hour with volume."""
    client = KalshiClient()
    if client._private_key is None:
        sys.exit("Parlay candles need API credentials in .env")
    CANDLE_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch_candles, client, r, r.status not in ("settled", "finalized")): r.ticker for r in mk.itertuples()}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="parlay candles"):
            try:
                fut.result()
            except Exception as e:  # keep going; the market is skipped in the fills table
                print(f"candles failed for {futs[fut]}: {str(e)[:80]}")
    rows = []
    for t in mk.ticker:
        f = CANDLE_DIR / f"{t}.json"
        if not f.exists():  # a fetch that failed inside the thread pool
            continue
        for c in json.loads(f.read_text()):
            vol = float(c.get("volume_fp") or 0)
            if vol <= 0:
                continue
            p = c.get("price") or {}
            rows.append({"ticker": t, "end_ts": c["end_period_ts"], "price": p.get("mean_dollars") or p.get("close_dollars"),
                         "price_open": p.get("open_dollars"), "price_close": p.get("close_dollars"),
                         "volume": vol, "open_interest": c.get("open_interest_fp")})
    df = pd.DataFrame(rows)
    if len(df):
        df["end_time"] = pd.to_datetime(df.end_ts, unit="s", utc=True)
        for c in ("price", "price_open", "price_close", "open_interest"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_parquet(DATA_RAW / "kalshi_parlay_fills.parquet", index=False)
    return df


if __name__ == "__main__":
    mk, lg = pull_markets(KalshiClient())
    print(f"{len(mk)} NFL parlay markets, {len(lg)} legs; by status {mk.status.value_counts().to_dict()}")
    # Fills are not on the public trade tape. Candles show them, but one request per market is slow for tens of
    # thousands of markets; 80% of parlays fill once, within the hour they are created, at the market's last
    # price, so the analysis uses (created_time, last_price) for all markets and candles for a sample to check it.
    sample = mk.sample(min(len(mk), int(sys.argv[sys.argv.index("--candles") + 1]) if "--candles" in sys.argv else 2000), random_state=0)
    fills = pull_fills(sample)
    print(f"{len(fills)} fill-hours on {fills.ticker.nunique() if len(fills) else 0} of {len(sample)} sampled markets")
