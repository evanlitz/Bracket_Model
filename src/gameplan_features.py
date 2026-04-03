"""Pre-tournament rolling features from per-game data (gameplan parquets).

For each team, computes stats over the last 10 regular/conference-tournament
games played BEFORE the NCAA tournament started. Tournament start dates are
read from config/tournament_dates.json, which was populated from verified
Wikipedia sources for each year (play-in / First Four start date).

Main entry point:
    build_rolling_matchup_df(years) -> pd.DataFrame
        One row per tournament matchup with rolling _diff columns.
        Merge with features.build_matchup_df() output on (year, team1, team2).
"""

import json
import re
from pathlib import Path

import pandas as pd

from src.names import normalize_name

DATA_DIR    = Path(__file__).parent.parent / 'data'
CONFIG_DIR  = Path(__file__).parent.parent / 'config'
DATES_PATH  = CONFIG_DIR / 'tournament_dates.json'
MONTH_MAP   = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}
# Number of games to use for "recent form" window
L_WINDOW = 10

# Rolling features computed per team before tournament cutoff
ROLLING_FEATURES = [
    'l10_off_eff',    # mean offensive efficiency, last 10 games
    'l10_def_eff',    # mean defensive efficiency, last 10 games
    'l10_net_eff',    # l10_off_eff - l10_def_eff
    'l10_win_pct',    # win rate, last 10 games
    'l10_efg',        # mean effective FG%, last 10 games
    'l10_to_pct',     # mean turnover rate, last 10 games
    'l10_opp_rank',   # mean opponent KP rank, last 10 (lower = harder schedule)
    'momentum_off',   # l10_off_eff - season_off_eff  (positive = heating up)
    'momentum_def',   # l10_def_eff - season_def_eff  (negative = tightening)
]

ROLLING_DIFF_FEATURES = [f'{f}_diff' for f in ROLLING_FEATURES]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_cutoffs() -> dict[int, tuple[int, int]]:
    """Return {year: (month, day)} cutoff from tournament_dates.json."""
    raw = json.loads(DATES_PATH.read_text())
    cutoffs = {}
    for k, v in raw.items():
        if k.startswith('_'):
            continue
        year = int(k)
        _, m, d = v.split('-')
        cutoffs[year] = (int(m), int(d))
    return cutoffs


def _parse_date(date_str: str) -> tuple[int, int] | None:
    """Parse gameplan date string like 'Thu Mar 13' -> (month, day)."""
    m = re.search(r'([A-Za-z]{3})\s+(\d+)', date_str)
    if not m:
        return None
    month = MONTH_MAP.get(m.group(1))
    day   = int(m.group(2))
    if month is None:
        return None
    return month, day


def _before_cutoff(date_str: str, cutoff: tuple[int, int]) -> bool:
    """Return True if date_str represents a date strictly before cutoff."""
    parsed = _parse_date(date_str)
    if parsed is None:
        return False
    cm, cd = cutoff
    pm, pd_ = parsed
    # Treat Jan/Feb as always before any March cutoff
    # Nov/Dec are always before any March cutoff
    if pm < cm:
        return True
    if pm > cm:
        return False
    return pd_ < cd


# ── Per-year loader ───────────────────────────────────────────────────────────

