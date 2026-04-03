"""Conference tournament performance features.

Extracts per-team conference tournament stats from existing gameplan parquets.
Uses a 14-day pre-NCAA-tournament window to identify conference tournament games
— no separate data source needed.

Why a date window works:
  - Regular season ends 7–10 days before the NCAA tournament begins.
  - Conference tournaments run 4–7 days immediately before the NCAA start.
  - A 14-day lookback from the NCAA cutoff cleanly captures all conf tournament
    games and nothing from the regular season (regular neutral-site events happen
    in November/December, not late February/March).

Features computed per team:
    conf_tourney_wins      — int: wins in conf tournament (0 if no games played)
    conf_tourney_win_pct   — float: win rate; 0.5 neutral prior if 0 games
    conf_tourney_net_eff   — float: mean(off_eff − def_eff); NaN if 0 games

Main entry point:
    build_conf_tourney_matchup_df(bracket_df, years) → pd.DataFrame
        One row per matchup with CONF_TOURNEY_DIFF_FEATURES columns.
        Merge with features.build_matchup_df() output on index.
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.names import normalize_name

DATA_DIR   = Path(__file__).parent.parent / 'data'
CONFIG_DIR = Path(__file__).parent.parent / 'config'
DATES_PATH = CONFIG_DIR / 'tournament_dates.json'

MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}

# Days before NCAA start that define the conference tournament window.
# 14 days is conservative: longest conference tournament is ~7 days,
# and regular season always ends at least 7 days before the NCAA start.
WINDOW_DAYS = 14

CONF_TOURNEY_FEATURES = [
    'conf_tourney_wins',
    'conf_tourney_win_pct',
    'conf_tourney_net_eff',
]
CONF_TOURNEY_DIFF_FEATURES = [f'{f}_diff' for f in CONF_TOURNEY_FEATURES]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_cutoffs() -> dict[int, str]:
    """Return {year: 'YYYY-MM-DD'} NCAA start dates from tournament_dates.json."""
    raw = json.loads(DATES_PATH.read_text())
    return {int(k): v for k, v in raw.items() if not k.startswith('_')}


def _conf_window_bounds(ncaa_date_str: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Compute (start_md, end_md) for the conference tournament window.

    Window = [ncaa_date − WINDOW_DAYS, ncaa_date).
    Returns two (month, day) tuples.
    """
    y, m, d = (int(x) for x in ncaa_date_str.split('-'))
    end   = date(y, m, d)
    start = end - timedelta(days=WINDOW_DAYS)
    return (start.month, start.day), (end.month, end.day)


def _parse_date(date_str: str) -> tuple[int, int] | None:
    """Parse 'Mon Mar 10' → (3, 10). Returns None on failure."""
    match = re.search(r'([A-Za-z]{3})\s+(\d+)', str(date_str))
    if not match:
        return None
    month = MONTH_MAP.get(match.group(1))
    if month is None:
        return None
    return month, int(match.group(2))


def _season_key(month: int, day: int) -> tuple[int, int]:
    """Sortable key that orders the basketball season correctly.

    Nov=11 < Dec=12 < Jan=13 < Feb=14 < Mar=15 < Apr=16.
    Months Jan–Mar get +12 so they sort after Nov/Dec.
    """
    return (month + 12 if month < 4 else month, day)


def _in_window(date_str: str, start_md: tuple[int, int], end_md: tuple[int, int]) -> bool:
    """Return True if date_str falls in [start_md, end_md)."""
    parsed = _parse_date(date_str)
    if not parsed:
        return False
    return _season_key(*start_md) <= _season_key(*parsed) < _season_key(*end_md)


# ── Per-year loader ────────────────────────────────────────────────────────────

def load_conf_tourney_features(year: int, ncaa_date_str: str) -> pd.DataFrame:
    """Load gameplan parquets for one year and extract conference tournament stats.

    Returns DataFrame indexed by normalized team name with CONF_TOURNEY_FEATURES
    columns. Teams with no games in the window are absent — callers assign defaults.
    """
    gp_dir = DATA_DIR / str(year) / 'gameplan'
    if not gp_dir.exists():
        return pd.DataFrame()

    start_md, end_md = _conf_window_bounds(ncaa_date_str)

    frames = []
    for p in gp_dir.glob('*.parquet'):
        df = pd.read_parquet(p)
        if 'team' not in df.columns or df.empty:
            continue
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    all_games = pd.concat(frames, ignore_index=True)
    all_games['team'] = all_games['team'].map(normalize_name)

    # Filter to the conference tournament window
    in_window = all_games['date'].map(lambda d: _in_window(str(d), start_md, end_md))
    ct = all_games[in_window].copy()

    if ct.empty:
        return pd.DataFrame()

    for col in ('off_eff', 'def_eff'):
        if col in ct.columns:
            ct[col] = pd.to_numeric(ct[col], errors='coerce')

    ct['won']     = (ct['outcome'] == 'W').astype(float)
    ct['net_eff'] = ct['off_eff'] - ct['def_eff']

    rows = []
    for team, grp in ct.groupby('team'):
        n    = len(grp)
        wins = float(grp['won'].sum())
        rows.append({
            'team':                  team,
            'conf_tourney_wins':     wins,
            'conf_tourney_win_pct':  wins / n,
            'conf_tourney_net_eff':  float(grp['net_eff'].mean()),
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index('team')


# ── Matchup diff builder ───────────────────────────────────────────────────────

def _get_team_stats(table: pd.DataFrame, team: str) -> dict:
    """Look up a team's conf tourney stats; return defaults if not found."""
    if not table.empty and team in table.index:
        return {f: float(table.loc[team, f]) for f in CONF_TOURNEY_FEATURES}
    # Default: 0 games played. win_pct = 0.5 (neutral — no information),
    # net_eff = NaN (model will impute via its own missing-value handling).
    return {
        'conf_tourney_wins':    0.0,
        'conf_tourney_win_pct': 0.5,
        'conf_tourney_net_eff': float('nan'),
    }


def build_conf_tourney_matchup_df(
    bracket_df: pd.DataFrame,
    years: list[int],
) -> pd.DataFrame:
    """Build conference tournament feature diffs for every matchup in bracket_df.

    Args:
        bracket_df: Must have columns year, team1, team2.
        years:      Years to process (must match bracket_df years).

    Returns:
        DataFrame with same index as bracket_df plus CONF_TOURNEY_DIFF_FEATURES
        columns. Teams with no conf tournament data receive:
            conf_tourney_wins_diff    = 0.0 (both teams default to 0)
            conf_tourney_win_pct_diff = 0.0 (both teams default to 0.5)
            conf_tourney_net_eff_diff = NaN
    """
    cutoffs = _load_cutoffs()

    print(f'Loading conference tournament features for {len(years)} seasons...')
    ct_tables: dict[int, pd.DataFrame] = {
        y: load_conf_tourney_features(y, cutoffs[y])
        for y in years
        if y in cutoffs
    }

    diff_rows = []
    for _, game in bracket_df.iterrows():
        year  = int(game['year'])
        t1    = game['team1']
        t2    = game['team2']
        table = ct_tables.get(year, pd.DataFrame())

        f1  = _get_team_stats(table, t1)
        f2  = _get_team_stats(table, t2)
        row = {'year': year, 'team1': t1, 'team2': t2}

        for feat in CONF_TOURNEY_FEATURES:
            row[f'{feat}_diff'] = f1[feat] - f2[feat]

        diff_rows.append(row)

    return pd.DataFrame(diff_rows)
