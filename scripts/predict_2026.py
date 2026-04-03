"""Generate 2026 bracket predictions using the trained model.

Simulates the 2026 tournament deterministically (argmax winner each game)
using the model trained on all 2002-2025 data. Saves results to
data/2026/bracket_loo.json in the same format as historical years so the
app can serve it via GET /api/simulate/2026.

Run from project root:
    python scripts/predict_2026.py
    python scripts/predict_2026.py --force   # overwrite existing output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bracket import simulate
from src import model as mdl

DATA_DIR   = Path(__file__).resolve().parent.parent / 'data'
MODEL_PATH = Path(__file__).resolve().parent.parent / 'model.joblib'
OUT_PATH   = DATA_DIR / '2026' / 'bracket_loo.json'


def main():
    parser = argparse.ArgumentParser(description='Predict 2026 NCAA bracket')
    parser.add_argument('--force', action='store_true', help='Overwrite existing output')
    args = parser.parse_args()

    if OUT_PATH.exists() and not args.force:
        print(f'Output already exists: {OUT_PATH}')
        print('Use --force to overwrite.')
        return

    if not MODEL_PATH.exists():
        print('model.joblib not found. Run: python scripts/run_bracket.py --year 2026 --sims 1')
        sys.exit(1)

    print('Loading model...')
    m = mdl.load(MODEL_PATH)

    print('Simulating 2026 bracket...')
    games = simulate(2026, m)

    # Normalize to match the historical bracket_loo.json format.
    # No actual results yet — actual_winner, correct, scores are all null.
    for g in games:
        g['round']         = str(g['round'])
        g['actual_winner'] = None
        g['correct']       = None
        g['score1']        = None
        g['score2']        = None

    output = {
        'year':              2026,
        'accuracy':          None,
        'accuracy_by_round': {},
        'games':             games,
    }

    OUT_PATH.write_text(json.dumps(output, indent=2, default=str))

    print(f'\n2026 Bracket Prediction')
    print('=' * 60)
    round_names = {'1': 'R64', '2': 'R32', '3': 'S16', '4': 'E8', '5': 'F4', '6': 'NCG'}
    for rnd in sorted({g['round'] for g in games}):
        rnd_games = [g for g in games if g['round'] == rnd]
        print(f'\n  {round_names.get(rnd, f"R{rnd}")}')
        for g in rnd_games:
            winner_prob = g['prob'] if g['winner'] == g['team1'] else 1 - g['prob']
            print(f'    {g["team1"]:<28} vs {g["team2"]:<28}  ->  {g["winner"]}  ({int(winner_prob*100)}%)')

    champ = [g for g in games if g['round'] == '6']
    if champ:
        print(f'\n  Predicted champion: {champ[0]["winner"].upper()}')

    print(f'\nSaved -> {OUT_PATH}')
    print('Restart the backend to serve /api/simulate/2026.')


if __name__ == '__main__':
    main()
