"""Precompute rich analytics data for the Feature Importance / Analytics tab.

Separate from precompute_feature_importance.py — this script focuses on:
  1. Year-by-year model accuracy, Brier score, upset rate (2002–2025)
  2. Model calibration curve (predicted prob bucket → actual win rate)
  3. Year-by-year feature correlation for tracked top features
  4. Era comparison (early / mid / recent) feature correlation
  5. Upset analysis — by seed matchup + feature correlations on upset games
  6. Feature redundancy matrix — pairwise correlations between top-20 features

Run once from project root:
    python scripts/precompute_analytics.py

Output: config/analytics.json
Runtime: ~5–10 minutes (one LYO CV pass, then fast analytics)
"""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features import build_matchup_df, DIFF_FEATURES
from src.kenpom import load_kenpom, YEARS
from src.names import normalize_name
from src.model import leave_year_out_cv

DATA_DIR   = Path(__file__).parent.parent / 'data'
CONFIG_DIR = Path(__file__).parent.parent / 'config'

# Feature display labels (shared with precompute_feature_importance.py)
PRETTY = {
    'AdjEM_diff':                   'Efficiency Margin',
    'net_score_rate_diff':          'Net Score Rate',
    'AdjOE_diff':                   'Offensive Efficiency',
    'AdjDE_diff':                   'Defensive Efficiency',
    'AdjTempo_diff':                'Pace (Tempo)',
    'efg_pct_off_diff':             'eFG% Off',
    'efg_pct_def_diff':             'eFG% Def',
    'to_pct_off_diff':              'Turnover Rate Off',
    'to_pct_def_diff':              'Turnover Rate Def',
    'or_pct_off_diff':              'Off Rebound Rate',
    'or_pct_def_diff':              'Def Rebound Rate',
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
    'coach_career_tourney_apps_diff': 'Coach Tourney Apps',
    'coach_career_ff_diff':           'Coach Final Fours',
    'conf_tourney_win_pct_diff':      'Conf Tourney Win%',
}

ERAS = [
    ('2002–2010', 2002, 2010),
    ('2011–2017', 2011, 2017),
    ('2018–2025', 2018, 2025),
]

ROUND_NAMES = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}


def lbl(col: str) -> str:
    return PRETTY.get(col, col.replace('_diff', ''))


# ── Seed lookup ────────────────────────────────────────────────────────────────

def build_seed_lkp() -> dict:
    lkp = {}
    for y in YEARS:
        if y == 2020:
            continue
        try:
            kp = load_kenpom(y)
            for _, row in kp.iterrows():
                if pd.notna(row.get('seed')):
                    lkp[(normalize_name(str(row['TeamName'])), y)] = float(row['seed'])
        except Exception:
            pass
    return lkp


# ── 1. Year-by-year accuracy ───────────────────────────────────────────────────

def yearly_accuracy(df: pd.DataFrame, cv_df: pd.DataFrame) -> list:
    records = []
    for year in sorted(df['year'].unique()):
        sub = cv_df[cv_df['year'] == year]
        if sub.empty:
            continue

        acc   = float((sub['pred'] == sub['label']).mean())
        n     = int(len(sub))
        brier = float(brier_score_loss(sub['label'], sub['prob']))
        ll    = float(log_loss(sub['label'], sub['prob']))

        # Upset rate: actual winner had worse seed
        if 'seed_diff' in sub.columns:
            seeded = sub[sub['seed_diff'].notna() & (sub['seed_diff'] != 0)]
            if not seeded.empty:
                # upset = worse-seeded team (higher seed number) won
                actual_upset = (
                    ((seeded['seed_diff'] < 0) & (seeded['label'] == 0)) |
                    ((seeded['seed_diff'] > 0) & (seeded['label'] == 1))
                )
                upset_rate = float(actual_upset.mean())
                seed_acc   = float(((seeded['seed_diff'] < 0) == seeded['label'].astype(bool)).mean())
            else:
                upset_rate = None
                seed_acc   = None
        else:
            upset_rate = None
            seed_acc   = None

        records.append({
            'year':        int(year),
            'n_games':     n,
            'accuracy':    round(acc,   4),
            'seed_accuracy': round(seed_acc, 4) if seed_acc is not None else None,
            'brier':       round(brier, 4),
            'logloss':     round(ll,    4),
            'upset_rate':  round(upset_rate, 4) if upset_rate is not None else None,
        })
    return records


# ── 2. Calibration curve ───────────────────────────────────────────────────────

