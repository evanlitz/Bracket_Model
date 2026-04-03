"""Scrape game-by-game data for all teams, 2001-2026 (excludes 2020), and save each to parquet."""
import random
import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gameplan import make_session, fetch_gameplan
from src.kenpom import load_all_kenpom

YEARS = list(range(2001, 2027))   # 2001-2026 inclusive
YEARS.remove(2020)                # no season in 2020

LOG_PATH = Path('scrape_errors.log')

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

# ── Log run start ─────────────────────────────────────────────────────────────
log_error(f'=== Run started: {len(team_years)} team-years ===')

error_count = 0
skip_count = 0

for i, (team, year) in enumerate(team_years, 1):
    out_dir = Path('data') / str(year) / 'gameplan'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{team_slug(team)}_gameplan.parquet'

    if out_path.exists():
        skip_count += 1
        if skip_count <= 5 or skip_count % 50 == 0:
            print(f'[{i}/{len(team_years)}] SKIP {year} {team}')
        elif skip_count == 6:
            print('  (suppressing further SKIP messages...)')
        continue

    try:
        df = fetch_gameplan(session, team, year)
        df.to_parquet(out_path, index=False)
        print(f'[{i}/{len(team_years)}] OK   {year} {team}  ({len(df)} rows)')
    except Exception as e:
        error_count += 1
        log_error(f'ERR {year} {team}: {e}')

    time.sleep(1.0 + random.uniform(0, 0.5))

log_error(f'=== Run finished: {error_count} errors, {skip_count} skipped ===')
print(f'\nDone. Errors: {error_count}  (see {LOG_PATH})')
