"""Run leave-year-out cross-validation and report accuracy metrics.

Builds the full matchup feature matrix for all available years, runs LYO-CV,
and prints accuracy, Brier score, and log loss — plus a breakdown by round.

Run from project root:
    python scripts/run_lyo_cv.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.metrics import brier_score_loss, log_loss

from src.features import build_matchup_df
from src.model import leave_year_out_cv

print('Building matchup feature matrix...')
df = build_matchup_df()

print('Running leave-year-out CV...')
cv = leave_year_out_cv(df)

acc   = (cv['pred'] == cv['label']).mean()
brier = brier_score_loss(cv['label'], cv['prob'])
ll    = log_loss(cv['label'], cv['prob'])

n_features = len([c for c in df.columns if c.endswith('_diff')])

print()
print('=' * 45)
print('Leave-Year-Out CV Results')
print('=' * 45)
print(f'  Games evaluated : {len(cv)}')
print(f'  Features used   : {n_features}')
print(f'  Accuracy        : {acc:.3f}')
print(f'  Brier score     : {brier:.4f}  (lower is better)')
print(f'  Log loss        : {ll:.4f}  (lower is better)')
print()
print('Accuracy by round:')
for rnd, grp in cv.groupby('round'):
    racc = (grp['pred'] == grp['label']).mean()
    bar  = '#' * int(racc * 30)
    print(f'  R{rnd}  ({len(grp):3d} games)  {racc:.3f}  {bar}')
print()
print('Accuracy by year:')
for year, grp in cv.groupby('year'):
    yacc = (grp['pred'] == grp['label']).mean()
    bar  = '#' * int(yacc * 30)
    print(f'  {int(year)}  ({len(grp):2d} games)  {yacc:.3f}  {bar}')
