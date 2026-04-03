# Feature Importance Analysis — March Madness Prediction Model

Training data: 2002–2025 (1449 tournament games, 23 seasons)
Features: 56 differential stats (team1 - team2)
CV accuracy: 0.716

## 4a — Univariate Correlation with Tournament Win

| Rank | Stat | Corr | Direction |
|---|---|---|---|
| 1 | Efficiency Margin (AdjEM) | +0.393 | higher = better for team1 |
| 2 | net_score_rate_diff | +0.391 | higher = better for team1 |
| 3 | Offensive Efficiency | +0.324 | higher = better for team1 |
| 4 | Two-Way Depth | +0.302 | higher = better for team1 |
| 5 | Defensive Efficiency | -0.289 | lower = better for team1 |
| 6 | L10 Opponent Rank | -0.277 | lower = better for team1 |
| 7 | Program Tourney Rate (L5) | +0.252 | higher = better for team1 |
| 8 | Program Final Four Rate (L10) | +0.199 | higher = better for team1 |
| 9 | Effective FG% (Def) | -0.185 | lower = better for team1 |
| 10 | Turnover Rate (Off) | -0.163 | lower = better for team1 |
| 11 | to_exposure_diff | -0.161 | lower = better for team1 |
| 12 | Interior Dominance | +0.159 | higher = better for team1 |
| 13 | Average Height | +0.155 | higher = better for team1 |
| 14 | Effective FG% (Off) | +0.146 | higher = better for team1 |
| 15 | Off Rebound Rate (Off) | +0.145 | higher = better for team1 |
| 16 | ts_efficiency_diff | +0.145 | higher = better for team1 |
| 17 | L10 Off Efficiency | +0.133 | higher = better for team1 |
| 18 | 2-Point % (Off) | +0.133 | higher = better for team1 |
| 19 | L10 Net Efficiency | +0.128 | higher = better for team1 |
| 20 | Block Rate (Def) | +0.123 | higher = better for team1 |
| 21 | avg_rotation_height_diff | +0.101 | higher = better for team1 |
| 22 | 3-Point % (Off) | +0.095 | higher = better for team1 |
| 23 | Depth EUP | +0.093 | higher = better for team1 |
| 24 | L10 Win % | +0.093 | higher = better for team1 |
| 25 | foul_trouble_risk_diff | -0.090 | lower = better for team1 |
| 26 | roster_seniority_diff | -0.083 | lower = better for team1 |
| 27 | Free Throw Rate (Def) | -0.082 | lower = better for team1 |
| 28 | playmaker_quality_diff | +0.080 | higher = better for team1 |
| 29 | L10 Turnover Rate | -0.078 | lower = better for team1 |
| 30 | Steal Rate (Def) | +0.076 | higher = better for team1 |
| 31 | Freshman Min % | +0.061 | higher = better for team1 |
| 32 | rotation_depth_diff | -0.060 | lower = better for team1 |
| 33 | Triple Threat Scorer | +0.060 | higher = better for team1 |
| 34 | ft_clutch_diff | +0.059 | higher = better for team1 |
| 35 | perimeter_depth_diff | +0.058 | higher = better for team1 |
| 36 | Assists/Turnover (Def) | +0.051 | higher = better for team1 |
| 37 | Star EUP | +0.044 | higher = better for team1 |
| 38 | Free Throw Rate (Off) | -0.044 | lower = better for team1 |
| 39 | L10 Def Efficiency | -0.043 | lower = better for team1 |
| 40 | bench_depth_diff | -0.042 | lower = better for team1 |
| 41 | Star Min Concentration | +0.035 | higher = better for team1 |
| 42 | D1 Experience | +0.032 | higher = better for team1 |
| 43 | 3PA Rate (Def) | -0.030 | lower = better for team1 |
| 44 | L10 Eff FG% | +0.030 | higher = better for team1 |
| 45 | Pace (Tempo) | +0.028 | higher = better for team1 |
| 46 | 3PA Rate (Off) | -0.026 | lower = better for team1 |
| 47 | 3-Point Share (Def) | -0.024 | lower = better for team1 |
| 48 | Defensive Momentum | +0.023 | higher = better for team1 |
| 49 | rebounding_balance_diff | +0.020 | higher = better for team1 |
| 50 | Turnover Rate (Def) | +0.020 | higher = better for team1 |
| 51 | 3-Point Share (Off) | -0.013 | lower = better for team1 |
| 52 | Assists/Turnover (Off) | +0.005 | higher = better for team1 |
| 53 | foul_drawing_diff | +0.005 | higher = better for team1 |
| 54 | Off Rebound Rate (Def) | -0.004 | lower = better for team1 |
| 55 | Offensive Momentum | -0.001 | lower = better for team1 |
| 56 | Returning Min % | +0.000 | higher = better for team1 |

### Correlation by Round Stratum

**R1 (32 games/year)** (736 games)

- Efficiency Margin (AdjEM): +0.329
- net_score_rate_diff: +0.326
- Defensive Efficiency: -0.265
- L10 Opponent Rank: -0.250
- Offensive Efficiency: +0.249
- Two-Way Depth: +0.234
- Turnover Rate (Off): -0.205
- to_exposure_diff: -0.195

