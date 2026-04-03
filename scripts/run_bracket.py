"""Run bracket simulation for a given year.

Modes:
    Default  — deterministic bracket, print game-by-game
    --backtest — compare predictions to actuals (historical years only)
    --sims N   — Monte Carlo: run N simulations, print champion probabilities

Examples:
    python scripts/run_bracket.py --year 2025 --backtest
    python scripts/run_bracket.py --year 2025 --sims 5000
    python scripts/run_bracket.py --year 2024
    python scripts/run_bracket.py --year 2026 --sims 5000
"""

import argparse
import sys
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bracket import backtest_loo, load_team_features, monte_carlo, simulate, ROUND_NAMES
from src.features import build_matchup_df
from src import model as mdl

MODEL_PATH = Path(__file__).resolve().parent.parent / 'model.joblib'


def _get_model():
    """Load saved model or train from scratch if missing or stale."""
    if MODEL_PATH.exists():
        print(f'Loading model from {MODEL_PATH}')
        m = mdl.load(MODEL_PATH)
        # Quick feature-set validation: build a tiny sample and check predict_proba
        try:
            from src.features import build_matchup_df as _bmdf, DIFF_FEATURES
            sample = _bmdf()
            feat_cols = [c for c in DIFF_FEATURES if c in sample.columns]
            m.predict_proba(sample[feat_cols].head(1))
            return m
        except ValueError:
            print('  Saved model feature set is stale — retraining...')
            MODEL_PATH.unlink()

    print('Training model (this takes ~30s)...')
    df = build_matchup_df()
    m = mdl.train(df)
    mdl.save(m, MODEL_PATH)
    return m


def _run_deterministic(year: int, m) -> None:
    team_table = load_team_features(year)
    games = simulate(year, m, team_table=team_table)

    print(f'\n{year} Bracket Prediction')
    print('=' * 52)
    for rnd in sorted({g['round'] for g in games}):
        rnd_games = [g for g in games if g['round'] == rnd]
        print(f'\n  {ROUND_NAMES.get(rnd, f"R{rnd}")}')
        for g in rnd_games:
            pct = int(g['prob'] * 100)
            bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
            print(f'    {g["team1"]:<28} vs {g["team2"]:<28}  →  {g["winner"]}  ({pct}%)')

    champ = [g for g in games if g['round'] == 6]
    if champ:
        print(f'\n  Predicted champion: {champ[0]["winner"].upper()}')


def _run_backtest(year: int) -> None:
    result = backtest_loo(year, verbose=True)
    print(f'\n  Overall: {result["accuracy"]:.1%}')


def _run_monte_carlo(year: int, m, n_sims: int) -> None:
    print(f'\nRunning {n_sims:,} simulations for {year}...')
    probs = monte_carlo(year, m, n_sims=n_sims)

    print(f'\n{year} Champion Probabilities  ({n_sims:,} sims)')
    print('=' * 48)
    for i, (team, p) in enumerate(probs.items(), 1):
        if p < 0.001:
            break
        bar = '█' * int(p * 50)
        print(f'  {i:>2}. {team:<30} {p:6.1%}  {bar}')


def main():
    parser = argparse.ArgumentParser(description='NCAA bracket simulator')
    parser.add_argument('--year',     type=int, required=True, help='Tournament year')
    parser.add_argument('--backtest', action='store_true',     help='Compare to actual results')
    parser.add_argument('--sims',     type=int, default=0,     help='Monte Carlo simulations (0=deterministic)')
    args = parser.parse_args()

    if args.backtest:
        _run_backtest(args.year)
        return

    m = _get_model()

    if args.sims > 0:
        _run_monte_carlo(args.year, m, args.sims)
    else:
        _run_deterministic(args.year, m)


if __name__ == '__main__':
    main()