def load_pretournament_rolling(year: int, cutoff: tuple[int, int]) -> pd.DataFrame:
    """Load all gameplan parquets for one year, filter to pre-tournament games,
    and compute rolling + season stats for each team.

    Returns DataFrame indexed by normalized team name. Missing teams (empty
    parquets, no data) will simply not appear — callers get NaN on join.
    """
    gp_dir = DATA_DIR / str(year) / 'gameplan'
    if not gp_dir.exists():
        return pd.DataFrame()

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

    # Filter to pre-tournament games only
    mask = all_games['date'].map(lambda d: _before_cutoff(str(d), cutoff))
    pre = all_games[mask].copy()

    if pre.empty:
        return pd.DataFrame()

    # Coerce efficiency columns to float
    for col in ('off_eff', 'def_eff', 'off_efg', 'off_to_pct', 'opp_kp_rank'):
        if col in pre.columns:
            pre[col] = pd.to_numeric(pre[col], errors='coerce')

    pre['won'] = (pre['outcome'] == 'W').astype(float)

    rows = []
    for team, grp in pre.groupby('team'):
        # Sort by date: Nov < Dec < Jan < Feb < Mar (no year in string, but
        # all seasons span Nov–Mar so month order is sufficient)
        grp = grp.copy()
        grp['_sort'] = grp['date'].map(
            lambda d: (_parse_date(str(d)) or (0, 0))
        )
        # Convert (month, day) to sortable int: treat Nov/Dec as month -2/-1
        def sort_key(md):
            m, d = md
            # Season runs Nov–Mar. Jan/Feb/Mar must sort AFTER Nov/Dec.
            # Bug fix: old `m if m >= 3` put Mar(3) before Nov(11).
            # Correct: add 12 to Jan/Feb/Mar so they read 13/14/15.
            return (m + 12 if m < 4 else m, d)
        grp['_sort_int'] = grp['_sort'].map(sort_key)
        grp = grp.sort_values('_sort_int')

        n = len(grp)
        last10 = grp.tail(L_WINDOW)

        season_off = grp['off_eff'].mean()
        season_def = grp['def_eff'].mean()

        row = {
            'team': team,
            'l10_off_eff':  last10['off_eff'].mean(),
            'l10_def_eff':  last10['def_eff'].mean(),
            'l10_net_eff':  last10['off_eff'].mean() - last10['def_eff'].mean(),
            'l10_win_pct':  last10['won'].mean(),
            'l10_efg':      last10['off_efg'].mean() if 'off_efg' in last10.columns else float('nan'),
            'l10_to_pct':   last10['off_to_pct'].mean() if 'off_to_pct' in last10.columns else float('nan'),
            'l10_opp_rank': last10['opp_kp_rank'].mean() if 'opp_kp_rank' in last10.columns else float('nan'),
            'momentum_off': last10['off_eff'].mean() - season_off,
            'momentum_def': last10['def_eff'].mean() - season_def,
        }
        rows.append(row)

    result = pd.DataFrame(rows).set_index('team')
    return result


# ── Matchup diff builder ──────────────────────────────────────────────────────

def build_rolling_matchup_df(
    bracket_df: pd.DataFrame,
    years: list[int],
) -> pd.DataFrame:
    """Build rolling feature diffs for every matchup in bracket_df.

    Args:
        bracket_df: Output of features.build_matchup_df() — must have
                    columns: year, round, team1, team2, label.
        years:      Years to process (must match bracket_df years).

    Returns:
        DataFrame with same index as bracket_df plus ROLLING_DIFF_FEATURES
        columns. Rows where either team has no gameplan data get NaN diffs.
    """
    cutoffs = _load_cutoffs()

    print(f'Loading gameplan rolling features for {len(years)} seasons...')
    rolling: dict[int, pd.DataFrame] = {
        y: load_pretournament_rolling(y, cutoffs[y])
        for y in years
        if y in cutoffs
    }

    diff_rows = []
    for _, game in bracket_df.iterrows():
        year  = int(game['year'])
        t1    = game['team1']
        t2    = game['team2']
        table = rolling.get(year, pd.DataFrame())

        row = {'year': year, 'team1': t1, 'team2': t2}
        if not table.empty and t1 in table.index and t2 in table.index:
            f1 = pd.to_numeric(table.loc[t1], errors='coerce')
            f2 = pd.to_numeric(table.loc[t2], errors='coerce')
            for feat in ROLLING_FEATURES:
                if feat in table.columns:
                    row[f'{feat}_diff'] = float(f1[feat]) - float(f2[feat])
                else:
                    row[f'{feat}_diff'] = float('nan')
        else:
            for feat in ROLLING_FEATURES:
                row[f'{feat}_diff'] = float('nan')

        diff_rows.append(row)

    return pd.DataFrame(diff_rows)
