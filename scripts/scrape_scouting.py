"""Scrape scouting reports for all teams, 2001-2026 (excludes 2020).

Per year:
  - D-I averages saved once to data/{year}/scouting/average_scouting.parquet
  - Team scouting saved to data/{year}/scouting/{slug}_scouting.parquet
"""
import random
import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gameplan import make_session
from src.scouting import fetch_team_page, parse_scouting_report, parse_d1_averages
from src.kenpom import load_all_kenpom

YEARS = list(range(2001, 2027))
YEARS.remove(2020)

LOG_PATH = Path('scrape_scouting_errors.log')

def team_slug(name: str) -> str:
    return name.replace(' ', '_').replace('.', '').replace("'", '')

def log_error(msg: str) -> None:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}\n'
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line)
    print(f'  LOGGED: {msg}')

# ── Build team-year list ──────────────────────────────────────────────────────
kp = load_all_kenpom()
kp_subset = kp[kp['Season'].isin(YEARS)]
team_years = list(kp_subset[['TeamName', 'Season']].itertuples(index=False, name=None))

print(f'Scraping {len(team_years)} team-year combinations ({min(YEARS)}-{max(YEARS)}, no 2020)...')
print(f'Error log → {LOG_PATH.resolve()}\n')

# ── Verify login ──────────────────────────────────────────────────────────────
session = make_session()
test = session.get('https://kenpom.com/summary.php')
if 'Login' in test.text or test.status_code == 403:
    print('LOGIN FAILED — make sure you are logged in to kenpom.com in Chrome.')
    sys.exit(1)
print('Login OK.\n')

log_error(f'=== Run started: {len(team_years)} team-years ===')

error_count = 0
skip_count = 0

# Track which years already have D-I averages saved
avg_saved = {
    year: (Path('data') / str(year) / 'scouting' / 'average_scouting.parquet').exists()
    for year in YEARS
}

for i, (team, year) in enumerate(team_years, 1):
    out_dir = Path('data') / str(year) / 'scouting'
    out_dir.mkdir(parents=True, exist_ok=True)
    team_path = out_dir / f'{team_slug(team)}_scouting.parquet'

    if team_path.exists() and avg_saved[year]:
        skip_count += 1
        if skip_count <= 5 or skip_count % 100 == 0:
            print(f'[{i}/{len(team_years)}] SKIP {year} {team}')
        elif skip_count == 6:
            print('  (suppressing further SKIP messages...)')
        continue

    try:
        html = fetch_team_page(session, team, year)

        if not team_path.exists():
            rec = parse_scouting_report(html, team, year)
            pd.DataFrame([rec]).to_parquet(team_path, index=False)
            print(f'[{i}/{len(team_years)}] OK   {year} {team}')
        else:
            skip_count += 1

        if not avg_saved[year]:
            avg_path = out_dir / 'average_scouting.parquet'
            avg_rec = parse_d1_averages(html, year)
            pd.DataFrame([avg_rec]).to_parquet(avg_path, index=False)
            avg_saved[year] = True

    except Exception as e:
        error_count += 1
        log_error(f'ERR {year} {team}: {e}')

    time.sleep(1.0 + random.uniform(0, 0.5))

log_error(f'=== Run finished: {error_count} errors, {skip_count} skipped ===')
print(f'\nDone. Errors: {error_count}  (see {LOG_PATH})')
