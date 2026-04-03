"""Predict the 2026 bracket using a dedicated model trained per round.

For each round (R64 → NCG), trains a separate HistGradientBoostingClassifier
on only the historical games from that round (2002-2025), then uses that
model to predict the corresponding round of the 2026 bracket.

Contrast with predict_2026.py which uses a single model trained on all rounds.

Caveats:
  - R5 (Final Four)  has only ~46 historical games — treat as directional.
  - R6 (Championship) has only ~23 historical games — very small sample.
  - R1 and R2 are the most reliable (~736 and ~368 games respectively).

Run from project root:
    python scripts/predict_2026_by_round.py
    python scripts/predict_2026_by_round.py --save   # write bracket_by_round.json
"""

import argparse
import json
import random
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.bracket import load_team_features, _precompute_team_vectors, _predict_game
from src.features import build_matchup_df, DIFF_FEATURES
from src.model import augment, _make_model
from src.names import normalize_name

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

ROUND_NAMES = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}


def train_round_models(df: pd.DataFrame) -> dict:
    """Train one model per round on that round's historical games only.

    Returns {round_int: fitted model}.
    """
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
    models = {}
    print('Training round-specific models:')
    for rnd in sorted(df['round'].unique()):
        rnd_df = df[df['round'] == rnd]
        n_games = len(rnd_df)
        aug = augment(rnd_df)
        m = _make_model()
        m.fit(aug[feat_cols], aug['label'])
        models[int(rnd)] = m
        print(f'  {ROUND_NAMES.get(int(rnd), f"R{rnd}"):<6}  {n_games:>3} games  '
              f'{"(small sample — treat as directional)" if n_games < 100 else ""}')
    return models


def simulate_by_round(year: int, round_models: dict, team_table: pd.DataFrame) -> list:
    """Simulate the bracket using a different model for each round.

    Round 1 matchups come from bracket.csv. Round 2+ use predicted winners
    from the previous round. Each round's games are predicted by that round's
    dedicated model.
    """
    bracket_path = DATA_DIR / str(year) / 'bracket.csv'
    if not bracket_path.exists():
        raise FileNotFoundError(f'No bracket.csv for {year}')

    raw = pd.read_csv(bracket_path)
    raw['Team1'] = raw['Team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    raw['Team2'] = raw['Team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    bracket = raw.set_index('MatchID')

    # Pre-compute team vectors for each round's model (column order may differ)
    team_vectors_by_round = {
        rnd: _precompute_team_vectors(team_table, m)
        for rnd, m in round_models.items()
    }

    # Build feeder map: match_id -> [feeder_match_id1, feeder_match_id2]
    feeders: dict[int, list[int]] = {}
    for mid, row in bracket.iterrows():
        nxt = row['WinnerNextMatchID']
        if pd.notna(nxt):
            nxt = int(nxt)
            feeders.setdefault(nxt, []).append(mid)
    for mid in feeders:
        feeders[mid].sort()

    predicted_winner: dict[int, str] = {}
    results = []

    for rnd in sorted(bracket['Round'].unique()):
        model      = round_models.get(rnd)
        tv         = team_vectors_by_round.get(rnd)
        round_games = bracket[bracket['Round'] == rnd]

        for mid, row in round_games.iterrows():
            if rnd == 1:
                t1 = row['Team1']
                t2 = row['Team2']
            else:
                feeds = feeders.get(mid, [])
                if len(feeds) < 2:
                    continue
                t1 = predicted_winner.get(feeds[0], row['Team1'])
                t2 = predicted_winner.get(feeds[1], row['Team2'])

            if model is None:
                winner, prob = t1, 0.5
            else:
                winner, prob = _predict_game(
                    t1, t2, team_table, model,
                    probabilistic=False, rng=None, team_vectors=tv,
                )

            predicted_winner[mid] = winner
            results.append({
                'match_id':   mid,
                'round':      str(rnd),
                'round_name': ROUND_NAMES.get(rnd, f'R{rnd}'),
                'region':     row.get('Region', ''),
                'team1':      t1,
                'team2':      t2,
                'prob':       round(prob, 4),
                'winner':     winner,
                'actual_winner': None,
                'correct':    None,
                'score1':     None,
                'score2':     None,
            })

    return results


def main():
    parser = argparse.ArgumentParser(description='Predict 2026 bracket with per-round models')
    parser.add_argument('--save', action='store_true', help='Save to data/2026/bracket_by_round.json')
    args = parser.parse_args()

    print('Loading historical matchup data...')
    df = build_matchup_df()
    print(f'  {len(df)} games across {df["year"].nunique()} seasons\n')

    round_models = train_round_models(df)

    print('\nLoading 2026 team features...')
    team_table = load_team_features(2026)
    print(f'  {len(team_table)} teams loaded\n')

    print('Simulating 2026 bracket...')
    games = simulate_by_round(2026, round_models, team_table)

    # Print results
    print(f'\n{"=" * 60}')
    print('2026 Bracket Prediction  (per-round models)')
    print(f'{"=" * 60}')
    for rnd in sorted({g['round'] for g in games}):
        rnd_games = [g for g in games if g['round'] == rnd]
        label = ROUND_NAMES.get(int(rnd), f'R{rnd}')
        print(f'\n  {label}  [model trained on {label} games only]')
        for g in rnd_games:
            winner_prob = g['prob'] if g['winner'] == g['team1'] else 1 - g['prob']
            print(f'    {g["team1"]:<28} vs {g["team2"]:<28}  ->  {g["winner"]}  ({int(winner_prob*100)}%)')

    champ = [g for g in games if g['round'] == '6']
    if champ:
        print(f'\n  Predicted champion: {champ[0]["winner"].upper()}')

    if args.save:
        out = DATA_DIR / '2026' / 'bracket_by_round.json'
        out.write_text(json.dumps({
            'year': 2026,
            'accuracy': None,
            'accuracy_by_round': {},
            'games': games,
        }, indent=2, default=str))
        print(f'\nSaved -> {out}')


if __name__ == '__main__':
    main()