**R2-R4 (28 games/year)** (644 games)

- Efficiency Margin (AdjEM): +0.421
- net_score_rate_diff: +0.415
- Offensive Efficiency: +0.338
- Two-Way Depth: +0.315
- Defensive Efficiency: -0.254
- Program Tourney Rate (L5): +0.243
- L10 Opponent Rank: -0.218
- L10 Off Efficiency: +0.193

**R5-R6 (Final 4 + Champ)** (69 games)

- net_score_rate_diff: +0.441
- Efficiency Margin (AdjEM): +0.430
- Two-Way Depth: +0.401
- Offensive Efficiency: +0.386
- Program Tourney Rate (L5): +0.350
- Assists/Turnover (Def): -0.333
- Effective FG% (Off): +0.295
- Program Final Four Rate (L10): +0.290

## 4b — Permutation Importance (Accuracy Drop)

| Rank | Stat | Accuracy Drop |
|---|---|---|
| 1 | Efficiency Margin (AdjEM) | +0.0118 |
| 2 | Assists/Turnover (Def) | +0.0092 |
| 3 | net_score_rate_diff | +0.0092 |
| 4 | 3PA Rate (Def) | +0.0067 |
| 5 | L10 Win % | +0.0054 |
| 6 | Offensive Efficiency | +0.0043 |
| 7 | ft_clutch_diff | +0.0041 |
| 8 | Interior Dominance | +0.0040 |
| 9 | Two-Way Depth | +0.0035 |
| 10 | Defensive Momentum | +0.0033 |
| 11 | Defensive Efficiency | +0.0031 |
| 12 | L10 Net Efficiency | +0.0031 |
| 13 | Steal Rate (Def) | +0.0026 |
| 14 | Free Throw Rate (Off) | +0.0024 |
| 15 | bench_depth_diff | +0.0022 |
| 16 | Assists/Turnover (Off) | +0.0022 |
| 17 | Triple Threat Scorer | +0.0021 |
| 18 | foul_trouble_risk_diff | +0.0021 |
| 19 | Star Min Concentration | +0.0019 |
| 20 | 3-Point Share (Def) | +0.0017 |
| 21 | L10 Turnover Rate | +0.0014 |
| 22 | L10 Eff FG% | +0.0014 |
| 23 | Freshman Min % | +0.0011 |
| 24 | Star EUP | +0.0010 |
| 25 | Returning Min % | +0.0010 |
| 26 | Block Rate (Def) | +0.0010 |
| 27 | roster_seniority_diff | +0.0009 |
| 28 | L10 Opponent Rank | +0.0008 |
| 29 | Effective FG% (Def) | +0.0008 |
| 30 | 3-Point % (Off) | +0.0007 |
| 31 | Average Height | +0.0007 |
| 32 | D1 Experience | +0.0007 |
| 33 | to_exposure_diff | +0.0007 |
| 34 | Program Final Four Rate (L10) | +0.0007 |
| 35 | Turnover Rate (Off) | +0.0006 |
| 36 | Offensive Momentum | +0.0006 |
| 37 | Turnover Rate (Def) | +0.0006 |
| 38 | Free Throw Rate (Def) | +0.0005 |
| 39 | playmaker_quality_diff | +0.0005 |
| 40 | L10 Off Efficiency | +0.0004 |
| 41 | perimeter_depth_diff | +0.0004 |
| 42 | L10 Def Efficiency | +0.0003 |
| 43 | 3PA Rate (Off) | +0.0003 |
| 44 | ts_efficiency_diff | +0.0003 |
| 45 | Depth EUP | +0.0002 |
| 46 | avg_rotation_height_diff | +0.0002 |
| 47 | Off Rebound Rate (Off) | +0.0002 |
| 48 | Effective FG% (Off) | +0.0001 |
| 49 | 3-Point Share (Off) | +0.0000 |
| 50 | Off Rebound Rate (Def) | +0.0000 |
| 51 | 2-Point % (Off) | +0.0000 |
| 52 | rebounding_balance_diff | +0.0000 |
| 53 | foul_drawing_diff | +0.0000 |
| 54 | rotation_depth_diff | +0.0000 |
| 55 | Pace (Tempo) | -0.0000 |
| 56 | Program Tourney Rate (L5) | -0.0006 |

## 4c — Standardized Logistic Regression Coefficients

_(1 std dev increase in feature → coefficient change in log-odds of team1 winning)_

