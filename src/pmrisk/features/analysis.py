"""Analysis of the pre-game feature table: is it sound, what is in it, and what is worth using?

integrity_checks     accounting identities, ranges, leakage screen, what unplayed games really contain
coverage_by_season   share of non-null values by feature and season
forecast_coverage    the same for unplayed games, by week
signal_table         rank correlation with a target, season by season, with season-level t and BH q-values
redundancy           clusters of near-duplicate features and the variance spectrum
drift_table          how far each feature's level moves across seasons
group_value          walk-forward ridge on each feature group, with paired, clustered comparisons

Everything runs on matchup_view, which reduces each home/away pair to two contrasts: diff_x = home_x - away_x, the
natural regressor for the margin, and avg_x = (home_x + away_x) / 2, the natural regressor for the total (the score
difference and the score sum respond to the teams' strengths in those two combinations; Glickman & Stern 2017).
The table stores diff_x for most pairs and avg_x for none, so both are derived here.
"""

from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .. import DATA_PROCESSED
from .ratings import HFA as ELO_HFA

TABLE = DATA_PROCESSED / "features" / "games_features.parquet"
DICTIONARY = DATA_PROCESSED / "features" / "feature_dictionary.csv"

TARGETS = ["home_score", "away_score", "margin", "total_pts", "home_win"]
MARKET = ["spread_line", "total_line", "home_moneyline", "away_moneyline", "home_spread_odds", "away_spread_odds",
          "over_odds", "under_odds", "market_p_home", "market_overround"]
RELOCATED = {"STL": "LA", "SD": "LAC", "OAK": "LV"}  # game_id keeps the code of the day, the team columns the current one
ID_LIKE = ["gsis", "pff", "ftn"]  # external game ids stored as floats; they rise with time, so they are not features
ALIASES = ["elo_diff", "rest_diff"]  # elo_diff is elo_spread x 25; rest_diff is the derived diff_rest
RAW_WEATHER = ["temp", "wind"]  # temp_filled, wind_filled carry the same values plus the domes
NOT_FEATURES = set(TARGETS + MARKET + ID_LIKE + ALIASES + RAW_WEATHER + ["season", "week"])

WINDOWS = ("l4", "l8", "ewm", "std", "prev")
GROUPS = ("ratings", "team form", "quarterback", "injuries", "situational")
ENCODING_FOR = {"margin": "diff", "margin_vs_spread": "diff", "total_pts": "avg", "total_vs_line": "avg"}
_NAME = re.compile(r"^(?:(home|away|diff|avg)_)?(qb_)?(?:(l4|l8|ewm|std|prev)_)?(.+)$")


def load_table() -> pd.DataFrame:
    return pd.read_parquet(TABLE)


def played(g: pd.DataFrame) -> pd.DataFrame:
    return g[g.home_score.notna()]


def parse_feature(name: str) -> dict:
    """Split e.g. diff_qb_ewm_epa_db into encoding diff, window ewm, stat qb_epa_db, group quarterback."""
    encoding, qb, window, stat = _NAME.match(name).groups()
    stat = f"{qb or ''}{stat}"
    if stat.startswith("inj_"):
        group = "injuries"
    elif stat.startswith("qb_"):
        group = "quarterback"
    elif "elo" in stat or "margin" in stat or "points_" in stat:
        group = "ratings"
    elif window:
        group = "team form"
    else:
        group = "situational"
    return {"feature": name, "encoding": encoding or "none", "window": window, "stat": stat, "group": group}


def describe_features(names) -> pd.DataFrame:
    return pd.DataFrame([parse_feature(n) for n in names]).set_index("feature")


def matchup_view(g: pd.DataFrame) -> pd.DataFrame:
    """Feature matrix for modelling: diff_x and avg_x for every home/away pair, plus the unsided features."""
    numeric = {c for c in g.columns if pd.api.types.is_numeric_dtype(g[c])}
    out = {}
    for c in g.columns:
        if c.startswith("home_") and c not in NOT_FEATURES and c in numeric:
            base, away = c[5:], f"away_{c[5:]}"
            if away in numeric:
                out[f"diff_{base}"] = g[c] - g[away]
                out[f"avg_{base}"] = (g[c] + g[away]) / 2
    for c in g.columns:
        if c in numeric and c not in NOT_FEATURES and not c.startswith(("home_", "away_", "diff_")):
            out[c] = g[c]
    return pd.DataFrame(out, index=g.index)