def calibration_curve(cv_df: pd.DataFrame) -> list:
    """Bucket by favorite's predicted probability (always ≥ 0.5), show actual win rate."""
    # Normalise: always express as P(favorite wins)
    probs  = cv_df['prob'].values
    labels = cv_df['label'].values

    fav_prob  = np.where(probs >= 0.5, probs, 1 - probs)
    fav_label = np.where(probs >= 0.5, labels, 1 - labels)

    buckets = np.arange(0.50, 1.01, 0.05)
    records = []
    for i in range(len(buckets) - 1):
        lo, hi = buckets[i], buckets[i + 1]
        mask = (fav_prob >= lo) & (fav_prob < hi)
        n = int(mask.sum())
        if n < 5:
            continue
        records.append({
            'bucket_lo':   round(float(lo), 2),
            'bucket_hi':   round(float(hi), 2),
            'bucket_mid':  round(float((lo + hi) / 2), 3),
            'predicted':   round(float(fav_prob[mask].mean()), 4),
            'actual':      round(float(fav_label[mask].mean()), 4),
            'n':           n,
        })
    return records


# ── 3. Year-by-year feature correlation ───────────────────────────────────────

def yearly_feature_correlation(df: pd.DataFrame, feat_cols: list,
                                tracked: list) -> dict:
    """For each year, compute correlation of tracked features with outcome."""
    result = {}
    for year in sorted(df['year'].unique()):
        sub = df[df['year'] == year]
        year_data = []
        for col in tracked:
            if col not in sub.columns:
                continue
            valid = sub[[col, 'label']].dropna()
            if len(valid) >= 8:
                corr = float(valid[col].corr(valid['label']))
                year_data.append({'feature': col, 'label': lbl(col), 'correlation': round(corr, 4)})
        result[str(int(year))] = year_data
    return result


# ── 4. Era comparison ──────────────────────────────────────────────────────────

def era_comparison(df: pd.DataFrame, feat_cols: list) -> list:
    records = []
    for era_name, y_start, y_end in ERAS:
        sub = df[(df['year'] >= y_start) & (df['year'] <= y_end)]
        if sub.empty:
            continue
        corr_data = []
        for col in feat_cols:
            valid = sub[[col, 'label']].dropna()
            if len(valid) >= 10:
                corr_data.append({
                    'feature': col,
                    'label': lbl(col),
                    'correlation': round(float(valid[col].corr(valid['label'])), 4),
                })
        corr_data.sort(key=lambda x: abs(x['correlation']), reverse=True)
        records.append({
            'era':     era_name,
            'y_start': y_start,
            'y_end':   y_end,
            'n_games': int(len(sub)),
            'top_features': corr_data[:15],
        })
    return records


# ── 5. Upset analysis ──────────────────────────────────────────────────────────

def upset_analysis(df: pd.DataFrame, cv_df: pd.DataFrame, feat_cols: list) -> dict:
    seeded = cv_df[cv_df['seed_diff'].notna() & (cv_df['seed_diff'] != 0)].copy()
    if seeded.empty:
        return {}

    seeded['actual_upset'] = (
        ((seeded['seed_diff'] < 0) & (seeded['label'] == 0)) |
        ((seeded['seed_diff'] > 0) & (seeded['label'] == 1))
    )
    seeded['model_upset'] = (
        ((seeded['seed_diff'] < 0) & (seeded['pred'] == 0)) |
        ((seeded['seed_diff'] > 0) & (seeded['pred'] == 1))
    )

    # By seed matchup (R64 only: rounds 1)
    r64 = seeded[seeded['round'] == 1].copy()
    r64['seed1_val'] = r64.apply(
        lambda r: abs(r.get('seed_diff', 0)) / 2 + r.get('seed_diff', 0) / abs(r.get('seed_diff', 1))
                  if r.get('seed_diff') else None, axis=1
    )

    # Reconstruct seed pairs from seed_diff
    # seed_diff = seed1 - seed2, and in R64 seeds sum to 17
    seed_matchups = []
    for rnd in [1, 2, 3]:
        rnd_df = seeded[seeded['round'] == rnd]
        if rnd_df.empty:
            continue
        abs_diffs = rnd_df['seed_diff'].abs().value_counts().head(10)
        for diff_val, count in abs_diffs.items():
            if diff_val < 1:
                continue
            sub2 = rnd_df[rnd_df['seed_diff'].abs() == diff_val]
            if len(sub2) < 3:
                continue
            seed_matchups.append({
                'round':            ROUND_NAMES.get(rnd, f'R{rnd}'),
                'seed_diff':        int(diff_val),
                'n':                int(len(sub2)),
                'actual_upset_rate': round(float(sub2['actual_upset'].mean()), 4),
                'model_upset_rate':  round(float(sub2['model_upset'].mean()), 4),
            })
    seed_matchups.sort(key=lambda x: (x['round'], x['seed_diff']))

    # Feature correlations on upset games vs non-upsets
    upset_df   = df[df.index.isin(seeded[seeded['actual_upset']].index)]
    no_upset   = df[df.index.isin(seeded[~seeded['actual_upset']].index)]

    def corr_list(sub):
        out = []
        for col in feat_cols:
            valid = sub[[col, 'label']].dropna()
            if len(valid) >= 8:
                out.append({'feature': col, 'label': lbl(col),
                            'correlation': round(float(valid[col].corr(valid['label'])), 4)})
        return sorted(out, key=lambda x: abs(x['correlation']), reverse=True)

    return {
        'by_seed_matchup': seed_matchups,
        'upset_feature_correlation':    corr_list(upset_df)[:20],
        'non_upset_feature_correlation': corr_list(no_upset)[:20],
        'n_upsets':    int(seeded['actual_upset'].sum()),
        'n_non_upsets': int((~seeded['actual_upset']).sum()),
    }


