"""Coaching experience features.

For each tournament matchup, computes three coaching experience metrics
for each team's head coach before year Y:

    coach_years_current      — consecutive seasons at this school before year Y
    coach_career_tourney_apps — NCAA tournament appearances across all schools
                                before year Y (pre-2002 from scraped stint totals;
                                2002+ counted exactly from bracket.csv)
    coach_career_ff           — Final Four appearances across all schools before
                                year Y (same sourcing as tourney_apps)

Data sources:
    config/team_coaches.json     — {team: {year: coach_name}}
    data/coaches_raw/*.json      — per-school stint totals (ncaa_apps, ff)
    bracket.csv (per year)       — post-2001 tournament appearances + FF rounds

Pre-2002 history rule:
    Only stints with year_to <= 2001 contribute their scraped totals.
    Stints straddling 2002 are counted from bracket.csv only (post-2001 portion).
    This avoids double-counting at the cost of a small undercount for
    coaches active at a school both before and after 2002.

Main entry point:
    build_coach_matchup_df(bracket_df, years) → pd.DataFrame
        One row per matchup with COACH_DIFF_FEATURES columns.
        Merge with features.build_matchup_df() output on index.
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from src.names import normalize_name

DATA_DIR     = Path(__file__).parent.parent / 'data'
CONFIG_DIR   = Path(__file__).parent.parent / 'config'
COACHES_PATH = CONFIG_DIR / 'team_coaches.json'
RAW_DIR      = DATA_DIR / 'coaches_raw'

# Round number in bracket.csv that corresponds to the Final Four
FINAL_FOUR_ROUND = 5

COACH_FEATURES = [
    'coach_years_current',
    'coach_career_tourney_apps',
    'coach_career_ff',
]
COACH_DIFF_FEATURES = [f'{f}_diff' for f in COACH_FEATURES]


# ── Loaders ────────────────────────────────────────────────────────────────────

def _load_team_coaches() -> dict[str, dict[str, str]]:
    """Return {team: {year_str: coach_name}} from team_coaches.json."""
    return json.loads(COACHES_PATH.read_text(encoding='utf-8'))


def _build_post2001_index(
    bracket_df: pd.DataFrame,
    team_coaches: dict[str, dict[str, str]],
) -> tuple[dict[str, set[int]], dict[str, set[int]], dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    """Build post-2001 tournament stats per coach (global) and per (coach, team) (for pre-2002 correction).

    Returns:
        tourney_years:        {coach: {years in tournament}}
        ff_years:             {coach: {years reached Final Four}}
        post2001_apps_by_school:  {(coach, team): count of tourney apps post-2001}
        post2001_ff_by_school:    {(coach, team): count of FF apps post-2001}

    A team appearing in a round-5 game reached the Final Four.
    Counts are deduplicated by year (a coach isn't counted twice per season).
    """
    tourney_years: dict[str, set[int]]             = defaultdict(set)
    ff_years:      dict[str, set[int]]             = defaultdict(set)
    apps_by_school: dict[tuple[str, str], set[int]] = defaultdict(set)
    ff_by_school:   dict[tuple[str, str], set[int]] = defaultdict(set)

    for _, row in bracket_df.iterrows():
        year     = int(row['year'])
        round_no = int(row['round'])
        year_str = str(year)

        for team_col in ('team1', 'team2'):
            team  = row[team_col]
            coach = team_coaches.get(team, {}).get(year_str)
            if not coach:
                continue
            tourney_years[coach].add(year)
            apps_by_school[(coach, team)].add(year)
            if round_no == FINAL_FOUR_ROUND:
                ff_years[coach].add(year)
                ff_by_school[(coach, team)].add(year)

    return (
        dict(tourney_years),
        dict(ff_years),
        {k: len(v) for k, v in apps_by_school.items()},
        {k: len(v) for k, v in ff_by_school.items()},
    )


def _load_pre2002_history(
    post2001_apps_by_school: dict[tuple[str, str], int],
    post2001_ff_by_school:   dict[tuple[str, str], int],
    sr_to_normalized:        dict[str, str],
) -> dict[str, dict[str, int]]:
    """Scan coaches_raw/*.json and compute pre-2002 tournament stats per coach.

    For stints ending entirely before 2002 (year_to <= 2001): use raw totals directly.
    For stints straddling 2002 (year_from < 2002 <= year_to): subtract the post-2001
    bracket.csv count to isolate the pre-2002 portion, avoiding double-counting.

    Returns {coach_name: {'ncaa_apps': int, 'ff': int}}.
    """
    history: dict[str, dict[str, int]] = defaultdict(lambda: {'ncaa_apps': 0, 'ff': 0})

    for path in RAW_DIR.glob('*.json'):
        raw       = json.loads(path.read_text(encoding='utf-8'))
        school_id = raw.get('school_id', path.stem)
        team_name = sr_to_normalized.get(school_id)

        for entry in raw.get('coaches', []):
            year_from = entry.get('year_from')
            year_to   = entry.get('year_to')
            name      = entry.get('name', '').strip()
            if not name or year_from is None or year_to is None:
                continue

            raw_apps = entry.get('ncaa_apps') or 0
            raw_ff   = entry.get('ff')        or 0

            if year_to <= 2001:
                # Entire stint is pre-2002 — use raw totals directly
                history[name]['ncaa_apps'] += raw_apps
                history[name]['ff']        += raw_ff

            elif year_from < 2002:
                # Stint straddles 2002 — subtract post-2001 bracket counts
                # to isolate how many apps happened before 2002
                post_apps = post2001_apps_by_school.get((name, team_name), 0) if team_name else 0
                post_ff   = post2001_ff_by_school.get((name, team_name), 0)   if team_name else 0
                pre_apps  = max(0, raw_apps - post_apps)
                pre_ff    = max(0, raw_ff   - post_ff)
                history[name]['ncaa_apps'] += pre_apps
                history[name]['ff']        += pre_ff
            # year_from >= 2002: entirely post-2001, counted from bracket.csv — skip

    return dict(history)


def _build_coach_start_years(
    team_coaches: dict[str, dict[str, str]],
) -> dict[tuple[str, str], int]:
    """Precompute {(team, coach_name): first_year_at_school}.

    Used to compute coach_years_current = year - first_year.
    """
    start_years: dict[tuple[str, str], int] = {}
    for team, year_map in team_coaches.items():
        # Walk years in ascending order to find each coach's first year
        seen: dict[str, int] = {}
        for year_str in sorted(year_map.keys(), key=int):
            coach = year_map[year_str]
            if coach not in seen:
                seen[coach] = int(year_str)
        for coach, first_year in seen.items():
            # If a coach left and returned, their later stint gets a new start year.
            # The sort above gives us the FIRST appearance — we need to handle
            # stints separately by detecting gaps.
            pass  # handled below

    # Rebuild with gap detection: a new stint starts when a coach reappears
    # after being absent for at least one year.
    start_years = {}
    for team, year_map in team_coaches.items():
        sorted_years = sorted(year_map.keys(), key=int)
        prev_year: int | None = None
        prev_coach: str | None = None
        stint_start: int | None = None

        for year_str in sorted_years:
            coach = year_map[year_str]
            year  = int(year_str)

            new_stint = (
                coach != prev_coach
                or prev_year is None
                or year != prev_year + 1
            )
            if new_stint:
                stint_start = year

            start_years[(team, coach, stint_start)] = stint_start  # key includes start to allow returns
            prev_year  = year
            prev_coach = coach

    # Simplify: map (team, coach) → most recent stint start as of each year.
    # Store as {(team, coach, year): stint_start} for O(1) lookup.
    tenure_map: dict[tuple[str, str, int], int] = {}
    for team, year_map in team_coaches.items():
        sorted_years = sorted(year_map.keys(), key=int)
        prev_year: int | None = None
        prev_coach: str | None = None
        stint_start: int | None = None

        for year_str in sorted_years:
            coach = year_map[year_str]
            year  = int(year_str)

            if (coach != prev_coach or prev_year is None or year != prev_year + 1):
                stint_start = year

            tenure_map[(team, coach, year)] = stint_start  # type: ignore[assignment]
            prev_year  = year
            prev_coach = coach

    return tenure_map  # type: ignore[return-value]


# ── Feature computation ────────────────────────────────────────────────────────

def _get_coach_features(
    team: str,
    year: int,
    team_coaches: dict,
    tenure_map: dict,
    pre2002: dict,
    tourney_years: dict,
    ff_years: dict,
) -> dict:
    """Compute coach features for one (team, year).

    Returns defaults (zeros) when coaching data is unavailable.
    """
    defaults = {
        'coach_years_current':       0,
        'coach_career_tourney_apps': 0,
        'coach_career_ff':           0,
    }

    coach = team_coaches.get(team, {}).get(str(year))
    if not coach:
        return defaults

    # Years at current school
    stint_start = tenure_map.get((team, coach, year))
    years_current = (year - stint_start) if stint_start is not None else 0

    # Career tournament appearances before this year
    pre  = pre2002.get(coach, {})
    post_apps = len({y for y in tourney_years.get(coach, set()) if y < year})
    post_ff   = len({y for y in ff_years.get(coach,      set()) if y < year})

    return {
        'coach_years_current':       years_current,
        'coach_career_tourney_apps': pre.get('ncaa_apps', 0) + post_apps,
        'coach_career_ff':           pre.get('ff',        0) + post_ff,
    }


# ── Per-year team loader (for bracket simulation) ─────────────────────────────

def load_coach_features(year: int) -> pd.DataFrame:
    """Return per-team coaching stats for one year, indexed by normalized team name.

    Used by bracket.py to add coaching features to the team table before
    simulation — mirrors what build_coach_matchup_df does at training time.

    Returns DataFrame with COACH_FEATURES columns. Teams with no coaching data
    are absent — callers should fill NaN via reindex or join with how='left'.
    """
    team_coaches = _load_team_coaches()
    tenure_map   = _build_coach_start_years(team_coaches)

    # Build a minimal bracket_df covering just this year so we can use the
    # existing post-2001 index builder (needed for pre-2002 correction).
    bracket_path = DATA_DIR / str(year) / 'bracket.csv'
    if not bracket_path.exists():
        return pd.DataFrame()

    raw = pd.read_csv(bracket_path)
    raw.columns = raw.columns.str.lower()
    raw['team1'] = raw['team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    raw['team2'] = raw['team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    raw = raw.dropna(subset=['team1', 'team2'])
    raw['year'] = year

    all_years_path = CONFIG_DIR / 'team_coaches.json'
    if not all_years_path.exists():
        return pd.DataFrame()

    # Build post-2001 index across ALL years (needed for pre-2002 correction).
    all_brackets = []
    for y in range(2002, year + 1):
        if y == 2020:
            continue
        p = DATA_DIR / str(y) / 'bracket.csv'
        if not p.exists():
            continue
        b = pd.read_csv(p)
        b.columns = b.columns.str.lower()
        b['team1'] = b['team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
        b['team2'] = b['team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
        b = b.dropna(subset=['team1', 'team2'])
        b['year'] = y
        all_brackets.append(b)

    if not all_brackets:
        return pd.DataFrame()

    all_bracket_df = pd.concat(all_brackets, ignore_index=True)
    tourney_years, ff_years, apps_by_school, ff_by_school = _build_post2001_index(
        all_bracket_df, team_coaches
    )

    sr_map_path = CONFIG_DIR / 'sr_school_map.json'
    if not sr_map_path.exists():
        return pd.DataFrame()
    sr_to_normalized = json.loads(sr_map_path.read_text(encoding='utf-8'))
    pre2002 = _load_pre2002_history(apps_by_school, ff_by_school, sr_to_normalized)

    # Get all teams in this year's tournament
    teams = set()
    for col in ('team1', 'team2'):
        teams.update(raw[col].dropna().unique())

    rows = []
    for team in sorted(teams):
        f = _get_coach_features(team, year, team_coaches, tenure_map, pre2002, tourney_years, ff_years)
        rows.append({'team': team, **f})

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index('team')


# ── Matchup diff builder ───────────────────────────────────────────────────────

def build_coach_matchup_df(
    bracket_df: pd.DataFrame,
    years: list[int],
) -> pd.DataFrame:
    """Build coaching feature diffs for every matchup in bracket_df.

    Args:
        bracket_df: Must have columns year, team1, team2, round.
        years:      Years to process (must match bracket_df years).

    Returns:
        DataFrame with same index as bracket_df plus COACH_DIFF_FEATURES columns.
        Teams with no coaching data default to zeros.
    """
    print('Loading coaching features...')

    sr_to_normalized = json.loads((CONFIG_DIR / 'sr_school_map.json').read_text(encoding='utf-8'))

    team_coaches = _load_team_coaches()
    tenure_map   = _build_coach_start_years(team_coaches)
    tourney_years, ff_years, apps_by_school, ff_by_school = _build_post2001_index(bracket_df, team_coaches)
    pre2002      = _load_pre2002_history(apps_by_school, ff_by_school, sr_to_normalized)

    diff_rows = []
    for _, game in bracket_df.iterrows():
        year = int(game['year'])
        t1   = game['team1']
        t2   = game['team2']

        f1 = _get_coach_features(t1, year, team_coaches, tenure_map, pre2002, tourney_years, ff_years)
        f2 = _get_coach_features(t2, year, team_coaches, tenure_map, pre2002, tourney_years, ff_years)

        row = {'year': year, 'team1': t1, 'team2': t2}
        for feat in COACH_FEATURES:
            row[f'{feat}_diff'] = f1[feat] - f2[feat]

        diff_rows.append(row)

    return pd.DataFrame(diff_rows)
