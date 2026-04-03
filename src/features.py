"""Build the matchup feature matrix for tournament game prediction.

For each historical tournament game (bracket.csv), joins pre-tournament
season stats for both teams and computes differential features
(team1_stat - team2_stat).

Main entry point:
    build_matchup_df(years) -> pd.DataFrame
        columns: year, round, team1, team2, label, <feature>_diff, ...
        label  : 1 = team1 won, 0 = team2 won
"""

import pandas as pd
from pathlib import Path

from src.kenpom import load_kenpom, YEARS
from src.names import normalize_name
from src.gameplan_features import build_rolling_matchup_df, ROLLING_DIFF_FEATURES
from src.player_features import build_player_matchup_df, PLAYER_DIFF_FEATURES
from src.program_features import build_program_matchup_df, PROGRAM_DIFF_FEATURES
from src.conf_tourney_features import build_conf_tourney_matchup_df, CONF_TOURNEY_DIFF_FEATURES
from src.coach_features import build_coach_matchup_df, COACH_DIFF_FEATURES

DATA_DIR = Path(__file__).parent.parent / 'data'

# Years with full scouting feature coverage (bench_min, d1_exp, etc. start 2007)
SCOUTING_YEARS = [y for y in YEARS if y >= 2002]

# KenPom columns to diff
KENPOM_FEATURES = ['AdjOE', 'AdjDE', 'AdjTempo', 'AdjEM', 'net_score_rate']

# Scouting columns to diff
SCOUTING_FEATURES = [
    'efg_pct_off', 'efg_pct_def',
    'to_pct_off',  'to_pct_def',
    'or_pct_off',  'or_pct_def',
    'ftr_off',     'ftr_def',
    'fg3a_rate_off', 'fg3a_rate_def',
    'fg2_pct_off', 'fg3_pct_off',
    'blk_pct_def', 'stl_rate_def',
    'd1_exp',      'avg_height',
    'pd3_off',     'pd3_def',
    'apl_off',     'apl_def',
]

DIFF_FEATURES = (
    [f'{c}_diff' for c in KENPOM_FEATURES + SCOUTING_FEATURES]
    + ROLLING_DIFF_FEATURES
    + PLAYER_DIFF_FEATURES
    + PROGRAM_DIFF_FEATURES
    + CONF_TOURNEY_DIFF_FEATURES
    + COACH_DIFF_FEATURES
)


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_season_scouting(year: int) -> pd.DataFrame:
    """Load all scouting parquets for one year into a DataFrame indexed by team.

    Returns empty DataFrame if no scouting directory exists for that year.
    """
    scouting_dir = DATA_DIR / str(year) / 'scouting'
    parquets = list(scouting_dir.glob('*.parquet'))
    if not parquets:
        return pd.DataFrame()

    frames = [pd.read_parquet(p) for p in parquets if p.stem != 'average_scouting']
    if not frames:
        return pd.DataFrame()
    # dropna(axis=1, how='all') prevents FutureWarning from concat with all-NA columns
    df = pd.concat([f.dropna(axis=1, how='all') for f in frames], ignore_index=True)
    df['team'] = df['team'].map(normalize_name)
    return df.set_index('team')


def load_season_features(year: int) -> pd.DataFrame:
    """Merge KenPom + scouting for one year into a single per-team feature table.

    Returns a DataFrame indexed by normalized team name.
    """
    kp = load_kenpom(year).copy()
    kp['TeamName'] = kp['TeamName'].map(normalize_name)
    # seed is Int64 (nullable); cast to float so arithmetic works cleanly
    kp['seed'] = kp['seed'].astype(float)
    kp = kp.set_index('TeamName')
    kp['net_score_rate'] = kp['AdjEM'] * kp['AdjTempo'] / 48

    sc = load_season_scouting(year)
    if sc.empty:
        return kp

    sc_cols = [c for c in SCOUTING_FEATURES if c in sc.columns]
    return kp.join(sc[sc_cols], how='left')


