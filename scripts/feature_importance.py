"""Multi-angle feature importance analysis for the March Madness model.

Produces analysis/feature_importance.md with four analyses:
  4a  Univariate correlation (overall + by round stratum)
  4b  Permutation importance from trained model
  4c  Standardized logistic regression coefficients
  4d  Round-stratified permutation importance

Run from project root:
    python scripts/feature_importance.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.features import build_matchup_df, DIFF_FEATURES
from src.model import leave_year_out_cv, train, augment, load

OUT_PATH = Path(__file__).parent.parent / 'analysis' / 'feature_importance.md'

PRETTY_NAMES = {
    'AdjEM_diff':          'Efficiency Margin (AdjEM)',
    'AdjOE_diff':          'Offensive Efficiency',
    'AdjDE_diff':          'Defensive Efficiency',
    'AdjTempo_diff':       'Pace (Tempo)',
    'seed_diff':           'Tournament Seed',
    'apl_off_diff':        'Assists/Turnover (Off)',
    'apl_def_diff':        'Assists/Turnover (Def)',
    'pd3_off_diff':        '3-Point Share (Off)',
    'pd3_def_diff':        '3-Point Share (Def)',
    'fr_min_pct_diff':     'Freshman Min %',
    'returning_min_pct_diff': 'Returning Min %',
    'star_min_conc_diff':  'Star Min Concentration',
    'star_eup_diff':       'Star EUP',
    'depth_eup_diff':      'Depth EUP',
    'two_way_depth_diff':  'Two-Way Depth',
    'interior_dom_diff':   'Interior Dominance',
    'triple_threat_diff':  'Triple Threat Scorer',
    'program_tourney_rate_l5_diff': 'Program Tourney Rate (L5)',
    'program_f4_rate_l10_diff':     'Program Final Four Rate (L10)',
    'efg_pct_off_diff':    'Effective FG% (Off)',
    'efg_pct_def_diff':    'Effective FG% (Def)',
    'to_pct_off_diff':     'Turnover Rate (Off)',
    'to_pct_def_diff':     'Turnover Rate (Def)',
    'or_pct_off_diff':     'Off Rebound Rate (Off)',
    'or_pct_def_diff':     'Off Rebound Rate (Def)',
    'ftr_off_diff':        'Free Throw Rate (Off)',
    'ftr_def_diff':        'Free Throw Rate (Def)',
    'fg3a_rate_off_diff':  '3PA Rate (Off)',
    'fg3a_rate_def_diff':  '3PA Rate (Def)',
    'fg2_pct_off_diff':    '2-Point % (Off)',
    'fg3_pct_off_diff':    '3-Point % (Off)',
    'blk_pct_def_diff':    'Block Rate (Def)',
    'stl_rate_def_diff':   'Steal Rate (Def)',
    'd1_exp_diff':         'D1 Experience',
    'avg_height_diff':     'Average Height',
    'l10_off_eff_diff':    'L10 Off Efficiency',
    'l10_def_eff_diff':    'L10 Def Efficiency',
    'l10_net_eff_diff':    'L10 Net Efficiency',
    'l10_win_pct_diff':    'L10 Win %',
    'l10_efg_diff':        'L10 Eff FG%',
    'l10_to_pct_diff':     'L10 Turnover Rate',
    'l10_opp_rank_diff':   'L10 Opponent Rank',
    'momentum_off_diff':   'Offensive Momentum',
    'momentum_def_diff':   'Defensive Momentum',
}


def pretty(col: str) -> str:
    return PRETTY_NAMES.get(col, col)


def bar(val: float, scale: float = 1.0, width: int = 25) -> str:
    n = max(0, int(abs(val) * scale * width))
    return '#' * min(n, width)


# ── 4a: Univariate point-biserial correlation ─────────────────────────────────

def univariate_corr(df: pd.DataFrame, feat_cols: list[str]) -> pd.Series:
    corrs = {}
    for col in feat_cols:
        valid = df[[col, 'label']].dropna()
        if len(valid) > 10:
            corrs[col] = valid[col].corr(valid['label'])
    return pd.Series(corrs).sort_values(key=abs, ascending=False)


# ── 4c: Logistic regression coefficients ─────────────────────────────────────

def logistic_coefficients(df: pd.DataFrame, feat_cols: list[str]) -> pd.Series:
    aug = augment(df)
    valid_cols = [c for c in feat_cols if aug[c].notna().sum() > 100]
    X = aug[valid_cols].fillna(aug[valid_cols].median())
    y = aug['label']
    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=1000, random_state=42),
    )
    pipe.fit(X, y)
    coefs = pipe.named_steps['logisticregression'].coef_[0]
    return pd.Series(coefs, index=valid_cols).sort_values(key=abs, ascending=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('Building matchup data...')
    df = build_matchup_df()
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]

    print('Running leave-year-out CV (full feature set)...')
    cv_df = leave_year_out_cv(df)

    print('Running leave-year-out CV (no seed)...')
    cv_no_seed = leave_year_out_cv(df.drop(columns=['seed_diff'], errors='ignore'))

    print('Training final model...')
    model = train(df)

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        '# Feature Importance Analysis — March Madness Prediction Model',
        '',
        f'Training data: 2002–2025 ({len(df)} tournament games, {df["year"].nunique()} seasons)',
        f'Features: {len(feat_cols)} differential stats (team1 - team2)',
        f'CV accuracy: {(cv_df["pred"] == cv_df["label"]).mean():.3f}'
        + (f'  |  Seed baseline: {((cv_df["seed_diff"] < 0) == cv_df["label"].astype(bool)).mean():.3f}'
           if "seed_diff" in cv_df.columns else ''),
        '',
    ]

    # ── 4a: Univariate correlation ─────────────────────────────────────────────
    lines += ['## 4a — Univariate Correlation with Tournament Win', '']
    corrs = univariate_corr(df, feat_cols)
    lines.append('| Rank | Stat | Corr | Direction |')
    lines.append('|---|---|---|---|')
    for i, (col, val) in enumerate(corrs.items(), 1):
        direction = 'higher = better for team1' if val > 0 else 'lower = better for team1'
        lines.append(f'| {i} | {pretty(col)} | {val:+.3f} | {direction} |')
    lines.append('')

    # By round stratum
    lines += ['### Correlation by Round Stratum', '']
    strata = {
        'R1 (32 games/year)':     cv_df[cv_df['round'] == 1],
        'R2-R4 (28 games/year)':  cv_df[cv_df['round'].between(2, 4)],
        'R5-R6 (Final 4 + Champ)': cv_df[cv_df['round'].isin([5, 6])],
    }
    for stratum_name, sub_cv in strata.items():
        sub_df = df[df['year'].isin(sub_cv['year'].unique()) &
                    df['round'].isin(sub_cv['round'].unique())]
        if sub_df.empty:
            continue
        sub_corrs = univariate_corr(sub_df, feat_cols).head(8)
        lines.append(f'**{stratum_name}** ({len(sub_df)} games)')
        lines.append('')
        for col, val in sub_corrs.items():
            lines.append(f'- {pretty(col)}: {val:+.3f}')
        lines.append('')

    # ── 4b: Permutation importance ────────────────────────────────────────────
    lines += ['## 4b — Permutation Importance (Accuracy Drop)', '']
    result = permutation_importance(
        model, df[feat_cols], df['label'],
        n_repeats=30, random_state=42, scoring='accuracy',
    )
    perm = pd.Series(result.importances_mean, index=feat_cols).sort_values(ascending=False)
    lines.append('| Rank | Stat | Accuracy Drop |')
    lines.append('|---|---|---|')
    for i, (col, val) in enumerate(perm.items(), 1):
        lines.append(f'| {i} | {pretty(col)} | {val:+.4f} |')
    lines.append('')

    # ── 4c: Logistic regression ───────────────────────────────────────────────
    lines += ['## 4c — Standardized Logistic Regression Coefficients', '']
    lines += ['_(1 std dev increase in feature → coefficient change in log-odds of team1 winning)_', '']
    coefs = logistic_coefficients(df, feat_cols)
    lines.append('| Rank | Stat | Coefficient | Favors |')
    lines.append('|---|---|---|---|')
    for i, (col, val) in enumerate(coefs.items(), 1):
        favors = 'team1' if val > 0 else 'team2'
        lines.append(f'| {i} | {pretty(col)} | {val:+.3f} | {favors} |')
    lines.append('')

    # ── 4d: Round-stratified permutation importance ───────────────────────────
    lines += ['## 4d — Permutation Importance by Round Stratum', '']
    lines += ['Top 8 features per stratum. Shows which stats matter more in early vs late rounds.', '']
    for stratum_name, sub_cv in strata.items():
        sub_df = df[df['round'].isin(sub_cv['round'].unique())].copy()
        if len(sub_df) < 30:
            continue
        result_s = permutation_importance(
            model, sub_df[feat_cols], sub_df['label'],
            n_repeats=20, random_state=42, scoring='accuracy',
        )
        perm_s = pd.Series(result_s.importances_mean, index=feat_cols).sort_values(ascending=False)
        lines.append(f'**{stratum_name}** ({len(sub_df)} games)')
        lines.append('')
        for col, val in perm_s.head(8).items():
            lines.append(f'- {pretty(col)}: {val:+.4f}')
        lines.append('')

    # ── 4e: Seed ablation ─────────────────────────────────────────────────────
    lines += ['## 4e — Seed Ablation', '']
    lines += [
        'Full model (no AdjEM) vs same model with seed_diff removed.',
        'Quantifies how much seeds add once all efficiency data is present.',
        '',
    ]

    def _cv_metrics(cv):
        acc   = (cv['pred'] == cv['label']).mean()
        brier = brier_score_loss(cv['label'], cv['prob'])
        ll    = log_loss(cv['label'], cv['prob'])
        return acc, brier, ll

    acc_full,    brier_full,    ll_full    = _cv_metrics(cv_df)
    acc_no_seed, brier_no_seed, ll_no_seed = _cv_metrics(cv_no_seed)

    lines += [
        '| Metric | With Seed | Without Seed | Delta |',
        '|---|---|---|---|',
        f'| CV Accuracy  | {acc_full:.4f} | {acc_no_seed:.4f} | {acc_full - acc_no_seed:+.4f} |',
        f'| Brier Score  | {brier_full:.4f} | {brier_no_seed:.4f} | {brier_full - brier_no_seed:+.4f} |',
        f'| Log Loss     | {ll_full:.4f} | {ll_no_seed:.4f} | {ll_full - ll_no_seed:+.4f} |',
        '',
        '_(Brier/Log loss: lower = better. Positive delta = seed adds value.)_',
        '',
    ]

    # ── Write output ──────────────────────────────────────────────────────────
    OUT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\nWrote {OUT_PATH}')

    # Also print top-10 correlation summary to terminal
    print('\nTop 10 by univariate correlation:')
    for i, (col, val) in enumerate(corrs.head(10).items(), 1):
        print(f'  {i:2d}. {pretty(col):<30s} {val:+.3f}  {bar(val, 5)}')


if __name__ == '__main__':
    main()