| Rank | Stat | Coefficient | Favors |
|---|---|---|---|
| 1 | Turnover Rate (Off) | -0.402 | team2 |
| 2 | 3PA Rate (Def) | +0.383 | team1 |
| 3 | 3-Point Share (Def) | -0.375 | team2 |
| 4 | net_score_rate_diff | +0.373 | team1 |
| 5 | Defensive Efficiency | -0.369 | team2 |
| 6 | L10 Turnover Rate | +0.351 | team1 |
| 7 | Efficiency Margin (AdjEM) | +0.321 | team1 |
| 8 | ts_efficiency_diff | +0.263 | team1 |
| 9 | L10 Eff FG% | -0.222 | team2 |
| 10 | roster_seniority_diff | -0.205 | team2 |
| 11 | L10 Opponent Rank | -0.196 | team2 |
| 12 | Assists/Turnover (Off) | +0.195 | team1 |
| 13 | L10 Win % | +0.183 | team1 |
| 14 | Offensive Efficiency | +0.176 | team1 |
| 15 | Interior Dominance | +0.176 | team1 |
| 16 | Off Rebound Rate (Def) | +0.175 | team1 |
| 17 | D1 Experience | +0.171 | team1 |
| 18 | Freshman Min % | -0.168 | team2 |
| 19 | bench_depth_diff | -0.164 | team2 |
| 20 | Effective FG% (Off) | +0.163 | team1 |
| 21 | 2-Point % (Off) | -0.163 | team2 |
| 22 | Program Final Four Rate (L10) | +0.159 | team1 |
| 23 | 3PA Rate (Off) | -0.156 | team2 |
| 24 | L10 Off Efficiency | +0.154 | team1 |
| 25 | Assists/Turnover (Def) | -0.142 | team2 |
| 26 | Turnover Rate (Def) | -0.137 | team2 |
| 27 | Two-Way Depth | +0.128 | team1 |
| 28 | Defensive Momentum | +0.125 | team1 |
| 29 | Returning Min % | -0.123 | team2 |
| 30 | 3-Point % (Off) | -0.117 | team2 |
| 31 | Block Rate (Def) | -0.116 | team2 |
| 32 | Free Throw Rate (Off) | -0.107 | team2 |
| 33 | Depth EUP | -0.103 | team2 |
| 34 | Steal Rate (Def) | +0.093 | team1 |
| 35 | Offensive Momentum | -0.085 | team2 |
| 36 | 3-Point Share (Off) | +0.083 | team1 |
| 37 | L10 Net Efficiency | +0.078 | team1 |
| 38 | Free Throw Rate (Def) | -0.063 | team2 |
| 39 | Triple Threat Scorer | -0.058 | team2 |
| 40 | Star EUP | -0.053 | team2 |
| 41 | L10 Def Efficiency | +0.049 | team1 |
| 42 | Effective FG% (Def) | -0.047 | team2 |
| 43 | foul_drawing_diff | -0.047 | team2 |
| 44 | Star Min Concentration | -0.044 | team2 |
| 45 | playmaker_quality_diff | -0.043 | team2 |
| 46 | Off Rebound Rate (Off) | +0.042 | team1 |
| 47 | ft_clutch_diff | -0.040 | team2 |
| 48 | perimeter_depth_diff | +0.038 | team1 |
| 49 | Pace (Tempo) | +0.036 | team1 |
| 50 | to_exposure_diff | -0.022 | team2 |
| 51 | avg_rotation_height_diff | -0.014 | team2 |
| 52 | foul_trouble_risk_diff | -0.014 | team2 |
| 53 | Program Tourney Rate (L5) | +0.013 | team1 |
| 54 | rebounding_balance_diff | -0.012 | team2 |
| 55 | Average Height | -0.006 | team2 |
| 56 | rotation_depth_diff | +0.005 | team1 |

## 4d — Permutation Importance by Round Stratum

Top 8 features per stratum. Shows which stats matter more in early vs late rounds.

**R1 (32 games/year)** (736 games)

- Efficiency Margin (AdjEM): +0.0247
- net_score_rate_diff: +0.0164
- Assists/Turnover (Def): +0.0112
- 3PA Rate (Def): +0.0073
- Defensive Efficiency: +0.0071
- Offensive Efficiency: +0.0069
- L10 Win %: +0.0069
- ft_clutch_diff: +0.0060

**R2-R4 (28 games/year)** (644 games)

- Assists/Turnover (Def): +0.0072
- net_score_rate_diff: +0.0064
- Free Throw Rate (Off): +0.0052
- 3PA Rate (Def): +0.0052
- Interior Dominance: +0.0050
- Offensive Efficiency: +0.0047
- Assists/Turnover (Off): +0.0047
- L10 Net Efficiency: +0.0041

**R5-R6 (Final 4 + Champ)** (69 games)

- Block Rate (Def): +0.0087
- Returning Min %: +0.0087
- Freshman Min %: +0.0058
- Offensive Momentum: +0.0036
- Interior Dominance: +0.0036
- L10 Opponent Rank: +0.0036
- 3PA Rate (Def): +0.0029
- ft_clutch_diff: +0.0029

## 4e — Seed Ablation

Full model (no AdjEM) vs same model with seed_diff removed.
Quantifies how much seeds add once all efficiency data is present.

| Metric | With Seed | Without Seed | Delta |
|---|---|---|---|
| CV Accuracy  | 0.7164 | 0.7164 | +0.0000 |
| Brier Score  | 0.1935 | 0.1935 | +0.0000 |
| Log Loss     | 0.5832 | 0.5832 | +0.0000 |

_(Brier/Log loss: lower = better. Positive delta = seed adds value.)_
