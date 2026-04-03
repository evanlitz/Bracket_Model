"""Precompute feature importance by tournament round and save to config/feature_importance.json.

Runs leave-year-out CV, then for each round + overall computes:
  - Permutation importance (accuracy drop when feature is shuffled)
  - Univariate correlation with win/loss
  - Feature coverage (fraction of non-NaN values)

Run once from project root:
    python scripts/precompute_feature_importance.py

Output: config/feature_importance.json (~60 features × 7 rounds)
Runtime: ~5-10 minutes
"""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.features import build_matchup_df, DIFF_FEATURES
from src.kenpom import load_kenpom, YEARS
from src.names import normalize_name
from src.model import train, leave_year_out_cv

ROUND_NAMES = {
    1: 'R64 (First Round)',
    2: 'R32 (Second Round)',
    3: 'S16 (Sweet 16)',
    4: 'E8 (Elite Eight)',
    5: 'F4 (Final Four)',
    6: 'NCG (Championship)',
}

PRETTY = {
    'AdjEM_diff':                   'Efficiency Margin',
    'net_score_rate_diff':          'Net Score Rate (EM×Tempo/48)',
    'AdjOE_diff':                   'Offensive Efficiency',
    'AdjDE_diff':                   'Defensive Efficiency',
    'AdjTempo_diff':                'Pace (Tempo)',
    'efg_pct_off_diff':             'eFG% Off',
    'efg_pct_def_diff':             'eFG% Def',
    'to_pct_off_diff':              'Turnover Rate Off',
    'to_pct_def_diff':              'Turnover Rate Def',
    'or_pct_off_diff':              'Off Rebound Rate Off',
    'or_pct_def_diff':              'Off Rebound Rate Def',
    'ftr_off_diff':                 'Free Throw Rate Off',
    'ftr_def_diff':                 'Free Throw Rate Def',
    'fg3a_rate_off_diff':           '3PA Rate Off',
    'fg3a_rate_def_diff':           '3PA Rate Def',
    'fg2_pct_off_diff':             '2-Pt % Off',
    'fg3_pct_off_diff':             '3-Pt % Off',
    'blk_pct_def_diff':             'Block Rate',
    'stl_rate_def_diff':            'Steal Rate',
    'd1_exp_diff':                  'D1 Experience',
    'avg_height_diff':              'Avg Height',
    'apl_off_diff':                 'Ast/TO Off',
    'apl_def_diff':                 'Ast/TO Def',
    'pd3_off_diff':                 '3-Pt Share Off',
    'pd3_def_diff':                 '3-Pt Share Def',
    'l10_off_eff_diff':             'L10 Off Efficiency',
    'l10_def_eff_diff':             'L10 Def Efficiency',
    'l10_net_eff_diff':             'L10 Net Efficiency',
    'l10_win_pct_diff':             'L10 Win %',
    'l10_efg_diff':                 'L10 eFG%',
    'l10_to_pct_diff':              'L10 Turnover Rate',
    'l10_opp_rank_diff':            'L10 Opponent Rank',
    'momentum_off_diff':            'Off Momentum',
    'momentum_def_diff':            'Def Momentum',
    'program_tourney_rate_l5_diff': 'Program Tourney Rate (L5)',
    'program_f4_rate_l10_diff':     'Program F4 Rate (L10)',
    'fr_min_pct_diff':              'Freshman Min %',
    'returning_min_pct_diff':       'Returning Min %',
    'star_min_conc_diff':           'Star Min Concentration',
    'star_eup_diff':                'Star EUP',
    'depth_eup_diff':               'Depth EUP',
    'two_way_depth_diff':           'Two-Way Depth',
    'interior_dom_diff':            'Interior Dominance',
    'triple_threat_diff':           'Triple Threat',
    'roster_seniority_diff':        'Roster Seniority',
    'ft_clutch_diff':               'FT Clutch',
    'playmaker_quality_diff':       'Playmaker Quality',
    'perimeter_depth_diff':         'Perimeter Depth',
    'to_exposure_diff':             'TO Exposure',
    'bench_depth_diff':             'Bench Depth',
    'rebounding_balance_diff':      'Rebounding Balance',
    'foul_drawing_diff':            'Foul Drawing',
    'foul_trouble_risk_diff':       'Foul Trouble Risk',
    'avg_rotation_height_diff':     'Avg Rotation Height',
    'ts_efficiency_diff':           'TS Efficiency',
    'rotation_depth_diff':          'Rotation Depth',
}


def label(col: str) -> str:
    return PRETTY.get(col, col.replace('_diff', ''))


