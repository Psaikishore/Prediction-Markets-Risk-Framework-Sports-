"""Empirical joint score distribution p(home, away), tilted to a target spread and total.

The prior is the historical frequency table of final scores. For a specific game it is reweighted
by exponential tilting, p(h, a) ∝ p0(h, a) · exp(λ₁·(h−a) + λ₂·(h+a)), with (λ₁, λ₂) chosen so the
tilted distribution has the game's expected margin and expected total. This is the minimum
relative-entropy (Kullback–Leibler) adjustment of the prior that satisfies the two moment
constraints, so key numbers, parity and the margin–total dependence of the prior are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats

MAX_PTS = 80


@dataclass
class ScoreGrid:
    p: np.ndarray  # p[h, a], shape (MAX_PTS+1, MAX_PTS+1), sums to 1

    @property
    def h(self) -> np.ndarray:
        return np.arange(self.p.shape[0])[:, None]

    @property
    def a(self) -> np.ndarray:
        return np.arange(self.p.shape[1])[None, :]

    @property
    def margin(self) -> np.ndarray:
        return self.h - self.a

    @property
    def total(self) -> np.ndarray:
        return self.h + self.a

    # -- moments -------------------------------------------------------------
    def mean_margin(self) -> float:
        return float((self.p * self.margin).sum())

    def mean_total(self) -> float:
        return float((self.p * self.total).sum())

    def margin_pmf(self) -> pd.Series:
        m = self.margin.ravel()
        return pd.Series(self.p.ravel()).groupby(m).sum()

    def total_pmf(self) -> pd.Series:
        t = self.total.ravel()
        return pd.Series(self.p.ravel()).groupby(t).sum()

    # -- contract prices --------------------------------------------------------
    def p_home_win(self, tie_value: float = 0.5) -> float:
        return float(self.p[self.margin > 0].sum() + tie_value * self.p[self.margin == 0].sum())

    def p_margin_over(self, k: float) -> float:
        """P(home − away > k). For an away-team spread strike k, use p_margin_under(−k)."""
        return float(self.p[self.margin > k].sum())

    def p_margin_under(self, k: float) -> float:
        return float(self.p[self.margin < k].sum())

    def p_total_over(self, k: float) -> float:
        return float(self.p[self.total > k].sum())

    def cdf_margin(self, k: float) -> float:
        return float(self.p[self.margin <= k].sum())

    # -- conditioning ------------------------------------------------------------------
    def condition(self, mask: np.ndarray) -> "ScoreGrid":
        q = np.where(mask, self.p, 0.0)
        return ScoreGrid(q / q.sum())


def empirical_grid(games: pd.DataFrame, weights: np.ndarray | None = None, smooth: float = 0.0) -> ScoreGrid:
    """Frequency table of (home_score, away_score) over completed games.

    `smooth` adds a small pseudo-count spread proportionally to the product of the two marginal
    score distributions, so cells never seen historically (but reachable) are not exactly zero.
    """
    h = games.home_score.astype(int).clip(0, MAX_PTS).to_numpy()
    a = games.away_score.astype(int).clip(0, MAX_PTS).to_numpy()
    w = np.ones(len(games)) if weights is None else np.asarray(weights, dtype=float)
    p = np.zeros((MAX_PTS + 1, MAX_PTS + 1))
    np.add.at(p, (h, a), w)
    if smooth > 0:
        mh, ma = p.sum(1), p.sum(0)
        p = p + smooth * np.outer(mh, ma) / p.sum()
    return ScoreGrid(p / p.sum())


def tilt(prior: ScoreGrid, target_margin: float, target_total: float) -> tuple[ScoreGrid, np.ndarray]:
    """Exponentially tilt the prior to hit E[margin] = target_margin and E[total] = target_total."""
    m, t, logp0 = prior.margin, prior.total, np.log(np.where(prior.p > 0, prior.p, 1e-300))
    support = prior.p > 0

    def tilted(lam):
        logq = np.where(support, logp0 + lam[0] * m + lam[1] * t, -np.inf)
        logq -= logq[support].max()
        q = np.exp(logq)
        return q / q.sum()

    def resid(lam):
        q = tilted(lam)
        return [(q * m).sum() - target_margin, (q * t).sum() - target_total]

    sol = optimize.root(resid, x0=[0.0, 0.0], method="hybr")
    if not sol.success:
        raise RuntimeError(f"tilt did not converge: {sol.message}")
    return ScoreGrid(tilted(sol.x)), sol.x


def tilt_features(prior: ScoreGrid, lam: np.ndarray) -> ScoreGrid:
    """General exponential tilt with features (margin, total, margin²); lam has length 3."""
    m, t = prior.margin, prior.total
    support = prior.p > 0
    logq = np.where(support, np.log(np.where(support, prior.p, 1.0)) + lam[0] * m + lam[1] * t + lam[2] * m**2, -np.inf)
    logq -= logq[support].max()
    q = np.exp(logq)
    return ScoreGrid(q / q.sum())


def normal_margin_cdf(k: float, spread: float, sd: float = 12.73) -> float:
    """Textbook comparison: margin ~ N(spread, sd²), continuity-corrected at half-points."""
    return float(stats.norm.cdf((k - spread) / sd))


def price_ladder(grid: ScoreGrid, quotes: pd.DataFrame, home_team: str) -> pd.DataFrame:
    """Model price for each Kalshi contract row (needs columns kind, floor_strike, ticker/team)."""
    out = quotes.copy()
    prices = []
    for r in out.itertuples():
        team = r.ticker.rsplit("-", 1)[-1].rstrip("0123456789")
        team = {"WSH": "WAS", "JAC": "JAX", "LAR": "LA"}.get(team, team)
        if r.kind == "winner":
            p = grid.p_home_win() if team == home_team else 1 - grid.p_home_win()
        elif r.kind == "spread":
            p = grid.p_margin_over(r.floor_strike) if team == home_team else grid.p_margin_under(-r.floor_strike)
        else:
            p = grid.p_total_over(r.floor_strike)
        prices.append(p)
    out["model"] = prices
    return out
