"""Traces a team's game-by-game path through a historical NCAA tournament.

Loads bracket.csv for the given year and extracts all games where the team
appeared, sorted by round. Enriches with opponent seeds from KenPom.
"""

import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.kenpom import load_kenpom
from src.names import normalize_name

DATA_DIR = _ROOT / 'data'

ROUND_NAMES = {
    1: 'Round of 64',
    2: 'Round of 32',
    3: 'Sweet 16',
    4: 'Elite 8',
    5: 'Final Four',
    6: 'Championship',
}


def _build_seed_lkp(year: int) -> dict[str, int]:
    """Return {normalized_team: seed} for a given year from KenPom summary."""
    try:
        kp = load_kenpom(year)
        lkp = {}
        for _, row in kp.iterrows():
            if pd.notna(row['seed']):
                lkp[normalize_name(str(row['TeamName']))] = int(row['seed'])
        return lkp
    except Exception:
        return {}


def get_bracket_path(year: int, team: str, seed_lkp: dict | None = None) -> list[dict]:
    """Return the team's tournament game-by-game path for the given year.

    Args:
        year:     Season year.
        team:     Normalized team name.
        seed_lkp: Optional {team: seed} dict. Loaded fresh if not provided.

    Returns:
        List of game dicts, sorted by Round. Each dict:
            round_num, round_name, opponent, team_score, opp_score,
            outcome ('W'/'L'), team_seed, opp_seed, region
    """
    path = DATA_DIR / str(year) / 'bracket.csv'
    if not path.exists():
        return []

    df = pd.read_csv(path)
    df['Team1_norm']   = df['Team1'].map(lambda x: normalize_name(str(x)))
    df['Team2_norm']   = df['Team2'].map(lambda x: normalize_name(str(x)))
    df['Winner_norm']  = df['Winner'].map(lambda x: normalize_name(str(x)))

    if seed_lkp is None:
        seed_lkp = _build_seed_lkp(year)

    team_seed = seed_lkp.get(team)
    games = []

    for _, row in df.iterrows():
        t1 = row['Team1_norm']
        t2 = row['Team2_norm']
        if team not in (t1, t2):
            continue

        if team == t1:
            opponent   = t2
            team_score = row['Score1']
            opp_score  = row['Score2']
        else:
            opponent   = t1
            team_score = row['Score2']
            opp_score  = row['Score1']

        outcome = 'W' if row['Winner_norm'] == team else 'L'
        rnd = int(row['Round'])

        games.append({
            'round_num':   rnd,
            'round_name':  ROUND_NAMES.get(rnd, f'Round {rnd}'),
            'opponent':    opponent,
            'team_score':  int(team_score) if pd.notna(team_score) else None,
            'opp_score':   int(opp_score)  if pd.notna(opp_score)  else None,
            'outcome':     outcome,
            'team_seed':   team_seed,
            'opp_seed':    seed_lkp.get(opponent),
            'region':      str(row['Region']),
        })

    games.sort(key=lambda g: g['round_num'])
    return games
