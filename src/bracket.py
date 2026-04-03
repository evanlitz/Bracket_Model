"""Bracket simulation using the trained prediction model.

Simulates a full NCAA tournament bracket round-by-round using model win
probabilities. Supports both deterministic prediction (argmax) and Monte
Carlo sampling (probabilistic winner selection, N simulations).

Works with any bracket.csv that has at least Round 1 games filled in.
Round 2+ team assignments are computed from predicted (not actual) winners.

Main entry points:
    simulate(year, model, team_features) -> list[dict]
        Deterministic simulation of a single bracket.

    backtest(year, model, df_all) -> dict
        Simulate all historical years and report accuracy vs actual results.

    monte_carlo(year, model, team_features, n_sims) -> dict[str, float]
        Run N simulations; return {team: championship_win_probability}.

Usage:
    python scripts/run_bracket.py --year 2025
"""

import random
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.features import (
    DIFF_FEATURES,
    KENPOM_FEATURES,
    SCOUTING_FEATURES,
    load_season_features,
)
from src.gameplan_features import ROLLING_FEATURES, load_pretournament_rolling, _load_cutoffs
from src.names import normalize_name
from src.player_features import load_player_features, PLAYER_FEATURES
from src.program_features import (
    _build_conf_lookup,
    _build_bracket_depth_lookup,
    load_program_features,
    PROGRAM_FEATURES,
)
from src.conf_tourney_features import (
    load_conf_tourney_features,
    CONF_TOURNEY_FEATURES,
    _load_cutoffs as _load_ct_cutoffs,
    _get_team_stats as _ct_get_team_stats,
)
from src.coach_features import load_coach_features, COACH_FEATURES

DATA_DIR = Path(__file__).parent.parent / 'data'

ROUND_NAMES = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}


# ── Team feature loading ───────────────────────────────────────────────────────

def load_team_features(year: int) -> pd.DataFrame:
    """Load all pre-tournament features for every team in a given year.

    Returns DataFrame indexed by normalized team name with all DIFF_FEATURES
    source columns (not diffed yet — diffing happens per-matchup).

    Loads the same feature types the model was trained on:
        KenPom + scouting + rolling + player roster + program pedigree
    """
    season = load_season_features(year)

    cutoffs = _load_cutoffs()
    if year in cutoffs:
        rolling = load_pretournament_rolling(year, cutoffs[year])
        season = season.join(rolling, how='left')

    pl = load_player_features(year)
    if not pl.empty:
        season = season.join(pl[PLAYER_FEATURES], how='left')

    conf_lkp    = _build_conf_lookup()
    bracket_lkp = _build_bracket_depth_lookup()
    prog = load_program_features(year, conf_lkp, bracket_lkp)
    if not prog.empty:
        season = season.join(prog[PROGRAM_FEATURES], how='left')

    # Conference tournament features
    ct_cutoffs = _load_ct_cutoffs()
    if year in ct_cutoffs:
        ct = load_conf_tourney_features(year, ct_cutoffs[year])
        if not ct.empty:
            season = season.join(ct[CONF_TOURNEY_FEATURES], how='left')

    # Coaching experience features
    coach = load_coach_features(year)
    if not coach.empty:
        season = season.join(coach[COACH_FEATURES], how='left')

    return season


# ── Matchup feature computation ────────────────────────────────────────────────

