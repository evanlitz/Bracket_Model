"""Simulate the 2026 tournament from the Sweet 16 onward.

Behavior:
  1. Lock in the actual Sweet 16 field from data/2026/bracket.csv
     using the recorded winners from rounds 1 and 2.
  2. For each remaining matchup, run Monte Carlo simulations of that matchup.
  3. Advance the team with the higher simulated win percentage.
  4. Repeat for Elite Eight, Final Four, and Championship.
  5. Save the deterministic Sweet 16-onward bracket with per-game percentages.

This script does NOT re-simulate rounds 1 or 2, so teams already eliminated
cannot leak back into the field.

Run from project root:
    python scripts/predict_2026_sweet16.py
    python scripts/predict_2026_sweet16.py --sims 10000
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.bracket import (
    ROUND_NAMES,
    _predict_game,
    _precompute_team_vectors,
    load_team_features,
)
from src.features import build_matchup_df, DIFF_FEATURES
from src.names import normalize_name
from src import model as mdl

MODEL_PATH = Path(__file__).resolve().parent.parent / 'model.joblib'
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
OUT_JSON_PATH = DATA_DIR / '2026' / 'sweet16_prediction.json'
OUT_CSV_PATH = DATA_DIR / '2026' / 'sweet16_prediction.csv'
YEAR = 2026
START_ROUND = 3
N_SIMS_DEFAULT = 5000


def _get_model():
    """Load saved model, retraining if feature set has changed."""
    if MODEL_PATH.exists():
        print(f'Loading model from {MODEL_PATH}...')
        m = mdl.load(MODEL_PATH)
        try:
            df_sample = build_matchup_df()
            feat_cols = [c for c in DIFF_FEATURES if c in df_sample.columns]
            m.predict_proba(df_sample[feat_cols].head(1))
            print(f'  Model valid ({len(feat_cols)} features).')
            return m
        except (ValueError, KeyError):
            print('  Feature set changed — retraining...')
            MODEL_PATH.unlink()

    print('Training model on 2002-2025 data...')
    df = build_matchup_df()
    m  = mdl.train(df)
    mdl.save(m, MODEL_PATH)
    print(f'  Trained on {len(df)} games. Saved to {MODEL_PATH}')
    return m


def _load_bracket() -> pd.DataFrame:
    """Load the 2026 bracket and normalize team / winner names."""
    path = DATA_DIR / str(YEAR) / 'bracket.csv'
    if not path.exists():
        raise FileNotFoundError(f'No bracket.csv found for {YEAR}: {path}')

    bracket = pd.read_csv(path)
    for col in ('Team1', 'Team2', 'Winner'):
        bracket[col] = bracket[col].map(
            lambda x: normalize_name(x) if isinstance(x, str) and x.strip() else x
        )
    return bracket.set_index('MatchID')


def _build_feeders(bracket: pd.DataFrame) -> dict[int, list[int]]:
    """Return {match_id: [feeder_match_ids sorted in bracket slot order]}."""
    feeders: dict[int, list[int]] = {}
    for mid, row in bracket.iterrows():
        nxt = row['WinnerNextMatchID']
        if pd.notna(nxt):
            feeders.setdefault(int(nxt), []).append(int(mid))
    for mid in feeders:
        feeders[mid].sort()
    return feeders


def _seed_completed_winners(bracket: pd.DataFrame) -> dict[int, str]:
    """Seed winner map with actual winners from completed rounds."""
    predicted_winner: dict[int, str] = {}
    completed = bracket[bracket['Round'] < START_ROUND]
    for mid, row in completed.iterrows():
        winner = row.get('Winner')
        if isinstance(winner, str) and winner.strip():
            predicted_winner[int(mid)] = normalize_name(winner)
    return predicted_winner


def _resolve_matchup(
    match_id: int,
    row: pd.Series,
    predicted_winner: dict[int, str],
    feeders: dict[int, list[int]],
) -> tuple[str, str]:
    """Resolve a game's teams, preferring explicit bracket entries when present."""
    team1 = row.get('Team1')
    team2 = row.get('Team2')
    if isinstance(team1, str) and isinstance(team2, str) and team1 and team2:
        return team1, team2

    feeds = feeders.get(int(match_id), [])
    if len(feeds) >= 2:
        team1 = predicted_winner.get(feeds[0])
        team2 = predicted_winner.get(feeds[1])
        if team1 and team2:
            return team1, team2

    raise ValueError(f'Could not resolve teams for MatchID {match_id}')


def _mc_matchup(
    team1: str,
    team2: str,
    model,
    team_table: pd.DataFrame,
    team_vectors: dict,
    n_sims: int,
    rng: random.Random,
) -> tuple[float, float]:
    """Return MC win percentages for one matchup that sum to 100%."""
    _, team1_prob = _predict_game(
        team1,
        team2,
        team_table,
        model,
        probabilistic=False,
        rng=None,
        team_vectors=team_vectors,
    )

    team1_wins = 0
    for _ in range(n_sims):
        if rng.random() < team1_prob:
            team1_wins += 1

    p1 = team1_wins / n_sims
    p2 = 1.0 - p1
    return p1, p2


