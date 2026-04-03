"""2026 bracket advancement probability table.

For every tournament team, computes the probability of reaching each round
by running N Monte Carlo simulations and tracking how far each team advances.

Output is a ranked table sorted by championship probability:

  Team              R64    R32    S16    E8     F4     NCG    Seed
  Duke              99%    87%    71%    52%    34%    18%    1
  Florida           98%    83%    65%    47%    29%    14%    1
  ...

Also prints the most likely upset picks — games where the model favors
a lower seed.

Run from project root:
    python scripts/predict_2026_advancement.py
    python scripts/predict_2026_advancement.py --sims 10000
    python scripts/predict_2026_advancement.py --sims 5000 --save
"""

import argparse
import json
import random
import sys
import warnings
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.bracket import (
    load_team_features,
    simulate,
    _precompute_team_vectors,
)
from src.names import normalize_name
from src import model as mdl

DATA_DIR   = Path(__file__).resolve().parent.parent / 'data'
MODEL_PATH = Path(__file__).resolve().parent.parent / 'model.joblib'

ROUND_NAMES = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}


def load_seeds(year: int) -> dict:
    """Return {team_name: seed} from the KenPom summary CSV."""
    yy  = str(year)[2:]
    p   = DATA_DIR / str(year) / f'summary{yy}_pt.csv'
    df  = pd.read_csv(p)
    out = {}
    for _, row in df.iterrows():
        s = row.get('seed', '')
        if pd.notna(s) and str(s).strip() not in ('', 'nan'):
            name = normalize_name(str(row['TeamName']).strip())
            out[name] = int(float(s))
    return out


def run_advancement_sims(year: int, model, n_sims: int) -> dict:
    """Run n_sims Monte Carlo brackets; return per-team round reach counts."""
    team_table = load_team_features(year)

    # Pre-compute once
    bracket_path = DATA_DIR / str(year) / 'bracket.csv'
    raw = pd.read_csv(bracket_path)
    raw['Team1'] = raw['Team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    raw['Team2'] = raw['Team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    bracket_df   = raw.set_index('MatchID')
    team_vectors = _precompute_team_vectors(team_table, model)

    rng = random.Random(42)

    # reached[team][round] = number of sims where team played in that round
    reached = defaultdict(lambda: defaultdict(int))

    for _ in range(n_sims):
        games = simulate(
            year, model,
            team_table=team_table,
            probabilistic=True,
            rng=rng,
            bracket_df=bracket_df,
            team_vectors=team_vectors,
        )
        for g in games:
            rnd = int(g['round'])
            reached[g['team1']][rnd] += 1
            reached[g['team2']][rnd] += 1
            # Championship winner counts as reaching a virtual round 7
            if rnd == 6:
                reached[g['winner']][7] += 1

    return reached


def build_table(reached: dict, n_sims: int, seeds: dict) -> pd.DataFrame:
    """Convert raw reach counts to a probability DataFrame."""
    rows = []
    for team, rnd_counts in reached.items():
        row = {'team': team, 'seed': seeds.get(team, '')}
        for rnd in range(1, 7):
            row[ROUND_NAMES[rnd]] = rnd_counts.get(rnd, 0) / n_sims
        row['Champion'] = rnd_counts.get(7, 0) / n_sims
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values('Champion', ascending=False).reset_index(drop=True)
    return df


def print_table(df: pd.DataFrame) -> None:
    cols   = ['R64', 'R32', 'S16', 'E8', 'F4', 'NCG', 'Champion']
    header = f"{'#':>3}  {'Team':<28}  {'Seed':>4}  " + '  '.join(f'{c:>8}' for c in cols)
    print(header)
    print('-' * len(header))
    for i, row in df.iterrows():
        seed_str = str(int(row['seed'])) if row['seed'] != '' else '—'
        vals = '  '.join(
            f"{row[c]*100:>7.1f}%" for c in cols
        )
        print(f"{i+1:>3}  {row['team']:<28}  {seed_str:>4}  {vals}")


def print_upsets(year: int, model) -> None:
    """Print R1 games where the model favors the higher-seeded (underdog) team."""
    from src.bracket import _predict_game, load_team_features, _precompute_team_vectors

    team_table   = load_team_features(year)
    team_vectors = _precompute_team_vectors(team_table, model)
    seeds        = load_seeds(year)

    bracket = pd.read_csv(DATA_DIR / str(year) / 'bracket.csv')
    r1      = bracket[bracket['Round'] == 1]

    upsets = []
    for _, row in r1.iterrows():
        t1 = normalize_name(str(row['Team1']).strip()) if isinstance(row['Team1'], str) else None
        t2 = normalize_name(str(row['Team2']).strip()) if isinstance(row['Team2'], str) else None
        if not t1 or not t2:
            continue

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            winner, prob = _predict_game(t1, t2, team_table, model, team_vectors=team_vectors)

        s1 = seeds.get(t1)
        s2 = seeds.get(t2)
        if s1 is None or s2 is None:
            continue

        win_prob = prob if winner == t1 else 1 - prob
        loser    = t2 if winner == t1 else t1
        win_seed = s1 if winner == t1 else s2
        los_seed = s2 if winner == t1 else s1

        if win_seed > los_seed:
            upsets.append((win_seed - los_seed, winner, win_seed, loser, los_seed, win_prob))

    if upsets:
        print('\n  Model-predicted R1 upsets (lower seed favored over higher):')
        print(f"  {'Underdog':<28} {'Seed':>4}   {'Favorite':<28} {'Seed':>4}   {'Model Win%':>10}")
        print('  ' + '-' * 80)
        for _, winner, ws, loser, ls, wp in sorted(upsets, key=lambda x: -x[5]):
            print(f'  {winner:<28} {ws:>4}   {loser:<28} {ls:>4}   {wp*100:>9.1f}%')
    else:
        print('\n  No R1 upsets predicted by the model.')


def main():
    parser = argparse.ArgumentParser(description='2026 bracket advancement probabilities')
    parser.add_argument('--sims', type=int, default=5000, help='Number of simulations (default 5000)')
    parser.add_argument('--save', action='store_true',    help='Save results to data/2026/advancement.json')
    args = parser.parse_args()

    print(f'Loading model...')
    m = mdl.load(MODEL_PATH)

    seeds = load_seeds(2026)

    print(f'Running {args.sims:,} simulations...\n')
    reached = run_advancement_sims(2026, m, args.sims)

    df = build_table(reached, args.sims, seeds)

    print(f'2026 Tournament Advancement Probabilities  ({args.sims:,} sims)')
    print('=' * 90)
    print_table(df)

    print_upsets(2026, m)

    if args.save:
        out = DATA_DIR / '2026' / 'advancement.json'
        records = df.to_dict(orient='records')
        out.write_text(json.dumps({'year': 2026, 'n_sims': args.sims, 'teams': records}, indent=2))
        print(f'\nSaved -> {out}')


if __name__ == '__main__':
    main()