def _game_features(t1: str, t2: str, team_table: pd.DataFrame) -> dict:
    """Compute diff features for a single matchup. Returns dict of col -> value.

    Covers all feature groups the model was trained on:
        KenPom + scouting + rolling + player roster + program pedigree
    """
    base_cols   = [c for c in KENPOM_FEATURES + SCOUTING_FEATURES if c in team_table.columns]
    roll_cols   = [c for c in ROLLING_FEATURES       if c in team_table.columns]
    player_cols = [c for c in PLAYER_FEATURES        if c in team_table.columns]
    prog_cols   = [c for c in PROGRAM_FEATURES       if c in team_table.columns]
    ct_cols     = [c for c in CONF_TOURNEY_FEATURES  if c in team_table.columns]
    coach_cols  = [c for c in COACH_FEATURES         if c in team_table.columns]
    all_cols    = base_cols + roll_cols + player_cols + prog_cols + ct_cols + coach_cols

    if t1 not in team_table.index or t2 not in team_table.index:
        return {}

    f1 = pd.to_numeric(team_table.loc[t1, all_cols], errors='coerce')
    f2 = pd.to_numeric(team_table.loc[t2, all_cols], errors='coerce')

    feats = {}
    for col in all_cols:
        feats[f'{col}_diff'] = float(f1[col] - f2[col]) if col in f1.index else float('nan')
    return feats


def _precompute_team_vectors(team_table: pd.DataFrame, model) -> dict:
    """Pre-compute a numpy feature vector for every team, in model column order.

    Returns {team_name: np.ndarray} where each array has one value per
    DIFF_FEATURES base column (i.e. the un-diffed per-team values).
    Diffing (t1 - t2) happens at prediction time via simple subtraction.
    """
    feat_cols = list(model.feature_names_in_) if hasattr(model, 'feature_names_in_') else DIFF_FEATURES
    # Each diff feature is named '<base>_diff'; strip the suffix to get the team-table column.
    base_cols = [c[:-5] if c.endswith('_diff') else c for c in feat_cols]
    present   = [c for c in base_cols if c in team_table.columns]
    indices   = [i for i, c in enumerate(base_cols) if c in team_table.columns]

    vectors = {}
    n = len(feat_cols)
    for team in team_table.index:
        arr = np.full(n, np.nan)
        row = pd.to_numeric(team_table.loc[team, present], errors='coerce').values
        for slot, val in zip(indices, row):
            arr[slot] = val
        vectors[team] = arr
    return vectors


def _predict_game(
    t1: str,
    t2: str,
    team_table: pd.DataFrame,
    model,
    probabilistic: bool = False,
    rng: random.Random | None = None,
    team_vectors: dict | None = None,
) -> tuple[str, float]:
    """Predict the winner of a single game.

    Returns (winner_name, p_team1_wins).
    If team features are missing, returns (t1, 0.5) as a coin-flip fallback.
    If team_vectors is provided (pre-computed numpy arrays), uses fast numpy
    path instead of constructing a DataFrame per call.
    """
    if team_vectors is not None:
        if t1 not in team_vectors or t2 not in team_vectors:
            return t1, 0.5
        X = (team_vectors[t1] - team_vectors[t2]).reshape(1, -1)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            prob = float(model.predict_proba(X)[0, 1])
    else:
        feats = _game_features(t1, t2, team_table)
        feat_cols = [c for c in DIFF_FEATURES if c in feats]
        if not feat_cols:
            return t1, 0.5
        X = pd.DataFrame([feats])[feat_cols]
        if hasattr(model, 'feature_names_in_'):
            X = X.reindex(columns=model.feature_names_in_)
        prob = float(model.predict_proba(X)[0, 1])

    if probabilistic:
        r = (rng or random).random()
        winner = t1 if r < prob else t2
    else:
        winner = t1 if prob >= 0.5 else t2

    return winner, prob


# ── Core simulation ────────────────────────────────────────────────────────────