def target_frame(g: pd.DataFrame) -> pd.DataFrame:
    """The outcomes, and the outcomes net of the closing line: a feature correlated with the latter knows something
    the close does not."""
    return pd.DataFrame({"margin": g.margin, "margin_vs_spread": g.margin - g.spread_line,
                         "total_pts": g.total_pts, "total_vs_line": g.total_pts - g.total_line}, index=g.index)


def features_for(names, target: str) -> list[str]:
    encoding = ENCODING_FOR[target]
    return [n for n in names if n.startswith(f"{encoding}_") or not n.startswith(("diff_", "avg_"))]


# ---- integrity ------------------------------------------------------------------------------------------------------
def integrity_checks(g: pd.DataFrame, dictionary: pd.DataFrame | None = None, leak_threshold: float = 0.6) -> pd.DataFrame:
    """One row per check: status pass, warn (usable, but a modeller must know) or fail (the table is wrong)."""
    rows = []

    def add(check, n_bad, detail="", bad="fail"):
        rows.append({"check": check, "status": bad if n_bad else "pass", "n_bad": int(n_bad), "detail": detail if n_bad else ""})

    def ids(mask, k=5):
        return ", ".join(g.loc[mask, "game_id"].head(k))

    p = played(g)
    add("game_id unique", g.game_id.duplicated().sum(), ids(g.game_id.duplicated()))
    expected = g.season.astype(str) + "_" + g.week.astype(str).str.zfill(2) + "_" + g.away_team + "_" + g.home_team
    current = g.game_id.str.split("_").map(lambda p: "_".join(p[:2] + [RELOCATED.get(t, t) for t in p[2:]]))
    add("game_id matches season, week and teams", (current != expected).sum(), ids(current != expected))
    long = pd.concat([g[["season", "week", "home_team"]].set_axis(["season", "week", "team"], axis=1),
                      g[["season", "week", "away_team"]].set_axis(["season", "week", "team"], axis=1)])
    add("at most one game per team and week", long.duplicated().sum())
    old = g.home_team.isin(list(RELOCATED)) | g.away_team.isin(list(RELOCATED))
    add("franchise codes follow relocations", old.sum(), ids(old))

    add("targets all present or all absent", g[TARGETS].notna().sum(axis=1).isin([0, len(TARGETS)]).eq(False).sum())
    add("margin = home_score - away_score", (p.margin != p.home_score - p.away_score).sum())
    add("total_pts = home_score + away_score", (p.total_pts != p.home_score + p.away_score).sum())
    ties = p[(p.margin == 0) & (p.home_win != 0.5)]
    add("home_win is 0.5 on a tie", len(ties), f"coded {sorted(set(ties.home_win.tolist()))}; winner contracts pay 0.5", "warn")
    late = g.home_score.isna() & (g.kickoff < p.kickoff.max())
    add("no unplayed game before the last played one", late.sum(), ids(late))

    pairs = [(c, f"home_{c[5:]}", f"away_{c[5:]}") for c in g.columns if c.startswith("diff_") and f"home_{c[5:]}" in g]
    pairs += [("rest_diff", "home_rest", "away_rest")]
    broken = [d for d, h, a in pairs if ((g[d] - (g[h] - g[a])).abs() > 1e-9).any() or (g[d].notna() != (g[h] - g[a]).notna()).any()]
    add(f"diff_x = home_x - away_x ({len(pairs)} pairs)", len(broken), ", ".join(broken[:5]))
    hfa = np.where(g.location == "Neutral", 0.0, ELO_HFA)
    add("elo_diff = home_elo + home field - away_elo", ((g.elo_diff - (g.home_elo + hfa - g.away_elo)).abs() > 1e-9).sum())

    num = g.select_dtypes("number")
    inf = np.isinf(num).any()
    add("no infinite values", inf.sum(), ", ".join(inf[inf].index[:5]))
    flat = num.columns[num.nunique() <= 1]
    add("no constant columns", len(flat), ", ".join(flat[:5]), "warn")
    bad_p = (g.market_p_home.notna() & ~g.market_p_home.between(0, 1)) | ~g.elo_p_home.between(0, 1)
    add("probabilities in [0, 1]", bad_p.sum(), ids(bad_p))
    neg = g.market_overround < 0
    add("overround not negative", neg.sum(), ids(neg), "warn")
    add("spread_line positive when the home team is favoured", int(p.spread_line.corr(p.margin) <= 0))
    odd = (g.wind_filled > 40) | ~g.temp_filled.between(-30, 120) & g.temp_filled.notna()
    add("weather plausible (wind <= 40 mph, temp in -30..120 F)", odd.sum(), ids(odd), "warn")
    numeric_ids = [c for c in ID_LIKE if c in num]
    add("external ids are not numeric", len(numeric_ids), f"{', '.join(numeric_ids)} pass an is_numeric_dtype feature filter", "warn")

    # Leakage: nothing pre-game should explain the score this well (the closing line itself reaches about 0.43).
    X = matchup_view(p)
    rho = pd.concat([X.corrwith(p.margin, method="spearman").abs(), X.corrwith(p.total_pts, method="spearman").abs()], axis=1).max(axis=1)
    high = rho[rho > leak_threshold].sort_values(ascending=False)
    add(f"no feature has |rho| > {leak_threshold} with its own game's score", len(high), ", ".join(high.index[:5]))
    teams = pd.concat([g[["kickoff", "home_team", "home_l4_epa_play"]].set_axis(["kickoff", "team", "x"], axis=1),
                       g[["kickoff", "away_team", "away_l4_epa_play"]].set_axis(["kickoff", "team", "x"], axis=1)])
    debut = teams.sort_values("kickoff").groupby("team").head(1)
    add("rolling form is null in a team's first game", debut.x.notna().sum())

    # At forecast time the rolling windows run over the future games' empty rows, so they decay with the horizon.
    u = g[g.home_score.isna()]
    if len(u):
        decayed = {w: float(u[f"home_{w}_epa_play"].isna().mean()) for w in WINDOWS}
        lost = {w: v for w, v in decayed.items() if v > 0}
        add("rolling windows stay populated on unplayed games", len(lost),
            "; ".join(f"{w} null on {v:.0%} of unplayed games" for w, v in lost.items()), "warn")

    # A starter's history must not depend on whether they threw a pass in this game, which is only known afterwards.
    cols = ["game_id", "kickoff", "qb_id", "dropbacks"]
    qb = pd.concat([g[["game_id", "kickoff", f"{side}_qb_id", f"{side}_qb_career_dropbacks"]].set_axis(cols, axis=1) for side in ("home", "away")])
    qb = qb.dropna(subset=["qb_id"]).sort_values("kickoff")
    seen = qb.groupby("qb_id").dropbacks.transform(lambda x: x.shift(1).cummax()) > 0
    lost = qb[seen & (qb.dropbacks == 0)]
    n_future = int(lost.game_id.isin(u.game_id).sum())
    add("a starter with prior dropbacks keeps that history", len(lost),
        f"career_dropbacks = 0 on {n_future} unplayed and {len(lost) - n_future} played team-games, e.g. {', '.join(lost.game_id.tail(3))}; the merge in qb_features needs a row for this game")
    unnamed = g.home_qb_id.isna() & g.home_qb_career_dropbacks.notna()
    add("QB experience is null when no starter is named", unnamed.sum(), f"0 reads as a debut; e.g. {ids(unnamed, 3)}", "warn")
    counts = [c for c in g.columns if c.startswith(("home_inj_", "away_inj_")) and "snapwt" not in c]
    empty = g.home_score.isna() & (g[counts].abs().sum(axis=1) == 0)
    add("injury counts are null when no report exists", empty.sum(), f"no report yet is stored as 0 injured on unplayed games; e.g. {ids(empty, 3)}", "warn")

    if dictionary is not None:
        missing = set(g.columns) ^ set(dictionary.column)
        add("feature dictionary lists exactly the table's columns", len(missing), ", ".join(sorted(missing)[:5]))
        grp = dictionary.set_index("column").group
        filed = [c for c in ID_LIKE + ["old_game_id", "nfl_detail_id", "pfr", "espn", "stadium_id"] if grp.get(c) != "identifiers"]
        add("feature dictionary files ids under identifiers", len(filed), ", ".join(filed[:5]), "warn")
    return pd.DataFrame(rows)


