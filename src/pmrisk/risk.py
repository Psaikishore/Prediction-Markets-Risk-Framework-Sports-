"""Pre-game line risk for Kalshi NFL contracts: Greeks with respect to the line, and historical-simulation VaR.

Before kickoff a winner, spread or total contract is (to first order) a function of two state variables,
the market's spread s and total t. The score grid tilted to (s, t) gives that function, so

    price(contract) = Q_{s,t}(payoff region),   Q_{s,t} = tilt(prior, s, t).

Greeks. Q_{s,t} is an exponential family in the tilt parameters λ with sufficient statistic T = (margin, total),
so dE[f]/dλ = Cov(f, T) and d(s, t)/dλ = Cov(T). By the chain rule the line delta is exact and needs no re-tilt:

    (∂P/∂s, ∂P/∂t) = Cov(f, T) · Cov(T)⁻¹.

Gammas are central differences of that analytic delta.

VaR. Line moves (Δs, Δt) from the sportsbook open to the close are the scenarios; each is revalued in full on a
precomputed lattice of tilted grids (no delta-gamma approximation, which matters for strikes near the line).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .nfl import KALSHI_TO_NFLVERSE, nfelo_game_id
from .score_model import MAX_PTS, ScoreGrid, tilt

KINDS = ("winner", "spread", "total")


@dataclass(frozen=True)
class Contract:
    """One Kalshi YES contract. `side` is "home" or "away" for winner/spread, "over" for totals.

    spread: side home, strike k pays if home − away > k; side away pays if away − home > k.
    qty is signed (negative = short YES); P&L is qty × change in price, in dollars.
    """
    kind: str
    side: str
    strike: float = 0.0
    qty: float = 1.0

    def payoff(self, grid: ScoreGrid) -> np.ndarray:
        m, t = grid.margin, grid.total
        if self.kind == "winner":
            win = (m > 0) if self.side == "home" else (m < 0)
            return win + 0.5 * (m == 0)
        if self.kind == "spread":
            return ((m > self.strike) if self.side == "home" else (m < -self.strike)).astype(float)
        return (t > self.strike).astype(float)


def contract_from_market(ticker: str, kind: str, floor_strike: float, home_team: str, qty: float = 1.0) -> Contract:
    """Kalshi market row -> Contract, using the team code at the end of the ticker (same rule as price_ladder)."""
    if kind == "total":
        return Contract("total", "over", float(floor_strike), qty)
    team = ticker.rsplit("-", 1)[-1].rstrip("0123456789")
    side = "home" if KALSHI_TO_NFLVERSE.get(team, team) == home_team else "away"
    return Contract(kind, side, 0.0 if kind == "winner" else float(floor_strike), qty)


# -- Greeks ---------------------------------------------------------------------------------------------

def line_delta(grid: ScoreGrid, payoff: np.ndarray) -> np.ndarray:
    """Exact (∂P/∂spread, ∂P/∂total) for a tilted grid: Cov(f, T) Cov(T)⁻¹ with T = (margin, total)."""
    p = grid.p
    T = np.stack([grid.margin * np.ones_like(p), grid.total * np.ones_like(p)])
    Tc = T - (p * T).sum(axis=(1, 2))[:, None, None]
    fc = payoff - (p * payoff).sum()
    cov_fT = (p * fc * Tc).sum(axis=(1, 2))
    cov_TT = np.einsum("ihw,jhw,hw->ij", Tc, Tc, p)
    return np.linalg.solve(cov_TT, cov_fT)


def line_greeks(prior: ScoreGrid, spread: float, total: float, contract: Contract, h: float = 0.5) -> dict:
    """Price, deltas and gammas of one contract with respect to the spread (home margin) and total."""
    g0, _ = tilt(prior, spread, total)
    f = contract.payoff(g0)
    d0 = line_delta(g0, f)
    gs_up, gs_dn = tilt(prior, spread + h, total)[0], tilt(prior, spread - h, total)[0]
    gt_up, gt_dn = tilt(prior, spread, total + h)[0], tilt(prior, spread, total - h)[0]
    ds = (line_delta(gs_up, f) - line_delta(gs_dn, f)) / (2 * h)
    dt = (line_delta(gt_up, f) - line_delta(gt_dn, f)) / (2 * h)
    return {"price": float((g0.p * f).sum()), "delta_spread": float(d0[0]), "delta_total": float(d0[1]),
            "gamma_spread": float(ds[0]), "gamma_total": float(dt[1]), "cross_gamma": float(0.5 * (ds[1] + dt[0]))}


# -- price lattice -------------------------------------------------------------------------------------------

class PriceLattice:
    """Margin and total CDFs of the tilted grid on a (spread, total) lattice, for fast full revaluation.

    Every winner/spread/total contract depends on the grid only through one marginal, so storing the two
    marginal CDFs per lattice point prices any contract at any lattice point by lookup; off-lattice (s, t)
    is bilinear interpolation.
    """

    def __init__(self, prior: ScoreGrid, spreads: np.ndarray, totals: np.ndarray):
        self.spreads, self.totals = np.asarray(spreads, float), np.asarray(totals, float)
        self.margin_values = np.arange(-MAX_PTS, MAX_PTS + 1)
        self.total_values = np.arange(0, 2 * MAX_PTS + 1)
        ns, nt = len(self.spreads), len(self.totals)
        self.margin_pmf = np.zeros((ns, nt, len(self.margin_values)), dtype=np.float32)
        self.total_pmf = np.zeros((ns, nt, len(self.total_values)), dtype=np.float32)
        m_idx = (prior.margin + MAX_PTS).ravel()
        t_idx = prior.total.ravel()
        for i, s in enumerate(self.spreads):
            for j, t in enumerate(self.totals):
                q = tilt(prior, s, t)[0].p.ravel()
                self.margin_pmf[i, j] = np.bincount(m_idx, q, len(self.margin_values))
                self.total_pmf[i, j] = np.bincount(t_idx, q, len(self.total_values))
        self._prep()

    def _prep(self):
        self.margin_cdf = np.cumsum(self.margin_pmf, axis=-1)
        self.total_cdf = np.cumsum(self.total_pmf, axis=-1)

    def save(self, path):
        np.savez_compressed(path, spreads=self.spreads, totals=self.totals,
                            margin_pmf=self.margin_pmf, total_pmf=self.total_pmf)

    @classmethod
    def load(cls, path) -> "PriceLattice":
        z = np.load(path)
        obj = cls.__new__(cls)
        obj.spreads, obj.totals = z["spreads"], z["totals"]
        obj.margin_values = np.arange(-MAX_PTS, MAX_PTS + 1)
        obj.total_values = np.arange(0, 2 * MAX_PTS + 1)
        obj.margin_pmf, obj.total_pmf = z["margin_pmf"], z["total_pmf"]
        obj._prep()
        return obj

    def surface(self, c: Contract) -> np.ndarray:
        """Price of the contract at every lattice point, shape (n_spreads, n_totals)."""
        def mcdf(k):  # P(margin <= k) for integer k
            return self.margin_cdf[..., int(np.clip(k + MAX_PTS, -1, 2 * MAX_PTS))] if k >= -MAX_PTS else 0.0
        if c.kind == "winner":
            p_tie = self.margin_pmf[..., MAX_PTS]
            home = 1 - mcdf(0) + 0.5 * p_tie
            return home if c.side == "home" else 1 - home
        if c.kind == "spread":
            k = int(np.floor(c.strike))
            return 1 - mcdf(k) if c.side == "home" else mcdf(-k - 1)
        k = int(np.floor(c.strike))
        return 1 - self.total_cdf[..., k]

    def interp(self, surface: np.ndarray, s, t) -> np.ndarray:
        """Bilinear interpolation of a lattice surface at arrays of (s, t), clipped to the lattice."""
        s = np.clip(np.asarray(s, float), self.spreads[0], self.spreads[-1])
        t = np.clip(np.asarray(t, float), self.totals[0], self.totals[-1])
        i = np.clip(np.searchsorted(self.spreads, s) - 1, 0, len(self.spreads) - 2)
        j = np.clip(np.searchsorted(self.totals, t) - 1, 0, len(self.totals) - 2)
        ws = (s - self.spreads[i]) / (self.spreads[i + 1] - self.spreads[i])
        wt = (t - self.totals[j]) / (self.totals[j + 1] - self.totals[j])
        return ((1 - ws) * (1 - wt) * surface[i, j] + ws * (1 - wt) * surface[i + 1, j]
                + (1 - ws) * wt * surface[i, j + 1] + ws * wt * surface[i + 1, j + 1])

    def value(self, contracts: list[Contract], s, t) -> np.ndarray:
        """Mark-to-model value of a position (sum of qty × price) at (s, t)."""
        return sum(c.qty * self.interp(self.surface(c), s, t) for c in contracts)

    def implied_line(self, surfaces: np.ndarray, mids: np.ndarray, weights: np.ndarray | None = None,
                     total0: float = 45.0, sweeps: int = 3) -> tuple[float, float, float]:
        """(spread, total, rmse) on the lattice that best fits observed mids by weighted least squares.

        `surfaces` is a stack of self.surface(c) for the observed contracts, shape (n, n_spreads, n_totals).
        Winner and spread prices barely depend on the total and total prices barely on the spread, so
        coordinate descent along the two lattice axes reaches the lattice optimum in a couple of sweeps.
        """
        w = np.ones(len(mids)) if weights is None else np.asarray(weights, float)
        mids = np.asarray(mids, float)[:, None]
        j = int(np.argmin(np.abs(self.totals - total0)))
        for _ in range(sweeps):
            i = int(np.argmin((w[:, None] * (surfaces[:, :, j] - mids) ** 2).sum(0)))
            j = int(np.argmin((w[:, None] * (surfaces[:, i, :] - mids) ** 2).sum(0)))
        sse = float((w * (surfaces[:, i, j] - mids[:, 0]) ** 2).sum())
        return float(self.spreads[i]), float(self.totals[j]), float(np.sqrt(sse / w.sum()))


# -- line moves and VaR ----------------------------------------------------------------------------------------

def line_moves(nfelo: pd.DataFrame) -> pd.DataFrame:
    """Open-to-close moves from the nfelo game file, in the home-margin convention (positive = home favoured)."""
    out = pd.DataFrame({"game_id": nfelo.game_id.map(nfelo_game_id), "season": nfelo.game_id.str[:4].astype(int),
                        "spread_open": -nfelo.home_line_open, "spread_close": -nfelo.home_line_close,
                        "total_open": nfelo.total_line_open, "total_close": nfelo.total_line_close})
    out["d_spread"] = out.spread_close - out.spread_open
    out["d_total"] = out.total_close - out.total_open
    return out.dropna(subset=["d_spread"]).reset_index(drop=True)


def scenario_pnl(lattice: PriceLattice, contracts: list[Contract], spread: float, total: float,
                 d_spread: np.ndarray, d_total: np.ndarray) -> np.ndarray:
    """P&L of the position under each (Δs, Δt) scenario, full revaluation on the lattice."""
    v0 = lattice.value(contracts, spread, total)
    return lattice.value(contracts, spread + np.asarray(d_spread), total + np.asarray(d_total)) - v0


def var_es(pnl: np.ndarray, alpha: float = 0.95) -> tuple[float, float]:
    """Historical VaR and expected shortfall at level alpha, reported as positive losses."""
    loss = -np.asarray(pnl)
    var = float(np.quantile(loss, alpha))
    return var, float(loss[loss >= var].mean())
