import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk.features.analysis import (cluster_se, drift_table, features_for, group_value, integrity_checks, load_table, matchup_view,
                                      parse_feature, played, redundancy, signal_table, walk_forward_errors, window_matrix)


@pytest.fixture(scope="module")
def table():
    return load_table()


def status(g, check_prefix):
    c = integrity_checks(g)
    return c[c.check.str.startswith(check_prefix)].iloc[0]


# ---- names and the matchup view -------------------------------------------------------------------------------------
@pytest.mark.parametrize("name,encoding,window,stat,group", [
    ("diff_ewm_epa_play", "diff", "ewm", "epa_play", "team form"),
    ("avg_l4_def_sacks", "avg", "l4", "def_sacks", "team form"),
    ("diff_qb_ewm_epa_db", "diff", "ewm", "qb_epa_db", "quarterback"),
    ("diff_qb_changed", "diff", None, "qb_changed", "quarterback"),
    ("avg_inj_out_QB", "avg", None, "inj_out_QB", "injuries"),
    ("diff_ewm_adj_margin", "diff", "ewm", "adj_margin", "ratings"),
    ("diff_elo", "diff", None, "elo", "ratings"),
    ("elo_spread", "none", None, "elo_spread", "ratings"),
    ("diff_rest", "diff", None, "rest", "situational"),
    ("short_week_home", "none", None, "short_week_home", "situational"),
])
def test_parse_feature(name, encoding, window, stat, group):
    p = parse_feature(name)
    assert (p["encoding"], p["window"], p["stat"], p["group"]) == (encoding, window, stat, group)


def test_view_excludes_targets_market_and_ids(table):
    cols = set(matchup_view(table.head(50)).columns)
    for c in ["margin", "total_pts", "home_win", "spread_line", "market_p_home", "gsis", "pff", "ftn", "season", "week",
              "diff_score", "avg_score", "diff_moneyline", "diff_spread_odds", "temp", "wind", "elo_diff", "rest_diff"]:
        assert c not in cols
    assert not any(c.startswith(("home_", "away_")) for c in cols)


def test_view_contrasts_are_the_home_and_away_columns(table):
    g = table.head(300)
    X = matchup_view(g)
    pd.testing.assert_series_equal(X.avg_ewm_epa_play, (g.home_ewm_epa_play + g.away_ewm_epa_play) / 2, check_names=False)
    pd.testing.assert_series_equal(X.diff_ewm_epa_play, g.diff_ewm_epa_play, check_names=False)
    pd.testing.assert_series_equal(X.diff_inj_out_QB, g.home_inj_out_QB - g.away_inj_out_QB, check_names=False)  # not stored in the table


def test_features_for_splits_by_encoding():
    names = ["diff_a", "avg_a", "dome"]
    assert features_for(names, "margin") == ["diff_a", "dome"]
    assert features_for(names, "total_vs_line") == ["avg_a", "dome"]


# ---- integrity: the real table, with one thing broken at a time ------------------------------------------------------
def test_real_table_fails_only_known_checks(table):
    """Delete an entry here when the build is fixed; anything new failing is a regression."""
    c = integrity_checks(table)
    known = {"a starter with prior dropbacks keeps that history"}  # qb_features merges on this game's passer rows
    assert set(c.check[c.status == "fail"]) <= known, c[c.status == "fail"].to_string()


def test_flags_a_starter_who_loses_history(table):
    g = table.copy()
    before = status(g, "a starter with prior").n_bad
    i = played(g[g.home_qb_career_dropbacks > 5000]).index[0]
    g.loc[i, "home_qb_career_dropbacks"] = 0
    assert status(g, "a starter with prior").n_bad == before + 1


def test_starter_history_check_clears_when_history_is_filled(table):
    g = table.copy()
    for side in ("home", "away"):
        c = f"{side}_qb_career_dropbacks"
        g.loc[g[f"{side}_qb_id"].notna() & (g[c] == 0), c] = 1.0
    assert status(g, "a starter with prior").status == "pass"


def test_flags_zero_filled_future_injuries(table):
    row = status(table, "injury counts are null")
    u = table[table.home_score.isna()]
    assert row.status == "warn" and 0 < row.n_bad <= len(u)


def test_flags_duplicate_game_id(table):
    g = table.copy()
    g.loc[g.index[1], "game_id"] = g.game_id.iloc[0]
    assert status(g, "game_id unique").status == "fail"


def test_flags_broken_diff(table):
    g = table.copy()
    g.loc[g.index[10], "diff_ewm_epa_play"] = 99.0
    row = status(g, "diff_x = home_x")
    assert row.status == "fail" and "diff_ewm_epa_play" in row.detail


def test_flags_wrong_margin(table):
    g = table.copy()
    g.loc[g.index[0], "margin"] = 99.0
    assert status(g, "margin =").status == "fail"


def test_flags_a_leaked_target(table):
    g = table.copy()
    g["home_ewm_margin"] = g.margin + g.away_ewm_margin  # diff_ewm_margin is now the game's own margin
    g["diff_ewm_margin"] = g.home_ewm_margin - g.away_ewm_margin
    row = status(g, "no feature has")
    assert row.status == "fail" and "diff_ewm_margin" in row.detail


def test_flags_a_missing_result(table):
    g = table.copy()
    i = played(g).sort_values("kickoff").index[100]
    g.loc[i, ["home_score", "away_score", "margin", "total_pts", "home_win"]] = np.nan
    assert status(g, "no unplayed game before").status == "fail"


def test_flags_form_in_a_first_game(table):
    g = table.copy()
    i = g.sort_values("kickoff").index[0]
    g.loc[i, "home_l4_epa_play"] = 0.1
    assert status(g, "rolling form is null").status == "fail"