# ---- coverage -------------------------------------------------------------------------------------------------------
def coverage_by_season(X: pd.DataFrame, season: pd.Series) -> pd.DataFrame:
    """Non-null share, feature x season."""
    return X.notna().groupby(season).mean().T.rename_axis("feature")


def forecast_coverage(g: pd.DataFrame) -> pd.DataFrame:
    """Non-null share on unplayed games by week: what a forecast at each horizon actually has to work with."""
    u = g[g.home_score.isna()]
    series = {f"form {w}": u[f"home_{w}_epa_play"] for w in WINDOWS}
    injured = u[[c for c in g.columns if c.startswith(("home_inj_", "away_inj_")) and "snapwt" not in c]].abs().sum(axis=1)
    series |= {"elo": u.home_elo, "named starter": u.home_qb_id, "qb rating": u.home_qb_ewm_epa_db, "injury report": injured.where(injured > 0),
               "weather": u.temp_filled, "closing spread": u.spread_line}
    return pd.DataFrame(series).notna().groupby(u.week).mean()


# ---- signal ---------------------------------------------------------------------------------------------------------
def signal_table(X: pd.DataFrame, y: pd.Series, season: pd.Series, min_games: int = 30, min_seasons: int = 5) -> pd.DataFrame:
    """Spearman correlation of each feature with y, computed within each season and then averaged.

    Within-season ranks keep league-wide drift out of the correlation, and the spread of the season values gives a t
    statistic that respects dependence inside a season (Fama-MacBeth). q is the Benjamini-Hochberg adjustment across
    the features passed in.
    """
    keep = y.notna()
    X, y, season = X[keep], y[keep], season[keep]
    per = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", stats.ConstantInputWarning)  # e.g. a flag that never fires in a season: rho is NaN
        for s, idx in season.groupby(season).groups.items():
            Xs = X.loc[idx]
            per[s] = Xs.corrwith(y.loc[idx], method="spearman").where(Xs.notna().sum() >= min_games)
    per = pd.DataFrame(per).rename_axis("feature")
    n_seasons = per.notna().sum(axis=1)
    per = per[n_seasons >= min_seasons]
    n_seasons = n_seasons[per.index]
    out = pd.DataFrame({"n": X[per.index].notna().sum(), "n_seasons": n_seasons, "rho_mean": per.mean(axis=1),
                        "rho_se": per.std(axis=1, ddof=1) / np.sqrt(n_seasons)})
    out["t"] = out.rho_mean / out.rho_se
    out["p"] = 2 * stats.t.sf(out.t.abs(), n_seasons - 1)
    ok = out.p.notna()
    out["q"] = np.nan
    out.loc[ok, "q"] = stats.false_discovery_control(out.loc[ok, "p"], method="bh")
    out["same_sign"] = per.apply(lambda r: (np.sign(r.dropna()) == np.sign(r.mean())).mean(), axis=1)
    half = per.apply(lambda r: pd.Series({"rho_early": r.dropna().iloc[:len(r.dropna()) // 2].mean(), "rho_late": r.dropna().iloc[len(r.dropna()) // 2:].mean()}), axis=1)
    return out.join(half).rename_axis("feature").sort_values("rho_mean", key=np.abs, ascending=False)


def window_matrix(signal: pd.DataFrame) -> pd.DataFrame:
    """|rho| of each team-form statistic across the five windows, strongest statistic first."""
    d = describe_features(signal.index)
    d = d[d.window.notna()]
    m = signal.rho_mean.abs().reindex(d.index).groupby([d.stat, d.window]).first().unstack("window")
    m = m.reindex(columns=[w for w in WINDOWS if w in m])
    return m.loc[m.max(axis=1).sort_values(ascending=False).index]


# ---- redundancy -----------------------------------------------------------------------------------------------------
def redundancy(X: pd.DataFrame, rho: pd.Series, threshold: float = 0.8) -> tuple[pd.DataFrame, np.ndarray]:
    """Average-linkage clusters on 1 - |r|, cut at |r| = threshold, and the cumulative variance of the correlation
    matrix's eigenvalues. Each cluster's representative is its member most correlated with the target."""
    Z = X.loc[:, X.notna().mean() >= 0.5]
    Z = Z.loc[:, Z.std() > 0]
    Z = Z.fillna(Z.median())
    corr = np.corrcoef(Z.values, rowvar=False)
    dist = np.clip(1 - np.abs(corr), 0, None)
    np.fill_diagonal(dist, 0)
    labels = fcluster(linkage(squareform(dist, checks=False), method="average"), t=1 - threshold, criterion="distance")
    members = pd.DataFrame({"cluster": labels, "rho": rho.reindex(Z.columns).values}, index=pd.Index(Z.columns, name="feature"))
    strength = members.rho.abs().fillna(-1)
    members["representative"] = strength == strength.groupby(members.cluster).transform("max")
    members["cluster_size"] = members.groupby("cluster").rho.transform("size")
    eig = np.linalg.eigvalsh(corr)[::-1]
    return members.sort_values(["cluster_size", "cluster", "representative"], ascending=[False, True, False]), np.cumsum(eig) / eig.sum()


# ---- drift ----------------------------------------------------------------------------------------------------------
def drift_table(X: pd.DataFrame, season: pd.Series, k: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Season means, and for each feature the share of variance between seasons (eta2) and the move from its first k
    seasons of data to its last k, in pooled standard deviations."""
    means = X.groupby(season).mean().T.rename_axis("feature")
    total = ((X - X.mean()) ** 2).sum()
    within = ((X - X.groupby(season).transform("mean")) ** 2).sum()
    first = means.apply(lambda r: r.dropna().iloc[:k].mean(), axis=1)
    last = means.apply(lambda r: r.dropna().iloc[-k:].mean(), axis=1)
    out = pd.DataFrame({"eta2": 1 - within / total.where(total > 0), "first_mean": first, "last_mean": last,
                        "shift_sd": (last - first) / X.std().where(X.std() > 0)})
    return out.rename_axis("feature").sort_values("shift_sd", key=np.abs, ascending=False), means


# ---- value of each group --------------------------------------------------------------------------------------------
def ridge():
    # Same specification as scripts/baseline_models.py. Keeping empty columns matters only before injuries exist.
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), RidgeCV(alphas=np.logspace(-1, 4, 20)))


def cluster_se(d: pd.Series, groups: pd.Series) -> float:
    """Cluster-robust standard error of the mean of d (Liang-Zeger with the G/(G-1) correction)."""
    m = pd.DataFrame({"d": d, "g": groups}).groupby("g").d.agg(["sum", "size"])
    if len(m) < 2:
        return np.nan
    u = m["sum"] - d.mean() * m["size"]
    return float(np.sqrt((u ** 2).sum()) / len(d) * np.sqrt(len(m) / (len(m) - 1)))


def walk_forward_errors(X: pd.DataFrame, y: pd.Series, season: pd.Series, test_seasons) -> pd.Series:
    """Absolute error of a ridge trained on seasons < t and tested on t."""
    err = pd.Series(np.nan, index=X.index)
    for t in test_seasons:
        tr, te = (season < t) & y.notna(), (season == t) & y.notna()
        model = ridge().fit(X[tr], y[tr])
        err[te] = (y[te] - model.predict(X[te])).abs()
    return err


def group_value(X: pd.DataFrame, g: pd.DataFrame, target: str, line: str, test_seasons, min_season: int = 2000) -> pd.DataFrame:
    """Walk-forward MAE of each feature group alone and of all groups with each one removed.

    Every model is compared with the all-groups ridge on the same games: diff > 0 means the model errs by more than
    all-groups, so for a leave-one-out row it is what the group adds. Standard errors are of the paired difference,
    clustered by week and by season.
    """
    keep = (g.season >= min_season) & g[target].notna()
    X, g = X[keep], g[keep]
    y, season = g[target], g.season
    names = features_for(X.columns, target)
    group_of = describe_features(names).group
    errs = {"all groups": walk_forward_errors(X[names], y, season, test_seasons)}
    for grp in GROUPS:
        errs[f"{grp} only"] = walk_forward_errors(X[group_of.index[group_of == grp]], y, season, test_seasons)
        errs[f"all minus {grp}"] = walk_forward_errors(X[group_of.index[group_of != grp]], y, season, test_seasons)
    league = pd.Series(np.nan, index=X.index)
    for t in test_seasons:
        league[season == t] = (y[season == t] - y[season < t].mean()).abs()
    errs["league average"] = league
    errs["closing line"] = (y - g[line]).abs()

    test = season.isin(list(test_seasons)) & g[line].notna()
    week = g.season.astype(str) + "_" + g.week.astype(str)
    base = errs["all groups"][test]
    rows = []
    for name, e in errs.items():
        d = e[test] - base
        row = {"model": name, "mae": e[test].mean(), "diff_vs_all": d.mean()}
        if name != "all groups":
            row |= {"se_week": cluster_se(d, week[test]), "se_season": cluster_se(d, season[test])}
            row["t_week"] = row["diff_vs_all"] / row["se_week"]
        rows.append(row)
    return pd.DataFrame(rows).assign(target=target, n=int(test.sum()))
