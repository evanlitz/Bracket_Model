"""Audit team name matching between gameplan, scouting, and bracket data.

Checks:
1. Every gameplan team name (normalized) has a matching scouting parquet
2. Every tournament team in bracket.csv (normalized) has a gameplan parquet
3. Reports mismatches with suggested name_map.json additions

Run from project root:
    python scripts/audit_names.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.names import normalize_name
from src.features import SCOUTING_YEARS, load_brackets

DATA_DIR = Path(__file__).parent.parent / 'data'


def scouting_teams(year: int) -> set[str]:
    d = DATA_DIR / str(year) / 'scouting'
    teams = set()
    for p in d.glob('*.parquet'):
        if p.stem == 'average_scouting':
            continue
        df = pd.read_parquet(p, columns=['team'])
        teams.update(df['team'].map(normalize_name).tolist())
    return teams


def gameplan_teams(year: int) -> set[str]:
    d = DATA_DIR / str(year) / 'gameplan'
    if not d.exists():
        return set()
    teams = set()
    for p in d.glob('*.parquet'):
        df = pd.read_parquet(p)
        if 'team' not in df.columns or df.empty:
            continue
        teams.update(df['team'].map(normalize_name).tolist())
    return teams


def bracket_teams(year: int) -> set[str]:
    path = DATA_DIR / str(year) / 'bracket.csv'
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    raw = set(df['Team1'].tolist() + df['Team2'].tolist())
    return {normalize_name(t) for t in raw}


def main():
    print('=' * 60)
    print('Name Matching Audit')
    print('=' * 60)

    gp_not_in_scouting = {}   # gameplan team with no scouting match
    bracket_no_gameplan = {}  # tournament team with no gameplan

    for year in SCOUTING_YEARS:
        sc = scouting_teams(year)
        gp = gameplan_teams(year)
        br = bracket_teams(year)

        # Gameplan teams not in scouting
        missing_sc = sorted(gp - sc)
        if missing_sc:
            gp_not_in_scouting[year] = missing_sc

        # Tournament teams not in gameplan
        missing_gp = sorted(br - gp)
        if missing_gp:
            bracket_no_gameplan[year] = missing_gp

    # ── Report 1: gameplan → scouting mismatches ──────────────────────────────
    print('\n[1] Gameplan teams with no matching scouting parquet:')
    if not gp_not_in_scouting:
        print('    None — all gameplan teams matched.')
    else:
        total = sum(len(v) for v in gp_not_in_scouting.values())
        print(f'    {total} team-years with mismatches:')
        for year, teams in sorted(gp_not_in_scouting.items()):
            for t in teams:
                print(f'    {year}  {t!r}')

    # ── Report 2: bracket → gameplan mismatches ───────────────────────────────
    print('\n[2] Tournament teams (bracket) with no gameplan parquet:')
    if not bracket_no_gameplan:
        print('    None — all tournament teams have gameplan data.')
    else:
        total = sum(len(v) for v in bracket_no_gameplan.values())
        print(f'    {total} team-years missing gameplan:')
        for year, teams in sorted(bracket_no_gameplan.items()):
            for t in teams:
                print(f'    {year}  {t!r}')

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    bracket_issues = sum(len(v) for v in bracket_no_gameplan.values())
    if bracket_issues == 0:
        print('All tournament teams have gameplan coverage. Safe to build rolling features.')
    else:
        print(f'{bracket_issues} tournament team-years lack gameplan data.')
        print('These games will have NaN rolling features (XGBoost/HistGBM handles NaN).')


if __name__ == '__main__':
    main()
