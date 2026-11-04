import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk.independence import (copula_hit_ratio, devig, dispersion, dispersion_null, leg_matrices, pair_corr,
                                 pair_corr_null, parlay_hit_rates)

rng = np.random.default_rng(0)
WEEKS = np.repeat(np.arange(200), 14)  # 200 weeks of 14 games
SEASON = WEEKS // 18


def test_devig_removes_the_margin():
    assert devig(-110, -110) == pytest.approx(0.5)
    assert devig(-500, 380) == pytest.approx((500 / 600) / (500 / 600 + 100 / 480))


def test_pair_corr_finds_a_planted_weekly_shock_and_not_a_missing_one():
    noise = rng.normal(size=len(WEEKS))
    shocked = noise + 0.5 * rng.normal(size=200)[WEEKS]  # pairwise correlation 0.25 / 1.25 = 0.2
    assert pair_corr(shocked, WEEKS)[0] == pytest.approx(0.2, abs=0.05)
    null = pair_corr_null(noise, WEEKS, SEASON, n_perm=300)
    rho = pair_corr(noise, WEEKS)[0]
    assert np.percentile(null, 1) < rho < np.percentile(null, 99)


def test_dispersion_is_one_when_independent_and_larger_when_events_bunch():
    p = np.full(len(WEEKS), 0.3)
    assert dispersion(rng.random(len(p)) < p, p, WEEKS) == pytest.approx(1.0, abs=0.25)
    week_p = np.clip(0.3 + 0.15 * rng.normal(size=200), 0.01, 0.99)[WEEKS]  # bad weeks for everyone
    bunched = rng.random(len(p)) < week_p
    assert dispersion(bunched, p, WEEKS) > np.percentile(dispersion_null(p, WEEKS, 300), 99)


def test_simulated_parlay_hit_rate_matches_the_product():
    q = np.array([0.7, 0.6, 0.55, 0.8])
    # parlay 0: home in games 0 and 1; parlay 1: away in game 2 and home in game 3
    A_home, A_away = leg_matrices([0, 0, 1, 1], [0, 1, 2, 3], np.array([True, True, False, True]), 2, 4)
    rates = parlay_hit_rates(A_home, A_away, q, np.array(["a", "b"]), n_sim=20000).mean(axis=0)
    assert rates == pytest.approx([0.7 * 0.6, 0.45 * 0.8], abs=0.01)


def test_copula_with_no_correlation_multiplies():
    ratio, rho = copula_hit_ratio(0.65, 4, 0.0, n_sim=200_000)
    assert ratio == pytest.approx(1.0, abs=0.03)
    assert rho == pytest.approx(0.0, abs=0.01)
