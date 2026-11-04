"""Pull Kalshi NFL game-level markets (winner, spread, total) and their full trade history.

Writes data/raw/kalshi_markets.parquet and data/raw/kalshi_trades.parquet.
Trades are fetched per market and cached in data/raw/kalshi_trades/<ticker>.json so the
script can be re-run incrementally.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk import DATA_RAW
from pmrisk.kalshi import GAME_SERIES, KalshiClient

TRADES_DIR = DATA_RAW / "kalshi_trades"
MARKET_FIELDS = [
    "ticker", "event_ticker", "title", "yes_sub_title", "strike_type", "floor_strike", "cap_strike",
    "open_time", "close_time", "expiration_time", "status", "result", "rules_primary", "rules_secondary",
]


def pull_markets(client: KalshiClient) -> pd.DataFrame:
    # No status filter: the public API only exposes markets listed since ~May 2026 anyway,
    # and filtering by status drops some of those. Older (2025-season) events exist in
    # /events but their markets and trades are archived and return empty.
    rows = []
    for kind, series in GAME_SERIES.items():
        ms = client.markets(series)
        for m in ms:
            row = {k: m.get(k) for k in MARKET_FIELDS}
            row.update(series=series, kind=kind)
            rows.append(row)
        print(f"{series:<12} {len(ms):>6} markets")
    df = pd.DataFrame(rows).drop_duplicates("ticker")
    df.to_parquet(DATA_RAW / "kalshi_markets.parquet", index=False)

    ev_rows = []
    for kind, series in GAME_SERIES.items():
        for e in client.events(series):
            ev_rows.append({"event_ticker": e["event_ticker"], "series": series, "kind": kind,
                            "title": e.get("title"), "sub_title": e.get("sub_title")})
    pd.DataFrame(ev_rows).drop_duplicates("event_ticker").to_parquet(DATA_RAW / "kalshi_events.parquet", index=False)
    return df


def fetch_trades(client: KalshiClient, ticker: str) -> int:
    out = TRADES_DIR / f"{ticker}.json"
    if out.exists():
        return -1
    trades = client.trades(ticker)
    out.write_text(json.dumps(trades))
    return len(trades)


def pull_trades(markets: pd.DataFrame, workers: int = 4) -> pd.DataFrame:
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    tickers = markets.ticker.tolist()
    client = KalshiClient()
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch_trades, client, t): t for t in tickers}
        for _ in tqdm(as_completed(futs), total=len(futs), desc="trades"):
            pass

    frames = []
    for t in tickers:
        trades = json.loads((TRADES_DIR / f"{t}.json").read_text())
        if trades:
            frames.append(pd.DataFrame(trades))
    df = pd.concat(frames, ignore_index=True)
    df["created_time"] = pd.to_datetime(df["created_time"], utc=True, format="ISO8601")
    for c in ("yes_price_dollars", "no_price_dollars", "count_fp"):
        df[c] = df[c].astype(float)
    df = df.rename(columns={"yes_price_dollars": "yes_price", "no_price_dollars": "no_price", "count_fp": "contracts"})
    df.to_parquet(DATA_RAW / "kalshi_trades.parquet", index=False)
    return df


if __name__ == "__main__":
    client = KalshiClient()
    print("auth:", "signed" if client._private_key is not None else "public only")
    markets = pull_markets(client)
    print(f"{len(markets)} unique markets across {markets.event_ticker.nunique()} events")
    trades = pull_trades(markets)
    print(f"{len(trades)} trades, {trades.contracts.sum():,.0f} contracts, "
          f"{trades.created_time.min():%Y-%m-%d} to {trades.created_time.max():%Y-%m-%d}")
