"""Feature importance broken down by tournament round.

For each round (R64 → NCG) and overall:
  - Permutation importance (accuracy drop when feature is shuffled)
  - Univariate correlation with win
  - Feature coverage (flags NaN-heavy features from early years)

Note: F4 (46 games) and NCG (23 games) have small sample sizes — treat
those results as directional signals, not statistically robust rankings.

Run from project root:
    python scripts/feature_importance_by_round.py
"""

import sys
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
    1: 'R64  (First Round)',
    2: 'R32  (Second Round)',
    3: 'S16  (Sweet 16)',
    4: 'E8   (Elite Eight)',
    5: 'F4   (Final Four)',
    6: 'NCG  (Championship)',
}

PRETTY = {
    'AdjEM_diff':                   'Efficiency Margin',
    'net_score_rate_diff':          'Net Score Rate (EM×Tempo/48)',
    'AdjOE_diff':                   'Offensive Efficiency',
    'AdjDE_diff':                   'Defensive Efficiency',
    'AdjTempo_diff':                'Pace (Tempo)',
    'seed_diff':                    'Seed',
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


def p(col: str) -> str:
    return PRETTY.get(col, col.replace('_diff', ''))


def hbar(val: float, width: int = 25, scale: float = 1.0) -> str:
    n = max(0, int(abs(val) * scale * width))
    return '|' + '#' * min(n, width)


def _corr(sub: pd.DataFrame, feat_cols: list) -> pd.Series:
    out = {}
    for col in feat_cols:
        valid = sub[[col, 'label']].dropna()
        if len(valid) >= 10:
            out[col] = valid[col].corr(valid['label'])
    return pd.Series(out).sort_values(key=abs, ascending=False)


def _perm(model, sub: pd.DataFrame, feat_cols: list, n_repeats: int) -> pd.Series:
    result = permutation_importance(
        model, sub[feat_cols], sub['label'],
        n_repeats=n_repeats, random_state=42, scoring='accuracy',
    )
    return pd.Series(result.importances_mean, index=feat_cols).sort_values(ascending=False)


def print_section(name: str, n_games: int, cv_acc: float, seed_acc: float,
                  perm: pd.Series | None, corr: pd.Series,
                  coverage: pd.Series, feat_cols: list, top_n: int = 12):

    print(f'\n{"=" * 65}')
    print(f'  {name}')
    print(f'  {n_games} games  |  CV acc: {cv_acc:.1%}  |  Seed baseline: {seed_acc:.1%}  |  Delta: {cv_acc - seed_acc:+.1%}')
    print(f'{"=" * 65}')

    # Coverage warnings
    low = coverage[coverage < 0.80].sort_values()
    if not low.empty:
        print(f'\n  [Feature coverage <80% — NaN from early years]:')
        for col, pct in low.items():
            print(f'    {p(col):<32} {pct:.0%} coverage')

    # Permutation importance
    if perm is not None:
        print(f'\n  Permutation Importance (accuracy drop when shuffled):')
        print(f'  {"Feature":<33} {"Drop":>7}  Chart')
        print(f'  {"-"*33} {"-"*7}  -----')
        for col, val in perm.head(top_n).items():
            cov_flag = ' *' if coverage.get(col, 1.0) < 0.80 else ''
            print(f'  {p(col):<33} {val:>+.4f}  {hbar(val, 25, scale=200)}{cov_flag}')
        neg = perm[perm < -0.002]
        if not neg.empty:
            print(f'\n  Negative importance (shuffling helps — possible noise):')
            for col, val in neg.items():
                print(f'    {p(col):<33} {val:>+.4f}')
    else:
        print(f'\n  [Permutation importance skipped — too few games for reliable results]')

    # Correlation
    print(f'\n  Univariate Correlation with Win:')
    print(f'  {"Feature":<33} {"Corr":>6}  Chart')
    print(f'  {"-"*33} {"-"*6}  -----')
    for col, val in corr.head(top_n).items():
        cov_flag = ' *' if coverage.get(col, 1.0) < 0.80 else '  '
        print(f'  {p(col):<33} {val:>+.3f}{cov_flag}  {hbar(val, 25, scale=4)}')


def _build_seed_lkp() -> dict:
    """Return {(team, year): seed} from KenPom data for all historical years."""
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


def main():
    print('Building matchup data...')
    df = build_matchup_df()
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
    print(f'  {len(df)} games | {df["year"].nunique()} seasons | {len(feat_cols)} features')

    print('Building seed lookup...')
    seed_lkp = _build_seed_lkp()
    # Add seed_diff to df for baseline calculation
    df['seed1'] = df.apply(lambda r: seed_lkp.get((r['team1'], r['year'])), axis=1)
    df['seed2'] = df.apply(lambda r: seed_lkp.get((r['team2'], r['year'])), axis=1)
    df['seed_diff'] = df['seed1'] - df['seed2']

    print('Training model on full dataset...')
    model = train(df)

    print('Running leave-year-out CV...')
    cv_df = leave_year_out_cv(df)  # seed_diff already present via df slice

    def seed_acc(sub_cv):
        s = sub_cv[sub_cv['seed_diff'].notna()]
        if s.empty:
            return float('nan')
        return ((s['seed_diff'] < 0) == s['label'].astype(bool)).mean()

    rounds = sorted(df['round'].unique())

    # ── Per round ──────────────────────────────────────────────────────────────
    for rnd in rounds:
        sub    = df[df['round'] == rnd].copy()
        cv_sub = cv_df[cv_df['round'] == rnd]
        name   = ROUND_NAMES.get(rnd, f'Round {rnd}')
        n      = len(sub)

        cv_acc   = (cv_sub['pred'] == cv_sub['label']).mean()
        sb_acc   = seed_acc(cv_sub)
        coverage = sub[feat_cols].notna().mean()
        corr     = _corr(sub, feat_cols)

        # Permutation importance: skip for very small samples (F4/NCG noisy)
        if n >= 40:
            n_rep = 30 if n >= 150 else 15
            perm = _perm(model, sub, feat_cols, n_rep)
            note = ''
        else:
            perm = None
            note = f'  (n={n} — too few for permutation importance)'

        print_section(name, n, cv_acc, sb_acc, perm, corr, coverage, feat_cols)
        if note:
            print(note)

    # ── Overall ───────────────────────────────────────────────────────────────
    cv_acc_all = (cv_df['pred'] == cv_df['label']).mean()
    sb_acc_all = seed_acc(cv_df)
    coverage   = df[feat_cols].notna().mean()
    corr_all   = _corr(df, feat_cols)
    perm_all   = _perm(model, df, feat_cols, n_repeats=30)

    print_section('OVERALL', len(df), cv_acc_all, sb_acc_all,
                  perm_all, corr_all, coverage, feat_cols, top_n=15)

    print('\n  * = feature has <80% coverage due to data starting mid-history')
    print(f'\n  Model: HistGradientBoostingClassifier (NaN-native — low coverage features')
    print(f'  still contribute where data exists; they are not excluded from training.)')


if __name__ == '__main__':
    main()
