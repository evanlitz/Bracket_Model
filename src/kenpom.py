import pandas as pd
from pathlib import Path

# Only 2001 and 2002 use the old column names.
# Maps old -> modern canonical names.
_COLUMN_RENAME = {
    'season':      'Season',
    'ORtg':        'AdjOE',
    'RankORtg':    'RankAdjOE',
    'DRtg':        'AdjDE',
    'RankDRtg':    'RankAdjDE',
    'NetRtg':      'AdjEM',
    'RankNetRtg':  'RankAdjEM',
}

# Canonical column order after normalization.
CANONICAL_COLS = [
    'Season', 'TeamName',
    'Tempo', 'RankTempo', 'AdjTempo', 'RankAdjTempo',
    'OE', 'RankOE', 'AdjOE', 'RankAdjOE',
    'DE', 'RankDE', 'AdjDE', 'RankAdjDE',
    'AdjEM', 'RankAdjEM',
    'seed',
]

DATA_DIR = Path(__file__).parent.parent / 'data'
YEARS = list(range(2001, 2027))
YEARS.remove(2020)


def load_kenpom(year: int) -> pd.DataFrame:
    """Load and normalize a single year's KenPom pre-tournament summary."""
    yy = str(year)[2:]
    path = DATA_DIR / str(year) / f'summary{yy}_pt.csv'

    df = pd.read_csv(path)
    df.rename(columns=_COLUMN_RENAME, inplace=True)

    missing = set(CANONICAL_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"{year}: missing columns after normalization: {missing}")

    df = df[CANONICAL_COLS].copy()

    # Normalize seed: empty string or whitespace -> None, otherwise int
    df['seed'] = pd.to_numeric(df['seed'], errors='coerce').astype('Int64')

    return df


def load_all_kenpom() -> pd.DataFrame:
    """Load and concatenate all years into a single normalized DataFrame."""
    frames = [load_kenpom(year) for year in YEARS]
    df = pd.concat(frames, ignore_index=True)
    return df