def test_reports_tie_coding(table):
    g = played(table).copy()
    row = status(table, "home_win is 0.5")
    assert row.n_bad == ((g.margin == 0) & (g.home_win != 0.5)).sum()


# ---- signal ---------------------------------------------------------------------------------------------------------
def panel(n_seasons=20, per_season=250, seed=0):
    rng = np.random.default_rng(seed)
    season = np.repeat(np.arange(2000, 2000 + n_seasons), per_season)
    n = len(season)
    y = rng.normal(size=n)
    X = pd.DataFrame({"real": y + rng.normal(size=n), "drifting": season - season.mean() + rng.normal(scale=0.1, size=n)})
    for i in range(50):
        X[f"noise{i}"] = rng.normal(size=n)
    return X, pd.Series(y), pd.Series(season)


def test_signal_finds_the_real_feature_and_controls_noise():
    X, y, season = panel()
    s = signal_table(X, y, season)
    assert s.index[0] == "real"
    assert s.rho_mean["real"] == pytest.approx(0.69, abs=0.03)  # Spearman of bivariate normal with r = 1/sqrt(2)
    assert s.q["real"] < 1e-6 and s.same_sign["real"] == 1
    assert (s.drop("real").q < 0.05).sum() <= 2


def test_signal_ignores_drift_between_seasons():
    """A feature and a target that merely trend together must not look like signal within seasons."""
    X, y, season = panel()
    trended = y + 0.5 * (season - season.mean())
    pooled = X.drifting.corr(trended, method="spearman")
    s = signal_table(X, trended, season)
    assert pooled > 0.9 and abs(s.rho_mean["drifting"]) < 0.05


def test_signal_requires_enough_seasons():
    X, y, season = panel()
    X["short"] = X.real.where(season < 2003)
    assert "short" not in signal_table(X, y, season).index


def test_signal_skips_rows_without_a_target():
    X, y, season = panel()
    assert signal_table(X, y.where(season < 2010), season).n_seasons.max() == 10


def test_window_matrix_shape():
    sig = pd.DataFrame({"rho_mean": [0.3, -0.2, 0.1]}, index=["diff_l4_a", "diff_ewm_a", "dome"])
    m = window_matrix(sig)
    assert list(m.columns) == ["l4", "ewm"] and m.loc["a", "ewm"] == pytest.approx(0.2)


# ---- redundancy and drift --------------------------------------------------------------------------------------------
def test_redundancy_groups_copies_and_names_the_strongest():
    rng = np.random.default_rng(1)
    a, b = rng.normal(size=500), rng.normal(size=500)
    X = pd.DataFrame({"a1": a, "a2": -a + 0.05 * rng.normal(size=500), "b": b, "flat": 1.0})
    members, cum = redundancy(X, pd.Series({"a1": 0.1, "a2": -0.3, "b": 0.05}))
    assert members.loc["a1", "cluster"] == members.loc["a2", "cluster"] != members.loc["b", "cluster"]
    assert members.loc["a2", "representative"] and not members.loc["a1", "representative"]
    assert "flat" not in members.index
    assert cum[0] == pytest.approx(2 / 3, abs=0.05) and cum[-1] == pytest.approx(1)


def test_drift_measures_a_level_shift():
    rng = np.random.default_rng(2)
    season = pd.Series(np.repeat(np.arange(2000, 2020), 100))
    X = pd.DataFrame({"level": (season >= 2010).astype(float) + rng.normal(scale=0.1, size=2000), "stable": rng.normal(size=2000)})
    d, means = drift_table(X, season)
    assert d.index[0] == "level"
    assert d.eta2["level"] > 0.9 and d.eta2["stable"] < 0.05
    assert d.first_mean["level"] == pytest.approx(0, abs=0.05) and d.last_mean["level"] == pytest.approx(1, abs=0.05)
    assert list(means.columns) == list(range(2000, 2020))


# ---- walk-forward and paired errors ----------------------------------------------------------------------------------
def test_cluster_se_matches_iid_formula_for_singleton_clusters():
    d = pd.Series(np.random.default_rng(3).normal(size=400))
    assert cluster_se(d, pd.Series(np.arange(400))) == pytest.approx(d.std(ddof=1) / 20, rel=1e-9)


def test_cluster_se_grows_with_within_cluster_correlation():
    rng = np.random.default_rng(4)
    groups = pd.Series(np.repeat(np.arange(20), 20))
    shared = pd.Series(rng.normal(size=20)[groups]) + pd.Series(rng.normal(scale=0.1, size=400))
    assert cluster_se(shared, groups) > 3 * shared.std() / 20


def test_walk_forward_cannot_see_the_test_season():
    """A target that flips sign in the test season: a look-ahead fit would track it, an honest one must err badly."""
    rng = np.random.default_rng(5)
    season = pd.Series(np.repeat([2000, 2001], 500))
    x = rng.normal(size=1000)
    y = pd.Series(np.where(season == 2000, x, -x))
    err = walk_forward_errors(pd.DataFrame({"x": x}), y, season, [2001])
    assert err[season == 2000].isna().all()
    assert err[season == 2001].mean() == pytest.approx(2 * np.abs(x[500:]).mean(), rel=0.02)


def test_group_value_on_a_small_window(table):
    p = played(table)
    p = p[p.season.between(2016, 2020)]
    v = group_value(matchup_view(p), p, "margin", "spread_line", [2020], min_season=2016).set_index("model")
    assert v.loc["closing line", "mae"] == pytest.approx((p[p.season == 2020].margin - p[p.season == 2020].spread_line).abs().mean())
    assert v.loc["all groups", "diff_vs_all"] == 0
    assert v.n.iloc[0] == (p.season == 2020).sum()
