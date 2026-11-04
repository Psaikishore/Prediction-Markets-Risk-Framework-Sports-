"""Tests of independence between NFL games, for pricing cross-game parlays as a product of legs.

Three statistics, each with a null distribution built by simulation or permutation so that pairs of games that
share a week (and therefore share games) are not treated as independent observations:

- `pair_corr`: average correlation of residuals (outcome minus market expectation) between games in the same group.
- `dispersion`: variance of the weekly count of events (e.g. upsets) over the variance independence implies.
- `parlay_hit_rates`: hit rate of a set of parlays under simulated independent game outcomes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import norm


def devig(home_ml, away_ml) -> np.ndarray:
    """Home win probability from American moneylines, with the book's margin removed proportionally."""
    def implied(m):
        m = np.asarray(m, dtype=float)
        return np.where(m < 0, -m, 100) / (np.abs(m) + 100)
    h, a = implied(home_ml), implied(away_ml)
    return h / (h + a)


def pair_corr(r: np.ndarray, groups: np.ndarray) -> tuple[float, int]:
    """Mean of r_i * r_j over all pairs i < j in the same group, divided by var(r). Returns (corr, n_pairs)."""
    r = np.asarray(r, dtype=float) - np.mean(r)
    codes = pd.factorize(groups)[0]
    s = np.bincount(codes, weights=r)
    s2 = np.bincount(codes, weights=r * r)
    n = np.bincount(codes)
    n_pairs = int((n * (n - 1) // 2).sum())
    return float(((s * s - s2) / 2).sum() / n_pairs / r.var()), n_pairs


def pair_corr_null(r, groups, strata, n_perm=2000, seed=0) -> np.ndarray:
    """pair_corr after shuffling group labels within each stratum (season): keeps group sizes, breaks grouping."""
    rng = np.random.default_rng(seed)
    groups, strata = np.asarray(groups), np.asarray(strata)
    idx = [np.flatnonzero(strata == s) for s in np.unique(strata)]
    out = np.empty(n_perm)
    for k in range(n_perm):
        g = groups.copy()
        for i in idx:
            g[i] = g[rng.permutation(i)]
        out[k] = pair_corr(r, g)[0]
    return out


def dispersion(y: np.ndarray, p: np.ndarray, groups: np.ndarray) -> float:
    """sum_w (count_w - expected_w)^2 / sum_w var_w: 1 if events are independent, > 1 if they bunch together."""
    codes = pd.factorize(groups)[0]
    dev = np.bincount(codes, weights=np.asarray(y, float) - p)
    var = np.bincount(codes, weights=p * (1 - p))
    return float((dev ** 2).sum() / var.sum())


def dispersion_null(p, groups, n_sim=2000, seed=0) -> np.ndarray:
    """dispersion under independent Bernoulli(p) outcomes."""
    rng = np.random.default_rng(seed)
    return np.array([dispersion(rng.random(len(p)) < p, p, groups) for _ in range(n_sim)])


def leg_matrices(parlay_idx, game_idx, needs_home, n_parlays, n_games):
    """Two sparse incidence matrices (parlays x games): legs that need the home team to win, and the away team."""
    parlay_idx, game_idx, needs_home = map(np.asarray, (parlay_idx, game_idx, needs_home))
    def mat(mask):
        return sparse.csr_matrix((np.ones(mask.sum(), np.float32), (parlay_idx[mask], game_idx[mask])), shape=(n_parlays, n_games))
    return mat(needs_home), mat(~needs_home)


def parlay_hit_rates(A_home, A_away, q_home, buckets, n_sim=1000, seed=0, chunk=100) -> np.ndarray:
    """Hit rate per bucket in each of n_sim seasons of independent game outcomes, home win ~ Bernoulli(q_home).

    Returns an (n_sim, n_buckets) array. A parlay hits when none of its legs fails.
    """
    rng = np.random.default_rng(seed)
    codes, uniq = pd.factorize(buckets, sort=True)
    size = np.bincount(codes, minlength=len(uniq))
    B = sparse.csr_matrix((np.ones(len(codes), np.float32), (codes, np.arange(len(codes)))), shape=(len(uniq), len(codes)))
    out = []
    for start in range(0, n_sim, chunk):
        k = min(chunk, n_sim - start)
        H = (rng.random((len(q_home), k)) < q_home[:, None]).astype(np.float32)
        fails = A_home @ (1 - H) + A_away @ H
        out.append((B @ (fails == 0).astype(np.float32)).T / size)
    return np.vstack(out)


def copula_hit_ratio(p: float, n_legs: int, rho_latent: float, n_sim=400_000, seed=0) -> tuple[float, float]:
    """P(all n legs hit) / p**n when the legs' latent normals share correlation rho_latent (Gaussian copula).

    Returns (ratio, outcome correlation between two legs). rho_latent must exceed -1/(n_legs-1).
    """
    rng = np.random.default_rng(seed)
    cov = np.full((n_legs, n_legs), rho_latent) + (1 - rho_latent) * np.eye(n_legs)
    z = rng.multivariate_normal(np.zeros(n_legs), cov, size=n_sim, method="cholesky")
    hit = z < norm.ppf(p)
    both = (hit[:, 0] & hit[:, 1]).mean()
    rho_outcome = (both - p * p) / (p * (1 - p))
    return float(hit.all(axis=1).mean() / p ** n_legs), float(rho_outcome)
