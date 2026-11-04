// Builds reports/NFL_two_output_random_forest.docx with embedded figures. Run: npm install docx && node scripts/build_report_docx.js

const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ImageRun,
        AlignmentType, LevelFormat, BorderStyle, ShadingType } = require("docx");
const FIG = "/Users/kishore/Documents/NYU_FRE/Prediction-Markets-Risk-Framework-Sports-/reports/figures/";
const PAGE_W = 12240, MARGIN = 1440, BODY_W = PAGE_W - 2 * MARGIN; // DXA

function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }
function figure(name, widthIn, caption) {
  const buf = fs.readFileSync(FIG + name + ".png"); const { w, h } = pngSize(buf);
  const wpx = Math.round(widthIn * 96), hpx = Math.round(wpx * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: hpx } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: caption, italics: true, size: 18, color: "555555" })] }),
  ];
}
const P = (text, opts = {}) => new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text, ...opts })] });
const PR = (runs) => new Paragraph({ spacing: { after: 120 }, children: runs.map(r => typeof r === "string" ? new TextRun(r) : new TextRun(r)) });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [new TextRun(t)] });
const B = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 }, children: [new TextRun(t)] });
const N = (t) => new Paragraph({ numbering: { reference: "numbers", level: 0 }, spacing: { after: 80 }, children: [new TextRun(t)] });
const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(rows, widthsIn) {
  const total = widthsIn.reduce((a, b) => a + b, 0); const cw = widthsIn.map(w => Math.round(BODY_W * w / total));
  return new Table({ width: { size: BODY_W, type: WidthType.DXA }, columnWidths: cw,
    rows: rows.map((r, i) => new TableRow({ tableHeader: i === 0, children: r.map((c, j) => new TableCell({
      width: { size: cw[j], type: WidthType.DXA }, borders, margins: { top: 60, bottom: 60, left: 90, right: 90 },
      shading: i === 0 ? { type: ShadingType.CLEAR, fill: "E8EEF6", color: "auto" } : undefined,
      children: [new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: String(c), bold: i === 0, size: 19 })] })] })) })) });
}
const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });

