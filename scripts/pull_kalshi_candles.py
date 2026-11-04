"""Pull hourly candlesticks (trade OHLC, yes bid/ask OHLC, volume, open interest) for every Kalshi
NFL game market in data/raw/kalshi_markets.parquet. Requires API credentials in .env.

Per-market results are cached in data/raw/kalshi_candles/<ticker>.json; the combined table is
written to data/raw/kalshi_candles.parquet.
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
from pmrisk.kalshi import KalshiClient

CANDLE_DIR = DATA_RAW / "kalshi_candles"


def fetch(client: KalshiClient, row) -> int:
    out = CANDLE_DIR / f"{row.ticker}.json"
    start = pd.Timestamp(row.open_time).to_pydatetime() - timedelta(hours=1)
    end = pd.Timestamp(row.close_time).to_pydatetime() + timedelta(hours=1)
    # Re-fetch any market whose cache was written before it closed. Checking the cache's own age (not
    # the market's current status) catches caches written while active that have since finalized.
    if out.exists() and datetime.fromtimestamp(out.stat().st_mtime, timezone.utc) >= end:
        return -1
    end = min(end, datetime.now(timezone.utc))
    candles = client.candlesticks(row.series, row.ticker, start, end, minutes=60)
    out.write_text(json.dumps(candles))
    return len(candles)


def flatten(ticker: str, candles: list[dict]) -> pd.DataFrame:
    rows = []
    for c in candles:
        p, b, a = c.get("price") or {}, c.get("yes_bid") or {}, c.get("yes_ask") or {}
        rows.append({
            "ticker": ticker,
            "end_ts": c["end_period_ts"],
            "open": p.get("open_dollars"), "high": p.get("high_dollars"), "low": p.get("low_dollars"),
            "close": p.get("close_dollars"), "mean": p.get("mean_dollars"),
            "bid_open": b.get("open_dollars"), "bid_close": b.get("close_dollars"),
            "bid_high": b.get("high_dollars"), "bid_low": b.get("low_dollars"),
            "ask_open": a.get("open_dollars"), "ask_close": a.get("close_dollars"),
            "ask_high": a.get("high_dollars"), "ask_low": a.get("low_dollars"),
            "volume": c.get("volume_fp"), "open_interest": c.get("open_interest_fp"),
        })
    return pd.DataFrame(rows)


def main(workers: int = 4):
    client = KalshiClient()
    if client._private_key is None:
        sys.exit("Candlesticks need API credentials; set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH in .env")
    CANDLE_DIR.mkdir(parents=True, exist_ok=True)
    markets = pd.read_parquet(DATA_RAW / "kalshi_markets.parquet")

    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch, client, r): r.ticker for r in markets.itertuples()}
        for _ in tqdm(as_completed(futs), total=len(futs), desc="candles"):
            pass

    frames = []
    for t in markets.ticker:
        f = CANDLE_DIR / f"{t}.json"
        if f.exists():
            candles = json.loads(f.read_text())
            if candles:
                frames.append(flatten(t, candles))
    df = pd.concat(frames, ignore_index=True)
    df["end_time"] = pd.to_datetime(df.end_ts, unit="s", utc=True)
    for c in df.columns.difference(["ticker", "end_ts", "end_time"]):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_parquet(DATA_RAW / "kalshi_candles.parquet", index=False)
    print(f"{len(df):,} hourly candles across {df.ticker.nunique()} markets, "
          f"{df.end_time.min():%Y-%m-%d} to {df.end_time.max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
