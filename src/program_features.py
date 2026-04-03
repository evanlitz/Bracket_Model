"""Program pedigree and tournament experience features.

For each team, computes program-level tournament history signals:

    program_tourney_rate_l5  — fraction of last 5 seasons this program made
                               the NCAA tournament (0-1). Proxy for coaching
                               quality, program stability, and culture.
    program_f4_rate_l10      — fraction of last 10 seasons this program
                               reached the Final Four (round >= 5). Captures
                               the program's ceiling beyond just making the field.
    roster_prior_tourney     — minutes-weighted average of prior NCAA tournament
                               seasons each player has experienced (0-3 for a Sr
                               on a perennial contender). Captures "been here
                               before" experience.

Data sources:
    config/conferences.parquet            -> ncaa_tourney boolean per team x season
    data/{year}/bracket.csv              -> max round each team reached per year
    data/{year}/players/{team}.parquet   -> player class year (Fr/So/Jr/Sr)

Note: no coach name data exists in any file. These features are the best
available proxies for coaching quality and tournament experience.

Main entry point:
    build_program_matchup_df(bracket_df, years) -> pd.DataFrame
        One row per tournament matchup with program _diff columns.
        Merge with features.build_matchup_df() output on index.
"""

from pathlib import Path

import pandas as pd

from src.names import normalize_name

DATA_DIR   = Path(__file__).parent.parent / 'data'
CONFIG_DIR = Path(__file__).parent.parent / 'config'

PROGRAM_FEATURES      = ['program_tourney_rate_l5', 'program_f4_rate_l10']
PROGRAM_DIFF_FEATURES = [f'{f}_diff' for f in PROGRAM_FEATURES]


# ── Lookup builders (called once per build_program_matchup_df call) ────────────

def _build_conf_lookup() -> dict[tuple, bool]:
    """Build {(normalized_team, season): ncaa_tourney_bool} from conferences.parquet."""
    path = CONFIG_DIR / 'conferences.parquet'
    if not path.exists():
        return {}
    df = pd.read_parquet(path)
    df['team'] = df['team'].map(normalize_name)
    return dict(zip(zip(df['team'], df['season']), df['ncaa_tourney'].astype(bool)))


def _build_bracket_depth_lookup() -> dict[tuple, int]:
    """Build {(normalized_team, year): max_round_reached} from all available bracket CSVs.

    max_round = highest round in which the team appears as Team1 or Team2.
    Final Four = max_round >= 5; Championship game = max_round == 6.
    Loads all years in data/ to support 10-year lookback windows.
    """
    lkp: dict[tuple, int] = {}
    for bracket_path in sorted(DATA_DIR.glob('*/bracket.csv')):
        year = int(bracket_path.parent.name)
        df = pd.read_csv(bracket_path)
        for _, row in df.iterrows():
            rnd = int(row['Round'])
            for col in ('Team1', 'Team2'):
                t   = normalize_name(str(row[col]))
                key = (t, year)
                lkp[key] = max(lkp.get(key, 0), rnd)
    return lkp


# ── Per-year loader ────────────────────────────────────────────────────────────

def load_program_features(
    year: int,
    conf_lkp: dict[tuple, bool],
    bracket_lkp: dict[tuple, int],
) -> pd.DataFrame:
    """Compute program features for all teams in a given year.

    Returns DataFrame indexed by normalized team name with columns:
        program_tourney_rate_l5, program_f4_rate_l10

    Uses players/ directory to enumerate teams; teams without a players
    file are skipped (those teams aren't in the tournament anyway).
    """
    player_dir = DATA_DIR / str(year) / 'players'
    if not player_dir.exists():
        return pd.DataFrame()

    rows = []
    for p in player_dir.glob('*.parquet'):
        df = pd.read_parquet(p)
        if df.empty or 'team' not in df.columns:
            continue

        team = normalize_name(df['team'].iloc[0])

        # ── program_tourney_rate_l5 ────────────────────────────────────────────
        # Fraction of last 5 seasons this team made the NCAA tournament.
        window_l5 = [y for y in range(year - 5, year) if y != 2020]
        if window_l5:
            appearances = sum(int(conf_lkp.get((team, y), 0)) for y in window_l5)
            program_tourney_rate_l5 = appearances / len(window_l5)
        else:
            program_tourney_rate_l5 = float('nan')

        # ── program_f4_rate_l10 ────────────────────────────────────────────────
        # Fraction of last 10 seasons this team reached the Final Four.
        window_l10 = [y for y in range(year - 10, year) if y != 2020]
        if window_l10:
            f4s = sum(1 for y in window_l10 if bracket_lkp.get((team, y), 0) >= 5)
            program_f4_rate_l10 = f4s / len(window_l10)
        else:
            program_f4_rate_l10 = float('nan')

        rows.append({
            'team':                    team,
            'program_tourney_rate_l5': program_tourney_rate_l5,
            'program_f4_rate_l10':     program_f4_rate_l10,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index('team')


# ── Matchup diff builder ───────────────────────────────────────────────────────

def build_program_matchup_df(
    bracket_df: pd.DataFrame,
    years: list[int],
) -> pd.DataFrame:
    """Build program feature diffs for every matchup in bracket_df.

    Args:
        bracket_df: Must have columns year, team1, team2.
        years:      Years to process (must match bracket_df years).

    Returns:
        DataFrame with same index as bracket_df plus PROGRAM_DIFF_FEATURES
        columns. Rows where either team has no program data get NaN diffs.
    """
    print(f'Loading program features for {len(years)} seasons...')
    conf_lkp    = _build_conf_lookup()
    bracket_lkp = _build_bracket_depth_lookup()

    program_tables: dict[int, pd.DataFrame] = {
        y: load_program_features(y, conf_lkp, bracket_lkp) for y in years
    }

    diff_rows = []
    for _, game in bracket_df.iterrows():
        year  = int(game['year'])
        t1    = game['team1']
        t2    = game['team2']
        table = program_tables.get(year, pd.DataFrame())

        row: dict = {'year': year, 'team1': t1, 'team2': t2}
        if not table.empty and t1 in table.index and t2 in table.index:
            f1 = table.loc[t1]
            f2 = table.loc[t2]
            for feat in PROGRAM_FEATURES:
                row[f'{feat}_diff'] = float(f1[feat]) - float(f2[feat])
        else:
            for feat in PROGRAM_FEATURES:
                row[f'{feat}_diff'] = float('nan')

        diff_rows.append(row)

    return pd.DataFrame(diff_rows)