# ── 6. Feature redundancy matrix ──────────────────────────────────────────────

def feature_redundancy(df: pd.DataFrame, feat_cols: list,
                        top_feats: list) -> dict:
    """Pairwise Pearson correlations between the top N features."""
    avail = [f for f in top_feats if f in df.columns][:20]
    sub   = df[avail].dropna()
    if len(sub) < 10:
        return {}

    mat   = sub.corr().values.tolist()
    mat_r = [[round(v, 3) for v in row] for row in mat]

    return {
        'features': avail,
        'labels':   [lbl(f) for f in avail],
        'matrix':   mat_r,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print('Building matchup data...')
    df = build_matchup_df()
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
    print(f'  {len(df)} games | {df["year"].nunique()} seasons | {len(feat_cols)} features')

    print('Building seed lookup...')
    seed_lkp = build_seed_lkp()
    df['seed1'] = df.apply(lambda r: seed_lkp.get((r['team1'], r['year'])), axis=1)
    df['seed2'] = df.apply(lambda r: seed_lkp.get((r['team2'], r['year'])), axis=1)
    df['seed_diff'] = df['seed1'] - df['seed2']

    print('Running leave-year-out CV...')
    cv_df = leave_year_out_cv(df)
    cv_df = cv_df.copy()
    cv_df['seed_diff'] = df.loc[cv_df.index, 'seed_diff'].values

    # ── Identify top features by overall correlation for tracking ──────────────
    overall_corr = {}
    for col in feat_cols:
        valid = df[[col, 'label']].dropna()
        if len(valid) >= 10:
            overall_corr[col] = abs(float(valid[col].corr(valid['label'])))
    top_tracked = sorted(overall_corr, key=lambda c: overall_corr[c], reverse=True)[:12]

    print('Computing year-by-year accuracy...')
    ya = yearly_accuracy(df, cv_df)

    print('Computing calibration curve...')
    cal = calibration_curve(cv_df)

    print('Computing year-by-year feature correlation...')
    yfc = yearly_feature_correlation(df, feat_cols, top_tracked)

    print('Computing era comparison...')
    era = era_comparison(df, feat_cols)

    print('Computing upset analysis...')
    upsets = upset_analysis(df, cv_df, feat_cols)

    print('Computing feature redundancy matrix...')
    redundancy = feature_redundancy(df, feat_cols, top_tracked)

    # Overall correlation list for reference
    all_corr = sorted(
        [{'feature': c, 'label': lbl(c), 'correlation': round(overall_corr[c], 4)}
         for c in overall_corr],
        key=lambda x: x['correlation'], reverse=True,
    )

    output = {
        'generated_at':             str(date.today()),
        'n_games':                  int(len(df)),
        'n_features':               len(feat_cols),
        'tracked_features':         [{'feature': f, 'label': lbl(f)} for f in top_tracked],
        'overall_correlation':      all_corr[:30],
        'yearly_accuracy':          ya,
        'calibration':              cal,
        'yearly_feature_correlation': yfc,
        'era_comparison':           era,
        'upset_analysis':           upsets,
        'feature_redundancy':       redundancy,
    }

    def _sanitize(obj):
        """Replace NaN/Inf with None so the output is valid JSON."""
        if isinstance(obj, float) and (obj != obj or obj == float('inf') or obj == float('-inf')):
            return None
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        return obj

    output = _sanitize(output)
    out_path = CONFIG_DIR / 'analytics.json'
    out_path.write_text(json.dumps(output, indent=2))
    print(f'\nSaved → {out_path}')
    print(f'Sections: yearly_accuracy({len(ya)}yr), calibration({len(cal)}buckets), '
          f'era({len(era)}), upsets, redundancy({len(redundancy.get("features", []))}x{len(redundancy.get("features", []))})')


if __name__ == '__main__':
    main()
