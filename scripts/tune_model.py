"""Hyperparameter search for HistGradientBoostingClassifier.

Uses leave-year-out CV (same as model.py) to compare candidate hyperparameter
sets and identifies the best config.

Run from project root:
    python scripts/tune_model.py              # search only, print results
    python scripts/tune_model.py --apply      # search + update src/model.py
    python scripts/tune_model.py --quick      # run only first 6 candidates (fast)
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.features import build_matchup_df, DIFF_FEATURES
from src.model import augment

ROUND_NAMES = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}


# ── Candidate grid ─────────────────────────────────────────────────────────────
# Explores three axes:
#   depth:   max_leaf_nodes (15=shallow, 31=moderate, 63=deeper)
#   density: min_samples_leaf (conservative 20 → aggressive 8)
#   rate:    learning_rate × max_iter combos (slow+more vs fast+less)
# l2_regularization controls overfitting on the small yearly folds.

CANDIDATES = [
    # ── Baseline (current production config) ──
    dict(max_iter=500,  max_leaf_nodes=15, min_samples_leaf=20, learning_rate=0.05, l2_regularization=1.0),

    # ── Shallower trees, more regularization (conservative) ──
    dict(max_iter=600,  max_leaf_nodes=15, min_samples_leaf=15, learning_rate=0.05, l2_regularization=0.5),
    dict(max_iter=800,  max_leaf_nodes=15, min_samples_leaf=12, learning_rate=0.03, l2_regularization=1.0),
    dict(max_iter=1000, max_leaf_nodes=15, min_samples_leaf=10, learning_rate=0.02, l2_regularization=1.0),

    # ── Moderate depth ──
    dict(max_iter=600,  max_leaf_nodes=25, min_samples_leaf=15, learning_rate=0.05, l2_regularization=0.5),
    dict(max_iter=600,  max_leaf_nodes=25, min_samples_leaf=20, learning_rate=0.08, l2_regularization=1.0),
    dict(max_iter=800,  max_leaf_nodes=25, min_samples_leaf=15, learning_rate=0.05, l2_regularization=0.25),
    dict(max_iter=800,  max_leaf_nodes=25, min_samples_leaf=12, learning_rate=0.03, l2_regularization=0.5),
    dict(max_iter=1000, max_leaf_nodes=25, min_samples_leaf=10, learning_rate=0.02, l2_regularization=0.5),

    # ── Deeper trees ──
    dict(max_iter=600,  max_leaf_nodes=31, min_samples_leaf=15, learning_rate=0.05, l2_regularization=0.5),
    dict(max_iter=800,  max_leaf_nodes=31, min_samples_leaf=15, learning_rate=0.05, l2_regularization=0.5),
    dict(max_iter=800,  max_leaf_nodes=31, min_samples_leaf=12, learning_rate=0.03, l2_regularization=0.5),
    dict(max_iter=1000, max_leaf_nodes=31, min_samples_leaf=10, learning_rate=0.02, l2_regularization=0.25),

    # ── Deeper + more aggressive ──
    dict(max_iter=600,  max_leaf_nodes=63, min_samples_leaf=15, learning_rate=0.05, l2_regularization=1.0),
    dict(max_iter=800,  max_leaf_nodes=63, min_samples_leaf=20, learning_rate=0.03, l2_regularization=1.0),

    # ── High learning rate, fewer iterations ──
    dict(max_iter=300,  max_leaf_nodes=15, min_samples_leaf=20, learning_rate=0.10, l2_regularization=1.0),
    dict(max_iter=300,  max_leaf_nodes=25, min_samples_leaf=15, learning_rate=0.10, l2_regularization=0.5),
    dict(max_iter=400,  max_leaf_nodes=25, min_samples_leaf=12, learning_rate=0.10, l2_regularization=0.5),
]

# First 6 candidates for --quick mode
QUICK_CANDIDATES = CANDIDATES[:6]


# ── CV runner ──────────────────────────────────────────────────────────────────

def _cv(df: pd.DataFrame, params: dict) -> dict:
    """Leave-year-out CV. Returns accuracy, brier, log_loss, and per-round accuracy."""
    years     = sorted(df['year'].unique())
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]

    all_preds, all_labels, all_probs = [], [], []
    round_preds: dict[int, list] = {}
    round_labels: dict[int, list] = {}

    for test_year in years:
        train = augment(df[df['year'] != test_year])
        test  = df[df['year'] == test_year].copy()

        m = HistGradientBoostingClassifier(random_state=42, **params)
        m.fit(train[feat_cols], train['label'])

        proba = m.predict_proba(test[feat_cols])[:, 1]
        pred  = (proba >= 0.5).astype(int)

        all_preds.extend(pred.tolist())
        all_labels.extend(test['label'].tolist())
        all_probs.extend(proba.tolist())

        for rnd, grp in test.groupby('round'):
            idx   = grp.index
            rnd   = int(rnd)
            round_preds.setdefault(rnd, []).extend(pred[test.index.get_indexer(idx)].tolist())
            round_labels.setdefault(rnd, []).extend(grp['label'].tolist())

    acc   = float((np.array(all_preds) == np.array(all_labels)).mean())
    brier = float(brier_score_loss(all_labels, all_probs))
    ll    = float(log_loss(all_labels, all_probs))

    by_round = {}
    for rnd in sorted(round_preds):
        p = np.array(round_preds[rnd])
        l = np.array(round_labels[rnd])
        by_round[rnd] = float((p == l).mean())

    return {'accuracy': acc, 'brier': brier, 'log_loss': ll, 'by_round': by_round}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Tune HistGradientBoostingClassifier hyperparams')
    parser.add_argument('--apply', action='store_true', help='Update src/model.py with best params')
    parser.add_argument('--quick', action='store_true', help='Run only first 6 candidates (fast check)')
    args = parser.parse_args()

    print('Building matchup data...')
    df = build_matchup_df()
    n_feat = len([c for c in DIFF_FEATURES if c in df.columns])
    print(f'Dataset: {len(df)} games across {df["year"].nunique()} seasons, {n_feat} features\n')

    candidates = QUICK_CANDIDATES if args.quick else CANDIDATES
    print(f'Testing {len(candidates)} hyperparameter combinations...\n')

    results = []
    for i, params in enumerate(candidates, 1):
        print(f'  [{i:2d}/{len(candidates)}] '
              f'leaf={params["max_leaf_nodes"]:2d}  '
              f'min_leaf={params["min_samples_leaf"]:2d}  '
              f'lr={params["learning_rate"]:.2f}  '
              f'l2={params["l2_regularization"]:.2f}  '
              f'iter={params["max_iter"]}  ...', end='', flush=True)
        r = _cv(df, params)
        results.append({'params': params, **r})
        print(f'  acc={r["accuracy"]:.4f}  brier={r["brier"]:.4f}  ll={r["log_loss"]:.4f}')

    results.sort(key=lambda r: (-r['accuracy'], r['brier']))

    # ── Summary table ──
    print()
    print('=' * 80)
    print('Ranked results (by accuracy, then brier):')
    print('=' * 80)
    header = (f'  {"#":>2}  {"acc":>6}  {"brier":>6}  {"ll":>6}  '
              f'{"leaf":>4}  {"min_l":>5}  {"lr":>5}  {"l2":>5}  {"iter":>4}')
    print(header)
    print('  ' + '-' * 70)
    for i, r in enumerate(results, 1):
        p   = r['params']
        tag = '  <- best' if i == 1 else ('  <- current baseline' if p == candidates[0] else '')
        print(f'  {i:2d}  {r["accuracy"]:.4f}  {r["brier"]:.4f}  {r["log_loss"]:.4f}  '
              f'{p["max_leaf_nodes"]:4d}  {p["min_samples_leaf"]:5d}  '
              f'{p["learning_rate"]:5.2f}  {p["l2_regularization"]:5.2f}  '
              f'{p["max_iter"]:4d}{tag}')

    # ── Best config detail ──
    best = results[0]
    print()
    print('Best config round-by-round accuracy:')
    for rnd, acc in sorted(best['by_round'].items()):
        bar = '#' * int(acc * 30)
        print(f'  {ROUND_NAMES.get(rnd, f"R{rnd}"):<4}  {acc:.3f}  {bar}')

    baseline = next((r for r in results if r['params'] == candidates[0]), None)
    if baseline and best['params'] != candidates[0]:
        delta = best['accuracy'] - baseline['accuracy']
        print(f'\nImprovement over baseline: {delta:+.4f} ({delta*100:+.2f}%)')

    if args.apply:
        _apply_best(best['params'])
    else:
        print('\nRun with --apply to update src/model.py with the best params.')


def _apply_best(params: dict):
    """Rewrite _make_model() in src/model.py with the best params using regex."""
    model_path = Path(__file__).parent.parent / 'src' / 'model.py'
    text = model_path.read_text(encoding='utf-8')

    # Build the new HistGradientBoostingClassifier block
    lines = ['    return HistGradientBoostingClassifier(']
    for k, v in params.items():
        lines.append(f'        {k}={v},')
    lines.append('        random_state=42,')
    lines.append('    )')
    new_block = '\n'.join(lines)

    # Replace existing instantiation with regex (handles any current param values)
    pattern = r'    return HistGradientBoostingClassifier\(.*?\)'
    updated, n = re.subn(pattern, new_block, text, flags=re.DOTALL)

    if n == 0:
        print('\nWarning: could not find HistGradientBoostingClassifier in src/model.py.')
        print('Update it manually with:')
        print(new_block)
        return

    model_path.write_text(updated, encoding='utf-8')
    print(f'\nUpdated src/model.py with best params.')
    print('Delete model.joblib and retrain:')
    print('  del model.joblib')
    print('  python scripts/run_bracket.py --year 2026 --sims 1')


if __name__ == '__main__':
    main()