def _build_seed_lkp() -> dict:
    lkp = {}
    for y in YEARS:
        if y == 2020:
            continue
        try:
            kp = load_kenpom(y)
            for _, row in kp.iterrows():
                if pd.notna(row['seed']):
                    lkp[(normalize_name(str(row['TeamName'])), y)] = float(row['seed'])
        except Exception:
            pass
    return lkp


def _corr(sub: pd.DataFrame, feat_cols: list) -> list:
    out = {}
    for col in feat_cols:
        valid = sub[[col, 'label']].dropna()
        if len(valid) >= 10:
            out[col] = float(valid[col].corr(valid['label']))
    return sorted(
        [{'feature': c, 'label': label(c), 'value': v} for c, v in out.items()],
        key=lambda x: abs(x['value']),
        reverse=True,
    )


def _perm(model, sub: pd.DataFrame, feat_cols: list, n_repeats: int) -> list:
    result = permutation_importance(
        model, sub[feat_cols], sub['label'],
        n_repeats=n_repeats, random_state=42, scoring='accuracy',
    )
    items = [
        {'feature': c, 'label': label(c), 'value': float(v)}
        for c, v in zip(feat_cols, result.importances_mean)
    ]
    return sorted(items, key=lambda x: abs(x['value']), reverse=True)


def _coverage(sub: pd.DataFrame, feat_cols: list) -> list:
    cov = sub[feat_cols].notna().mean()
    return sorted(
        [{'feature': c, 'label': label(c), 'value': float(cov[c])} for c in feat_cols],
        key=lambda x: x['value'],
    )


def _seed_acc(cv_sub: pd.DataFrame) -> float | None:
    s = cv_sub[cv_sub['seed_diff'].notna()]
    if s.empty:
        return None
    return float(((s['seed_diff'] < 0) == s['label'].astype(bool)).mean())


def make_round_data(sub: pd.DataFrame, cv_sub: pd.DataFrame,
                    model, feat_cols: list) -> dict:
    n = len(sub)
    cv_acc = float((cv_sub['pred'] == cv_sub['label']).mean()) if len(cv_sub) else None
    seed_a = _seed_acc(cv_sub)

    if n >= 40:
        n_rep = 30 if n >= 150 else 15
        perm = _perm(model, sub, feat_cols, n_rep)
    else:
        perm = None

    return {
        'n_games':  n,
        'cv_acc':   cv_acc,
        'seed_acc': seed_a,
        'permutation': perm,
        'correlation': _corr(sub, feat_cols),
        'coverage':    _coverage(sub, feat_cols),
    }


def main():
    print('Building matchup data...')
    df = build_matchup_df()
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
    print(f'  {len(df)} games | {df["year"].nunique()} seasons | {len(feat_cols)} features')

    print('Building seed lookup...')
    seed_lkp = _build_seed_lkp()
    df['seed1'] = df.apply(lambda r: seed_lkp.get((r['team1'], r['year'])), axis=1)
    df['seed2'] = df.apply(lambda r: seed_lkp.get((r['team2'], r['year'])), axis=1)
    df['seed_diff'] = df['seed1'] - df['seed2']

    print('Training model on full dataset...')
    model = train(df)

    print('Running leave-year-out CV...')
    cv_df = leave_year_out_cv(df)
    # seed_diff present in cv_df via df slice
    cv_df['seed_diff'] = df.loc[cv_df.index, 'seed_diff'].values

    rounds = {}

    print('Computing per-round importance...')
    for rnd in sorted(df['round'].unique()):
        name = ROUND_NAMES.get(rnd, f'Round {rnd}')
        print(f'  {name}...')
        sub    = df[df['round'] == rnd]
        cv_sub = cv_df[cv_df['round'] == rnd]
        rounds[str(rnd)] = {'name': name, **make_round_data(sub, cv_sub, model, feat_cols)}

    print('Computing overall importance...')
    rounds['overall'] = {'name': 'Overall', **make_round_data(df, cv_df, model, feat_cols)}

    output = {
        'generated_at': str(date.today()),
        'n_games':      len(df),
        'n_features':   len(feat_cols),
        'feature_labels': {c: label(c) for c in feat_cols},
        'rounds':       rounds,
    }

    out_path = Path(__file__).parent.parent / 'config' / 'feature_importance.json'
    out_path.write_text(json.dumps(output, indent=2))
    print(f'\nSaved -> {out_path}')
    print(f'Rounds: {list(rounds.keys())}')


if __name__ == '__main__':
    main()