def simulate(
    year: int,
    model,
    team_table: pd.DataFrame | None = None,
    probabilistic: bool = False,
    rng: random.Random | None = None,
    bracket_df: pd.DataFrame | None = None,
    team_vectors: dict | None = None,
) -> list[dict]:
    """Simulate a full bracket for the given year.

    Loads the bracket.csv for `year`, predicts each game in round order,
    and feeds predicted winners (not actual winners) into subsequent rounds.

    Args:
        year:          Tournament year.
        model:         Trained HistGradientBoostingClassifier.
        team_table:    Pre-loaded team features (from load_team_features). If
                       None, loads automatically.
        probabilistic: If True, sample winner probabilistically instead of argmax.
        rng:           Optional seeded Random instance for reproducibility.
        bracket_df:    Pre-parsed bracket DataFrame (indexed by MatchID). If
                       provided, skips the CSV read. Pass this in monte_carlo
                       loops to avoid re-reading the file each simulation.
        team_vectors:  Pre-computed numpy feature vectors per team (from
                       _precompute_team_vectors). If provided, skips per-game
                       DataFrame construction for a major speed boost.

    Returns:
        List of game dicts, one per match, with keys:
            match_id, round, region, team1, team2, prob, winner
    """
    if bracket_df is not None:
        bracket = bracket_df
    else:
        bracket_path = DATA_DIR / str(year) / 'bracket.csv'
        if not bracket_path.exists():
            raise FileNotFoundError(f'No bracket.csv for {year}')
        raw = pd.read_csv(bracket_path)
        raw['Team1'] = raw['Team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
        raw['Team2'] = raw['Team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
        bracket = raw.set_index('MatchID')

    if team_table is None:
        team_table = load_team_features(year)

    # Build reverse map: match_id -> sorted list of feeder match_ids
    # Lower feeder match_id -> Team1 slot; higher -> Team2 slot
    feeders: dict[int, list[int]] = {}
    for mid, row in bracket.iterrows():
        nxt = row['WinnerNextMatchID']
        if pd.notna(nxt):
            nxt = int(nxt)
            feeders.setdefault(nxt, []).append(mid)
    for mid in feeders:
        feeders[mid].sort()  # lower id = Team1 slot

    # Simulate round by round
    predicted_winner: dict[int, str] = {}  # match_id -> predicted winner name
    results = []

    for rnd in sorted(bracket['Round'].unique()):
        round_games = bracket[bracket['Round'] == rnd]

        for mid, row in round_games.iterrows():
            # Determine team assignments: R1 is fixed from bracket.csv;
            # R2+ comes from predicted winners of feeder games.
            if rnd == 1:
                t1 = row['Team1']
                t2 = row['Team2']
            else:
                feeds = feeders.get(mid, [])
                if len(feeds) < 2:
                    continue
                t1 = predicted_winner.get(feeds[0], row['Team1'])
                t2 = predicted_winner.get(feeds[1], row['Team2'])

            winner, prob = _predict_game(t1, t2, team_table, model, probabilistic, rng, team_vectors=team_vectors)
            predicted_winner[mid] = winner

            results.append({
                'match_id': mid,
                'round':    rnd,
                'round_name': ROUND_NAMES.get(rnd, f'R{rnd}'),
                'region':   row.get('Region', ''),
                'team1':    t1,
                'team2':    t2,
                'prob':     round(prob, 4),
                'winner':   winner,
            })

    return results


# ── Backtesting ────────────────────────────────────────────────────────────────

def backtest_loo(year: int, verbose: bool = True) -> dict:
    """Leave-year-out backtest: train on all years except `year`, simulate that year.

    The model never sees target-year data — this is the honest evaluation.
    Equivalent to leave_year_out_cv() in model.py but runs a full bracket
    simulation rather than just game-level predictions.
    """
    from src.features import build_matchup_df
    from src import model as mdl

    df = build_matchup_df()
    m = mdl.train(df[df['year'] != year])
    return backtest(year, m, verbose=verbose)


def backtest(year: int, model, verbose: bool = True) -> dict:
    """Simulate bracket for one historical year; compare to actual results.

    Returns:
        dict with keys: year, games (list of result dicts with 'correct' field),
        accuracy (overall), accuracy_by_round (dict[round -> float])
    """
    bracket_path = DATA_DIR / str(year) / 'bracket.csv'
    bracket_actual = pd.read_csv(bracket_path)
    # Infer missing winners from scores (same as features.py)
    mask = bracket_actual['Winner'].isna() & bracket_actual['Score1'].notna() & bracket_actual['Score2'].notna()
    bracket_actual.loc[mask, 'Winner'] = bracket_actual.loc[mask].apply(
        lambda r: r['Team1'] if r['Score1'] > r['Score2'] else r['Team2'], axis=1
    )
    bracket_actual['Winner'] = bracket_actual['Winner'].where(bracket_actual['Winner'].notna()).map(
        lambda v: normalize_name(v) if isinstance(v, str) else v
    )
    actual_winners = dict(zip(bracket_actual['MatchID'], bracket_actual['Winner']))

    team_table = load_team_features(year)
    games = simulate(year, model, team_table=team_table)

    for g in games:
        actual = actual_winners.get(g['match_id'])
        g['actual_winner'] = actual
        g['correct'] = (g['winner'] == actual) if actual else None

    correct = [g for g in games if g['correct'] is True]
    total   = [g for g in games if g['correct'] is not None]
    acc = len(correct) / len(total) if total else 0.0

    by_round: dict[int, float] = {}
    for rnd in sorted({g['round'] for g in games}):
        rnd_games = [g for g in games if g['round'] == rnd and g['correct'] is not None]
        if rnd_games:
            by_round[rnd] = sum(g['correct'] for g in rnd_games) / len(rnd_games)

    if verbose:
        print(f'\n{year} Bracket Simulation')
        print('=' * 42)
        print(f'  Overall accuracy: {acc:.3f}  ({len(correct)}/{len(total)} games)')
        print()
        for rnd, racc in by_round.items():
            rnd_games = [g for g in games if g['round'] == rnd and g['correct'] is not None]
            bar = '#' * int(racc * 25)
            print(f'  {ROUND_NAMES.get(rnd, f"R{rnd}"):<4}  {racc:.3f}  {bar}')
        champ_game = [g for g in games if g['round'] == 6]
        if champ_game:
            g = champ_game[0]
            print(f'\n  Predicted champion : {g["winner"]}')
            print(f'  Actual champion    : {g["actual_winner"]}')

    return {
        'year': year,
        'games': games,
        'accuracy': acc,
        'accuracy_by_round': by_round,
    }


# ── Monte Carlo ────────────────────────────────────────────────────────────────

def monte_carlo(
    year: int,
    model,
    n_sims: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Run N probabilistic bracket simulations; return championship win rates.

    Args:
        year:   Tournament year.
        model:  Trained model.
        n_sims: Number of simulations to run.
        seed:   Random seed for reproducibility.

    Returns:
        Dict mapping team name -> fraction of simulations they won the championship.
        Sorted descending by win probability.
    """
    team_table = load_team_features(year)

    # Pre-compute once — these are reused across all simulations
    bracket_path = DATA_DIR / str(year) / 'bracket.csv'
    if not bracket_path.exists():
        raise FileNotFoundError(f'No bracket.csv for {year}')
    raw = pd.read_csv(bracket_path)
    raw['Team1'] = raw['Team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    raw['Team2'] = raw['Team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    bracket_df   = raw.set_index('MatchID')
    team_vectors = _precompute_team_vectors(team_table, model)

    rng = random.Random(seed)
    champ_counts: dict[str, int] = {}

    for _ in range(n_sims):
        games = simulate(year, model, team_table=team_table, probabilistic=True, rng=rng,
                         bracket_df=bracket_df, team_vectors=team_vectors)
        champ_games = [g for g in games if g['round'] == 6]
        if champ_games:
            champ = champ_games[0]['winner']
            champ_counts[champ] = champ_counts.get(champ, 0) + 1

    return {
        team: count / n_sims
        for team, count in sorted(champ_counts.items(), key=lambda x: -x[1])
    }