def simulate_sweet16(n_sims: int) -> list[dict]:
    """Lock the Sweet 16 field, then advance the higher-MC team each round."""
    model = _get_model()
    team_table = load_team_features(YEAR)
    team_vectors = _precompute_team_vectors(team_table, model)
    bracket = _load_bracket()
    feeders = _build_feeders(bracket)
    predicted_winner = _seed_completed_winners(bracket)
    rng = random.Random(42)

    results: list[dict] = []

    print(f'\nRunning Sweet 16-onward simulation with {n_sims:,} MC draws per matchup...')
    for rnd in range(START_ROUND, 7):
        round_games = bracket[bracket['Round'] == rnd]
        for match_id, row in round_games.iterrows():
            team1, team2 = _resolve_matchup(int(match_id), row, predicted_winner, feeders)
            p1, p2 = _mc_matchup(team1, team2, model, team_table, team_vectors, n_sims, rng)
            winner = team1 if p1 >= p2 else team2
            predicted_winner[int(match_id)] = winner

            results.append({
                'match_id': int(match_id),
                'round': int(rnd),
                'round_name': ROUND_NAMES.get(int(rnd), f'R{rnd}'),
                'region': str(row.get('Region', '')),
                'team1': team1,
                'team2': team2,
                'team1_win_pct': round(p1, 4),
                'team2_win_pct': round(p2, 4),
                'winner': winner,
                'simulations': int(n_sims),
            })

    return results


def _to_payload(results: list[dict], n_sims: int) -> dict:
    champion = ''
    title_games = [g for g in results if g['round'] == 6]
    if title_games:
        champion = title_games[0]['winner']

    return {
        'year': YEAR,
        'start_round': START_ROUND,
        'start_round_name': ROUND_NAMES.get(START_ROUND, f'R{START_ROUND}'),
        'method': (
            'Sweet 16 field locked from actual completed games; '
            'each remaining matchup simulated via Monte Carlo; '
            'higher win-percentage team advanced round by round.'
        ),
        'simulations_per_matchup': int(n_sims),
        'champion': champion,
        'games': results,
    }


def _build_summary_rows(results: list[dict]) -> list[dict]:
    """Return flat rows convenient for spreadsheet / post-analysis work."""
    rows = []
    for g in results:
        winner_pct = g['team1_win_pct'] if g['winner'] == g['team1'] else g['team2_win_pct']
        loser = g['team2'] if g['winner'] == g['team1'] else g['team1']
        loser_pct = 1.0 - winner_pct
        rows.append({
            'match_id': g['match_id'],
            'round': g['round'],
            'round_name': g['round_name'],
            'region': g['region'],
            'team1': g['team1'],
            'team2': g['team2'],
            'team1_win_pct': g['team1_win_pct'],
            'team2_win_pct': g['team2_win_pct'],
            'winner': g['winner'],
            'winner_win_pct': round(winner_pct, 4),
            'loser': loser,
            'loser_win_pct': round(loser_pct, 4),
            'simulations': g['simulations'],
        })
    return rows


def save_results(results: list[dict], n_sims: int, json_path: Path, csv_path: Path) -> None:
    """Persist results to disk in both JSON and CSV form."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    payload = _to_payload(results, n_sims)
    json_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    summary_df = pd.DataFrame(_build_summary_rows(results))
    summary_df.to_csv(csv_path, index=False)

    print(f'\nSaved JSON -> {json_path}')
    print(f'Saved CSV  -> {csv_path}')


def print_results(results: list[dict], n_sims: int) -> None:
    print()
    print('=' * 78)
    print(f'  2026 Sweet 16 Deterministic Bracket  ({n_sims:,} MC draws per matchup)')
    print('=' * 78)

    for rnd in range(START_ROUND, 7):
        round_games = [g for g in results if g['round'] == rnd]
        print(f'\n  {ROUND_NAMES.get(rnd, f"R{rnd}")}')
        for g in round_games:
            print(
                f'    {g["team1"]:<28} vs {g["team2"]:<28}  '
                f'->  {g["winner"]:<15}  '
                f'({g["team1_win_pct"]:.1%} / {g["team2_win_pct"]:.1%})'
            )

    title_games = [g for g in results if g['round'] == 6]
    if title_games:
        print(f'\n  Predicted champion: {title_games[0]["winner"].upper()}')


def main():
    parser = argparse.ArgumentParser(description='Predict 2026 from the Sweet 16 onward')
    parser.add_argument(
        '--sims',
        type=int,
        default=N_SIMS_DEFAULT,
        help=f'Monte Carlo draws per matchup (default: {N_SIMS_DEFAULT})',
    )
    parser.add_argument(
        '--out-json',
        type=Path,
        default=OUT_JSON_PATH,
        help=f'Output JSON path (default: {OUT_JSON_PATH})',
    )
    parser.add_argument(
        '--out-csv',
        type=Path,
        default=OUT_CSV_PATH,
        help=f'Output CSV path (default: {OUT_CSV_PATH})',
    )
    args = parser.parse_args()

    results = simulate_sweet16(args.sims)
    print_results(results, args.sims)
    save_results(results, args.sims, args.out_json, args.out_csv)


if __name__ == '__main__':
    main()