def load_brackets(years: list[int]) -> pd.DataFrame:
    """Load and concatenate bracket CSVs for the given years.

    Infers Winner from scores where the Winner field is missing.
    """
    frames = [
        pd.read_csv(DATA_DIR / str(y) / 'bracket.csv')
        for y in years
        if (DATA_DIR / str(y) / 'bracket.csv').exists()
    ]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    # Fill missing Winner from scores (Score1 > Score2 → Team1 wins)
    mask = df['Winner'].isna() & df['Score1'].notna() & df['Score2'].notna()
    df.loc[mask, 'Winner'] = df.loc[mask].apply(
        lambda r: r['Team1'] if r['Score1'] > r['Score2'] else r['Team2'], axis=1
    )
    return df.dropna(subset=['Winner'])


# ── Feature builder ───────────────────────────────────────────────────────────

def build_matchup_df(years: list[int] | None = None) -> pd.DataFrame:
    """Build the full matchup feature DataFrame for model training/evaluation.

    For each tournament game, looks up pre-tournament stats for both teams
    and computes differential features (team1 - team2). Games where either
    team cannot be matched are dropped and reported.

    Args:
        years: Tournament years to include. Defaults to SCOUTING_YEARS (2007+).

    Returns:
        DataFrame with columns:
            year, round, team1, team2  — metadata
            label                      — 1 = team1 won, 0 = team2 won
            <feature>_diff             — one per feature in DIFF_FEATURES
    """
    if years is None:
        years = SCOUTING_YEARS

    bracket = load_brackets(years)
    if bracket.empty:
        raise ValueError('No bracket data found for the requested years.')

    # Pre-load all season feature tables up front
    print(f'Loading features for {len(years)} seasons...')
    season_features: dict[int, pd.DataFrame] = {
        y: load_season_features(y) for y in years
    }

    rows = []
    missing = []

    for _, game in bracket.iterrows():
        year = int(game['Year'])
        if year not in season_features:
            continue

        t1 = normalize_name(game['Team1'])
        t2 = normalize_name(game['Team2'])
        feat_table = season_features[year]

        t1_missing = t1 not in feat_table.index
        t2_missing = t2 not in feat_table.index
        if t1_missing or t2_missing:
            missing.append((year, int(game['Round']), t1, t2, t1_missing, t2_missing))
            continue

        f1 = feat_table.loc[t1]
        f2 = feat_table.loc[t2]

        available = [c for c in KENPOM_FEATURES + SCOUTING_FEATURES if c in feat_table.columns]
        f1_num = pd.to_numeric(f1[available], errors='coerce')
        f2_num = pd.to_numeric(f2[available], errors='coerce')
        diffs = f1_num - f2_num

        row: dict = {
            'year':  year,
            'round': int(game['Round']),
            'team1': t1,
            'team2': t2,
            'label': 1 if normalize_name(game['Winner']) == t1 else 0,
        }
        for col in available:
            row[f'{col}_diff'] = diffs[col]

        rows.append(row)

    if missing:
        print(f'Warning: {len(missing)} game(s) dropped (name mismatch):')
        for year, rnd, t1, t2, t1m, t2m in missing[:15]:
            print(f'  {year} R{rnd}: {"[?] " if t1m else "    "}{t1!r}  vs  {"[?] " if t2m else "    "}{t2!r}')
        if len(missing) > 15:
            print(f'  ... and {len(missing) - 15} more')

    df = pd.DataFrame(rows)

    # Merge in pre-tournament rolling features from gameplan data
    rolling = build_rolling_matchup_df(df, years)
    df = df.merge(rolling.drop(columns=['year', 'team1', 'team2']),
                  left_index=True, right_index=True)

    # Merge in player roster features
    player = build_player_matchup_df(df, years)
    df = df.merge(player.drop(columns=['year', 'team1', 'team2']),
                  left_index=True, right_index=True)

    # Merge in program pedigree / tournament experience features
    program = build_program_matchup_df(df, years)
    df = df.merge(program.drop(columns=['year', 'team1', 'team2']),
                  left_index=True, right_index=True)

    # Merge in conference tournament performance features
    conf_tourney = build_conf_tourney_matchup_df(df, years)
    df = df.merge(conf_tourney.drop(columns=['year', 'team1', 'team2']),
                  left_index=True, right_index=True)

    # Merge in coaching experience features
    coach = build_coach_matchup_df(df, years)
    df = df.merge(coach.drop(columns=['year', 'team1', 'team2']),
                  left_index=True, right_index=True)

    print(f'Built {len(df)} matchups across {df["year"].nunique()} seasons '
          f'({len(df.columns) - 5} features).')
    return df
