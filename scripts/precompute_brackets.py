"""Precompute leave-year-out bracket predictions for all historical years.

For each year with a bracket.csv, trains on all OTHER years (leave-year-out),
simulates that year's bracket, and saves results to data/{year}/bracket_loo.json.

Run once from project root:
    python scripts/precompute_brackets.py
    python scripts/precompute_brackets.py --force   # overwrite existing

Takes ~30s per year (~10 min total for all 23 years).
Results are served by GET /api/simulate/{year}.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.bracket import backtest_loo

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'


def _get_scores(year: int) -> dict:
    """Load (score1, score2) keyed by match_id from bracket.csv."""
    p = DATA_DIR / str(year) / 'bracket.csv'
    df = pd.read_csv(p)
    scores = {}
    for _, row in df.iterrows():
        mid = int(row['MatchID'])
        s1 = int(row['Score1']) if pd.notna(row.get('Score1')) else None
        s2 = int(row['Score2']) if pd.notna(row.get('Score2')) else None
        scores[mid] = (s1, s2)
    return scores


def precompute(year: int) -> None:
    out_path = DATA_DIR / str(year) / 'bracket_loo.json'
    print(f'  {year}: training LOO model + simulating...', end='', flush=True)

    result = backtest_loo(year, verbose=False)
    scores = _get_scores(year)

    for g in result['games']:
        s1, s2 = scores.get(g['match_id'], (None, None))
        g['score1'] = s1
        g['score2'] = s2

    output = {
        'year': year,
        'accuracy': round(result['accuracy'], 4),
        'accuracy_by_round': {
            str(k): round(v, 4)
            for k, v in result['accuracy_by_round'].items()
        },
        'games': result['games'],
    }

    out_path.write_text(json.dumps(output, indent=2, default=str))
    correct = sum(1 for g in result['games'] if g.get('correct'))
    total   = sum(1 for g in result['games'] if g.get('correct') is not None)
    print(f' done  {correct}/{total}  ({result["accuracy"]:.1%})')


def main():
    parser = argparse.ArgumentParser(description='Precompute LOO bracket predictions')
    parser.add_argument('--force', action='store_true', help='Overwrite existing files')
    parser.add_argument('--year', type=int, default=None, help='Only compute one year')
    args = parser.parse_args()

    if args.year:
        years = [args.year]
    else:
        years = [
            y for y in range(2002, 2026)
            if y != 2020 and (DATA_DIR / str(y) / 'bracket.csv').exists()
        ]

    print(f'Precomputing LOO brackets for {len(years)} year(s)')
    if len(years) > 1:
        print('Takes ~30s per year (~10 min total)\n')

    skipped = 0
    for year in years:
        out_path = DATA_DIR / str(year) / 'bracket_loo.json'
        if out_path.exists() and not args.force:
            print(f'  {year}: already exists (use --force to overwrite)')
            skipped += 1
            continue
        precompute(year)

    computed = len(years) - skipped
    print(f'\nDone. {computed} computed, {skipped} skipped.')
    if computed:
        print(f'Files written to data/{{year}}/bracket_loo.json')


if __name__ == '__main__':
    main()
