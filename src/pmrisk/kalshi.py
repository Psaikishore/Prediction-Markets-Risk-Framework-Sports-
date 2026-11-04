"""Thin client for the Kalshi trade API v2.

Public endpoints (markets, events, trades) need no auth. If KALSHI_API_KEY_ID and
KALSHI_PRIVATE_KEY_PATH are set in the environment (or a .env at the repo root),
requests are RSA-PSS signed so authenticated endpoints (candlesticks, orderbook)
also work.
"""

from __future__ import annotations

import base64
import os
import threading
import time
from datetime import datetime, timezone
from typing import Iterator

import requests
from dotenv import load_dotenv

from . import ROOT

BASE = "https://api.elections.kalshi.com/trade-api/v2"
GAME_SERIES = {"winner": "KXNFLGAME", "spread": "KXNFLSPREAD", "total": "KXNFLTOTAL"}

load_dotenv(ROOT / ".env")


class _RateLimiter:
    """Shared token bucket; the public API allows roughly 10 requests/second."""

    def __init__(self, rate: float):
        self.interval = 1.0 / rate
        self.lock = threading.Lock()
        self.next_slot = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            self.next_slot = max(self.next_slot, now) + self.interval
            delay = self.next_slot - now - self.interval
        if delay > 0:
            time.sleep(delay)


_LIMITER = _RateLimiter(rate=8.0)


class KalshiClient:
    def __init__(self, sleep: float = 0.0, max_retries: int = 8):
        self.session = requests.Session()
        self.sleep = sleep
        self.max_retries = max_retries
        self.key_id = os.getenv("KALSHI_API_KEY_ID")
        self._private_key = None
        key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
        if self.key_id and key_path and os.path.exists(key_path):
            from cryptography.hazmat.primitives import serialization

            with open(key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(f.read(), password=None)

    # -- auth -----------------------------------------------------------------
    def _headers(self, method: str, path: str) -> dict:
        if self._private_key is None:
            return {}
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        ts = str(int(time.time() * 1000))
        # Signature covers the path without the query string.
        msg = (ts + method.upper() + "/trade-api/v2" + path.split("?")[0]).encode()
        sig = self._private_key.sign(
            msg,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
            "KALSHI-ACCESS-TIMESTAMP": ts,
        }

    # -- transport ------------------------------------------------------------
    def get(self, path: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        for attempt in range(self.max_retries):
            _LIMITER.wait()
            try:
                r = self.session.get(BASE + path, params=params, headers=self._headers("GET", path), timeout=30)
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(min(2**attempt, 30))
                continue
            if r.status_code == 429:
                time.sleep(0.3 * (attempt + 1))
                continue
            if r.status_code >= 500:
                time.sleep(min(2**attempt, 30))
                continue
            r.raise_for_status()
            time.sleep(self.sleep)
            return r.json()
        r.raise_for_status()
        return {}

    def paginate(self, path: str, key: str, limit: int = 1000, **params) -> Iterator[dict]:
        cursor = None
        while True:
            page = self.get(path, limit=limit, cursor=cursor, **params)
            yield from page.get(key, [])
            cursor = page.get("cursor")
            if not cursor:
                break

    # -- endpoints ------------------------------------------------------------
    def markets(self, series_ticker: str, status: str | None = None) -> list[dict]:
        return list(self.paginate("/markets", "markets", series_ticker=series_ticker, status=status))

    def market(self, ticker: str) -> dict:
        return self.get(f"/markets/{ticker}")["market"]

    def mve_markets(self, series_ticker: str, status: str | None = None) -> list[dict]:
        """Multivariate-event (parlay) markets of a series; legs are in each market's `mve_selected_legs`."""
        return list(self.paginate("/markets", "markets", series_ticker=series_ticker, status=status, mve_filter="only"))

    def events(self, series_ticker: str, status: str | None = None) -> list[dict]:
        return list(self.paginate("/events", "events", limit=200, series_ticker=series_ticker, status=status))

    def trades(self, ticker: str) -> list[dict]:
        return list(self.paginate("/markets/trades", "trades", ticker=ticker))

    def candlesticks(
        self, series_ticker: str, ticker: str, start: datetime, end: datetime, minutes: int = 60, max_periods: int = 4000
    ) -> list[dict]:
        # The endpoint rejects (HTTP 400) any range spanning more than 5000 periods, so page through
        # [start, end] in chunks and stitch the results, de-duplicating candles on chunk boundaries.
        path = f"/series/{series_ticker}/markets/{ticker}/candlesticks"
        lo, hi, step = int(start.timestamp()), int(end.timestamp()), max_periods * minutes * 60
        by_ts: dict[int, dict] = {}
        while lo < hi:
            chunk_end = min(lo + step, hi)
            page = self.get(path, start_ts=lo, end_ts=chunk_end, period_interval=minutes)
            for c in page.get("candlesticks", []):
                by_ts[c["end_period_ts"]] = c
            lo = chunk_end
        return [by_ts[ts] for ts in sorted(by_ts)]


def parse_event_ticker(event_ticker: str) -> dict:
    """KXNFLGAME-26SEP28PHICHI -> date 2026-09-28, away PHI, home CHI.

    Kalshi writes the matchup as AWAYHOME after the date; team codes are 2-3 letters,
    so the split is ambiguous for 5-letter codes and resolved against the schedule later.
    """
    _, tail = event_ticker.split("-", 1)
    date_str, teams = tail[:7], tail[7:]
    date = datetime.strptime(date_str, "%y%b%d").replace(tzinfo=timezone.utc).date()
    return {"event_date": date, "teams_raw": teams}