const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Predicting NFL Team Scores with a Two-Output Random Forest")] }),
  P("Sai Kishore, NYU Financial Engineering. October 2026 (revised 20 October with follow-ups).", { italics: true }),

  H1("Summary"),
  P("The goal is to predict the final score of both teams in an NFL game using only information available before kickoff. I trained a random forest with two outputs (home score, away score) on 759 pre-game features covering about 7,000 games since 1999, and tested it season by season from 2010 to 2025, always training on past seasons only."),
  P("The forest predicts each team's score with a mean absolute error of about 7.5 points and the margin with an error of 10.35 points. An Elo rating built from results alone gets 10.38, a linear model gets 10.34, and the Vegas closing line gets 10.05. So the model is a point better than guessing the league average, slightly better than Elo, and a third of a point behind the market. This is the same gap the academic literature has reported since 1980, which I take as a sign that the pipeline is correct rather than a disappointment."),
  P("The two predicted scores are well calibrated, and the errors around them have standard deviations of 9.6 and 9.4 points with almost no correlation. Those three numbers are what is needed to turn a pair of predicted scores into a probability for any outcome, and the next step is to predict them game by game."),

  H1("How I am thinking about the problem"),
  P("Everything we eventually want (who wins, by how much, how many total points) is a question about the joint distribution of the two final scores. Predicting each team's score is the natural first step: the two predictions give the centre of that distribution, and the spread of the errors around them gives its width. A model that only predicts the margin throws away the level of scoring, and a 30-27 game is not the same as a 17-14 game even though both have margin 3."),
  P("Three facts from the historical data shaped the design."),
  B("Margins are lumpy. The margin of victory is exactly 3 in 14.8% of games and exactly 7 in 8.7%, about three times and twice what a normal distribution would say. Any smooth distribution placed on the predicted scores will get these wrong, so I keep an empirical table of historical scores and use the model to shift it."),
  B("Margin and total are almost uncorrelated (0.03) but never independent: they are the difference and sum of the same two integers and always have the same parity. That is why I model the two scores and derive margin and total, instead of modelling margin and total directly."),
  B("The closing line is unbiased and well calibrated, with a residual standard deviation of 12.7 points on the margin. It is the benchmark, and no published model beats it by more than noise."),
  ...figure("nfl_abs_margin", 6.3, "Figure 1. Absolute margin of victory, 2015-2026 (3,076 games). Key numbers 3, 7, 6, 10, 14 in orange."),

  H1("What the literature says"),
  PR([{ text: "Ratings from scores. ", bold: true }, "Harville (1980) fit a mixed linear model to score differences and got an average error of 10.68 points versus 10.49 for the bookmaker. Glickman and Stern (1998) let team strength drift week to week in a state-space model and matched the Vegas line. Their 2017 handbook chapter surveys these methods and recommends entering each statistic as the difference and the average of the two teams, which I followed. FiveThirtyEight's Elo is the practical version: one strength number per team, updated from margin of victory, with home-field, rest and quarterback adjustments."]),
  PR([{ text: "Exact scores. ", bold: true }, "Baker and McHale (2013) is the only paper that forecasts both teams' exact NFL scores; it does about as well as the bookmaker. Stern (1991) showed that margin minus spread is roughly normal with standard deviation near 14, which is how a spread is turned into a win probability."]),
  PR([{ text: "Play-level data. ", bold: true }, "Yurko, Ventura and Horowitz (2019) defined expected points and win probability from play-by-play data. Expected points added (EPA) per play is now the standard efficiency measure, and the nflverse project provides it for every play since 1999. Most of my team-form features come from it."]),
  PR([{ text: "Market efficiency. ", bold: true }, "Levitt (2004) showed that bookmakers set lines as skilled forecasts rather than to balance money, which is why the closing line is hard to beat. Boulier and Stekler (2003) and Song, Boulier and Stekler (2007) found the market more accurate than both statistical systems and experts. Gray and Gray (1997) and Zuber, Gandar and Bowers (1985) found only small, unstable inefficiencies."]),
  PR([{ text: "Machine learning papers. ", bold: true }, "Several report 70-95% accuracy at picking winners. Where methods are described, this comes from using same-game statistics (leakage) or tiny test sets. The closing line picks winners about 66% of the time, so I treat anything far above that as suspect. Two lessons: build an explicit leakage test, and do not expect a flexible learner to add much over a good rating model with 7,000 games."]),
  P("The professors' suggestions fit this picture: a multi-output random forest can use every feature without selection, a linear baseline shows whether the forest adds anything, and a probabilistic extension (two means, two standard deviations, a correlation) is the natural destination for a two-score model."),

  H1("Data"),
  P("All data is free and public from nflverse. The feature table has 7,548 games (1999-2026), one row per game with the home team first, and 805 columns."),
  table([
    ["Group", "Columns", "Content", "From"],
    ["Team form", "604", "20 offensive and 20 defensive efficiency stats from play-by-play (EPA/play, success rate, pass/rush splits, explosive plays, yards/play, CPOE, turnovers, sacks, third downs, points per drive), each over five windows (last 4, last 8, exponentially weighted, season to date, last season), for home, away and the difference", "1999 (CPOE 2006)"],
    ["Ratings", "68", "Pre-game Elo, exponentially weighted margin, opponent-adjusted margin", "1999"],
    ["Quarterback", "23", "Starter's weighted EPA per dropback, CPOE, sack and interception rates, career dropbacks, starter-change flag", "1999"],
    ["Injuries", "44", "Players Out/Doubtful and Questionable by position group; snap share of players now out", "2009 (snaps 2013)"],
    ["Situational", "31", "Rest, bye, short week, primetime, dome, surface, temperature, wind, divisional, playoff", "1999"],
    ["Market", "10", "Closing spread, total, moneylines. Used only as a benchmark, never as a feature", "1999"],
    ["Targets", "5", "Home score, away score, margin, total, home win", "1999"],
  ], [1.1, 0.7, 4.6, 1.2]),
  gap(),
  PR([{ text: "Nothing from the game itself. ", bold: true }, "Rolling stats are shifted by one game, Elo is the pre-update value, and injuries come from the report before the game. A test takes one game, multiplies its play statistics by 10 and adds 30 points to its score, rebuilds the table, and checks that the game's own features are unchanged while the teams' later games change. Six random games pass."]),
  P("The test caught a real problem. The nflverse schedule has two post-game fields, result and total, that equal the margin and the total. The first forest I trained included them and reported a margin error of 2.4 points, with 85% of its importance on those two columns. That is what leakage looks like. I removed them and checked that no remaining column has correlation above 0.6 with any target."),

  H1("Model and evaluation"),
  table([
    ["Model", "Inputs", "Role"],
    ["League average", "Mean scores in the training seasons", "Floor"],
    ["Elo", "Results only", "Rating baseline from the literature"],
    ["Two-output ridge", "759 features, standardised, median-imputed", "Linear baseline"],
    ["Two-output random forest", "759 features, 500 trees, min 20 games per leaf, 30% of features per split, no tuning", "Main model"],
    ["Closing line", "Sportsbook spread and total", "Benchmark"],
  ], [1.6, 3.6, 1.8]),
  gap(),
  P("The forest predicts the two scores together: each leaf holds the mean home and away score of similar past games. Evaluation is walk-forward: train on every season before year t, test on year t, for t = 2010 to 2025 (4,363 test games). I did not use random splits because games within a season are related through the teams. Margin and total are the difference and sum of the two predicted scores."),

  H1("Results"),
  H2("Point accuracy"),
  P("Mean absolute error in points over the 16 test seasons."),
  table([
    ["Model", "Home score", "Away score", "Margin", "Total"],
    ["League average", "8.09", "7.91", "11.18", "11.02"],
    ["Elo", "", "", "10.38", ""],
    ["Two-output ridge", "7.62", "7.40", "10.34", "10.63"],
    ["Two-output random forest", "7.63", "7.45", "10.35", "10.66"],
    ["Closing line", "", "", "10.05", "10.47"],
  ], [2.4, 1.1, 1.1, 1.1, 1.1]),
  gap(),
  P("The forest explains about 11% of the variance of the home score and 9% of the away score out of sample. That sounds low but is normal here: a single game is mostly noise, and even the closing line explains only a little more. The forest and the ridge are indistinguishable. Both are 0.03-0.04 points better than Elo, within one standard error, and 0.3 points worse than the line. The forest picks the winner 64.7% of the time against 66.3% for the line, and picks the side that covers the spread 49.9% of the time, which is what an efficient market implies."),
  ...figure("rf_mae_by_season", 6.3, "Figure 2. Margin error by test season. All methods share the hard and easy seasons; the closing line is lowest in 15 of 16."),
  ...figure("rf_pred_vs_actual", 6.3, "Figure 3. Left: predicted vs actual margin. Right: the forest's margin against the closing spread (correlation 0.86)."),

  H2("The two-output structure"),
  P("Because the forest predicts a point in the (home score, away score) plane, its errors describe a two-dimensional distribution around that point."),
  table([
    ["Quantity", "Home", "Away"],
    ["Std. dev. of actual score", "10.21", "9.83"],
    ["Std. dev. of residual", "9.64", "9.36"],
    ["Range of predictions", "15.8 to 33.3", "13.3 to 30.4"],
    ["Residual std. dev., lowest third of predictions", "9.20", "8.88"],
    ["Residual std. dev., highest third of predictions", "10.11", "9.76"],
  ], [3.6, 1.6, 1.6]),
  gap(),
  P("The correlation between the home and away residuals is 0.01: once the two means are set, the leftover error in one score says nothing about the other. The spread of the errors grows with the predicted score, so high-scoring games are less predictable in points, as a Poisson-like scoring process would imply. Calibration per score is good: when the forest predicts 20, the team scores 20 on average, across the whole range."),
  ...figure("rf_bivariate", 6.5, "Figure 4. Calibration of the home and away score predictions, and the joint distribution of the two residuals."),
  P("Using these pooled residuals as a bivariate normal around the two predicted scores gives a home-win probability with Brier score 0.221 over 2016-2025, against 0.222 for Elo and 0.211 for the de-vigged moneyline. The probabilities are calibrated; the gap to the market is in sharpness, not bias."),
  ...figure("rf_calibration", 4.2, "Figure 5. Calibration of home-win probabilities, 2016-2025."),

  H2("What the forest uses"),
  P("The five most important features are all team-strength summaries from results: the opponent-adjusted weighted margin difference, the weighted margin difference, and the three Elo features. The first play-by-play feature is yards per play at sixth, followed by the starting quarterback's success rate and EPA per dropback and points per drive. Injury, rest and weather features are far down. Most of what the model knows is how good each team has been; the efficiency and quarterback features refine that at the margin. The forest used all 759 features with no selection or tuning and matched a regularised linear model, which is what Professor Shasha expected."),
  ...figure("rf_importance", 5.4, "Figure 6. Top 25 features by mean impurity importance over the 16 fits."),

  H1("What I learned"),
  B("Point accuracy is capped near the closing line for every method tried here and in the literature. The useful goal is a calibrated distribution over both scores, not a lower point error."),
  B("With about 7,000 games the forest and the linear model tie. The information is in the features, and the features are mostly ratings."),
  B("Leakage is the main risk and is easy to introduce by accident. The perturbation test and a sanity check against the literature's error levels are both needed."),
  B("The two-output residuals are simple: uncorrelated, roughly normal, variance rising with scoring. A model for those parameters is feasible."),

  H1("Limitations"),
  B("Uncertainty is pooled across games. The forest's per-tree disagreement has correlation 0.04 with the actual error, so it is not a useful game-level proxy."),
  B("Seasons 1999-2025 are weighted equally despite changes in the scoring environment (season mean totals range from 43.6 to 49.5)."),
  B("No travel distance or precipitation; nflverse has no stadium coordinates."),
  B("For future weeks the starting quarterback is not yet known, so those features are missing until a starter is listed."),
  B("The forest is untuned; gradient boosting and a tuned forest are the obvious comparisons."),

  H1("Next steps"),
  N("Probabilistic head: predict the two means, two standard deviations and the correlation per game, trained on the bivariate log-likelihood, as suggested. Compare it with the empirical score table near key numbers."),
  N("The other suggested methods on the same table: LARS, gradient boosting, PCA and UMAP for exploration, and a cascade-correlation network."),
  N("Separate offence and defence ratings in the Glickman and Stern form, so each predicted score has its own strength input."),
  N("Recency weighting or a season drift term for scoring levels."),
  N("Weekly updates through the 2026 season to build a live out-of-sample record."),

  H1("Follow-up: ensembles"),
  P("Question from Professor Shasha: can an ensemble of the prediction models we have, or can get, do better? I tested this with stacking: fit least-squares weights on earlier seasons' out-of-sample predictions, apply them to the next season, 2013-2025. I added two public forecasts, the nfelo model (a public Elo variant with a quarterback adjustment) and FiveThirtyEight's Elo (available to 2020), and the sportsbook opening line."),
  table([
    ["Forecast", "Margin MAE 2013-2025", "Note"],
    ["Random forest (ours)", "10.22", ""],
    ["Ridge (ours)", "10.20", ""],
    ["Elo (ours)", "10.25", ""],
    ["Stack of our three", "10.18", "weights 0.19 / 0.36 / 0.51"],
    ["nfelo, pure model", "10.01", "its history is back-computed with the current model, so this is likely optimistic"],
    ["Stack: ours + nfelo", "10.04", "our models get weight about 0"],
    ["Opening line", "10.02", ""],
    ["Closing line", "9.92", ""],
    ["Stack: ours + nfelo + closing line", "9.95", "closing line 0.58, nfelo 0.72, ours about 0"],
  ], [2.4, 1.5, 3.1]),
  gap(),
  P("Three things come out of this. First, averaging our own three models gains only a few hundredths of a point, because their predictions are correlated at 0.89-0.94: they disagree too little for averaging to help. Second, nfelo is a better single forecast than anything we built, by about 0.2 points, which I attribute to its quarterback adjustment and to the fact that its published history was generated by the current version of the model (so it is not strictly out of sample). Third, and most important, no stack improves on the closing line: when the line is a component, it takes nearly all the weight and our models take none. The same holds for totals, where the opening total (10.47) is in fact slightly better than the closing total (10.53) in this sample, and adding our models to either does not help."),
  P("So the honest answer is: ensembling what we have does not beat the market. The one ensemble that could is one built from forecasts that carry information the market does not yet have, such as injury or weather news between the opening and closing line, and that is a different data collection exercise."),
  ...figure("ensemble_external", 6.3, "Figure 7. Left: margin error of single forecasts and the lines, 2013-2025 (3,562 games with all forecasts). Right: stacking weights when our models, nfelo and both lines are combined."),

  H1("Follow-up: full distributions and the Vegas lines"),
  P("Second question: can the models give a distribution for the margin and the total, and how does it compare with the lines? Yes. The two predicted scores set the centre, and the distribution around them comes either from a bivariate normal with the residual standard deviations (9.6 and 9.4, correlation 0.01), or from the historical score table shifted so that its mean margin and total match the forest. The second keeps the spikes at 3 and 7 points that the normal smooths away. From either, the probability of any outcome is a sum: P(home wins), P(home covers the Vegas spread), P(over the Vegas total)."),
  ...figure("game_distributions", 6.5, "Figure 8. Four 2025 games. Top: margin distribution from the shifted score table (bars) and the bivariate normal (dashed), with the Vegas spread (orange) and the actual margin (green). Bottom: the same for the total."),
  table([
    ["Game (2025)", "Pred. score", "Model margin", "Vegas spread", "P(cover)", "Model total", "Vegas total", "P(over)", "Actual"],
    ["CLE at BAL, wk 2", "BAL 31.3-17.0", "14.3", "12.5", "0.53", "48.3", "46.5", "0.53", "41-17"],
    ["DAL at NYJ, wk 5", "NYJ 23.1-23.1", "0.0", "1.5", "0.48", "46.3", "48.5", "0.41", "22-37"],
    ["DAL at DET, wk 14", "DET 29.5-23.9", "5.6", "3.5", "0.51", "53.4", "55.5", "0.42", "44-30"],
    ["NO at TEN, wk 17", "TEN 19.8-20.3", "-0.5", "-1.5", "0.51", "40.1", "39.5", "0.51", "26-34"],
  ], [1.4, 1.2, 0.8, 0.8, 0.7, 0.8, 0.8, 0.7, 0.7]),
  gap(),
  P("Across all 2,758 games from 2016 to 2025, the model's P(cover) averages 0.50 with a standard deviation of only 0.09, and P(over) averages 0.49 with a standard deviation of 0.08. Only a quarter of games get a cover probability outside 0.40-0.60. The model mostly agrees with Vegas on where the centre is, which is the same finding as the point-accuracy tables."),
  ...figure("cover_over_calibration", 6.0, "Figure 9. Calibration of the model's cover and over probabilities against what happened, 2016-2025. Bin sizes shown."),
  P("The calibration plot is the key result. When the model says a team has a 65% chance of covering the spread, it covers about 52% of the time; when it says 35%, about 48%. The curves are flat. The distributions are internally consistent and calibrated for outcomes the market has not priced (any particular margin, the joint score, the width), but they do not know which side of the Vegas number will hit. Brier scores of 0.257 for cover and 0.255 for over, against 0.25 for a coin flip, say the same thing. This is the expected result for an efficient line, and it is the reason the project's value lies in pricing the whole distribution consistently rather than in picking sides against the market."),

  H1("Week 5 forecasts"),
  P("Model trained on 2000-2025. Predicted scores, implied home-win probability, and the closing line for comparison."),
  table([
    ["Date", "Away", "Home", "Pred. away", "Pred. home", "Margin", "Total", "P(home)", "Spread", "Total line"],
    ["Oct 8", "TB", "DAL", "20.7", "26.1", "5.4", "46.8", "0.64", "8.5", "47.5"],
    ["Oct 11", "PHI", "JAX", "18.5", "26.3", "7.8", "44.8", "0.70", "7.0", "42.5"],
    ["Oct 11", "CIN", "MIA", "25.9", "19.5", "-6.4", "45.4", "0.33", "-7.0", "42.5"],
    ["Oct 11", "LV", "NE", "17.9", "25.5", "7.6", "43.4", "0.70", "3.5", "45.5"],
    ["Oct 11", "MIN", "NO", "22.2", "19.7", "-2.5", "41.9", "0.43", "-1.5", "42.5"],
    ["Oct 11", "IND", "PIT", "20.6", "22.1", "1.5", "42.7", "0.54", "2.5", "44.5"],
    ["Oct 11", "NYG", "WAS", "21.8", "22.1", "0.3", "43.9", "0.51", "3.5", "43.5"],
    ["Oct 11", "CHI", "GB", "25.6", "22.2", "-3.4", "47.8", "0.41", "-3.0", "45.5"],
    ["Oct 11", "HOU", "TEN", "22.5", "17.8", "-4.7", "40.3", "0.37", "-7.5", "38.5"],
    ["Oct 11", "CLE", "NYJ", "21.4", "20.5", "-0.9", "41.9", "0.48", "2.5", "39.5"],
    ["Oct 11", "DEN", "LAC", "21.7", "18.7", "-3.0", "40.4", "0.42", "-3.5", "42.5"],
    ["Oct 11", "DET", "ARI", "26.5", "20.7", "-5.8", "47.2", "0.35", "-4.5", "54.5"],
    ["Oct 11", "SF", "SEA", "22.1", "25.8", "3.7", "47.9", "0.60", "2.5", "46.5"],
    ["Oct 11", "BAL", "ATL", "24.2", "21.8", "-2.4", "46.0", "0.44", "3.5", "43.5"],
    ["Oct 12", "BUF", "LA", "23.7", "25.4", "1.7", "49.1", "0.54", "2.5", "54.5"],
  ], [0.8, 0.7, 0.7, 0.9, 0.9, 0.8, 0.8, 0.8, 0.8, 0.9]),
  gap(),

  H1("Reproduction"),
  P("Everything runs in the nfl conda environment from the repository. The notebook notebooks/rf_two_score_model.ipynb reproduces every table and figure here, including the leakage test, in about six minutes. Scripts: build_features.py, test_leakage.py, model_rf.py, rf_bivariate.py."),

  H1("References"),
  ...[
    "Baker, R. and McHale, I. (2013). Forecasting exact scores in National Football League games. International Journal of Forecasting 29, 122-130.",
    "Boulier, B. and Stekler, H. (2003). Predicting the outcomes of National Football League games. International Journal of Forecasting 19, 257-270.",
    "Glickman, M. and Stern, H. (1998). A state-space model for National Football League scores. Journal of the American Statistical Association 93, 25-35.",
    "Glickman, M. and Stern, H. (2017). Estimating team strength in the NFL. In Handbook of Statistical Methods and Analyses in Sports. CRC Press.",
    "Gray, P. and Gray, S. (1997). Testing market efficiency: evidence from the NFL sports betting market. Journal of Finance 52, 1725-1737.",
    "Harville, D. (1980). Predictions for National Football League games via linear-model methodology. Journal of the American Statistical Association 75, 516-524.",
    "Levitt, S. (2004). Why are gambling markets organised so differently from financial markets? Economic Journal 114, 223-246.",
    "Song, C., Boulier, B. and Stekler, H. (2007). The comparative accuracy of judgmental and model forecasts of American football games. International Journal of Forecasting 23, 405-413.",
    "Stern, H. (1991). On the probability of winning a football game. The American Statistician 45, 179-183.",
    "Yurko, R., Ventura, S. and Horowitz, M. (2019). nflWAR: a reproducible method for offensive player evaluation in football. Journal of Quantitative Analysis in Sports 15, 163-183.",
    "Zuber, R., Gandar, J. and Bowers, B. (1985). Beating the spread: testing the efficiency of the gambling market for National Football League games. Journal of Political Economy 93, 800-806.",
    "FiveThirtyEight. NFL Elo ratings, data and methodology. github.com/fivethirtyeight/data/tree/master/nfl-elo.",
    "nflverse. NFL play-by-play, schedules, rosters and injury data, via nflreadpy. nflverse.nflverse.com.",
  ].map(t => new Paragraph({ spacing: { after: 80 }, indent: { left: 360, hanging: 360 }, children: [new TextRun({ text: t, size: 20 })] })),
];

const doc = new Document({
  styles: { default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: "1F3864", font: "Calibri" }, paragraph: { keepNext: true, spacing: { before: 280, after: 120 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, color: "2E5597", font: "Calibri" }, paragraph: { keepNext: true, spacing: { before: 200, after: 100 } } },
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { size: 40, bold: true, color: "1F3864", font: "Calibri" }, paragraph: { spacing: { after: 120 } } },
    ] },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
  ] },
  sections: [{ properties: { page: { size: { width: PAGE_W, height: 15840 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } }, children }],
});
const OUT = "/Users/kishore/Documents/NYU_FRE/Prediction-Markets-Risk-Framework-Sports-/reports/NFL_two_output_random_forest.docx";
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("wrote", OUT, (b.length / 1024).toFixed(0), "KB"); });
