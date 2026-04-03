"""Scrape per-school coaching history from Sports-Reference.

For each school in SCHOOL_IDS, fetches:
    https://www.sports-reference.com/cbb/schools/{school_id}/men/coaches.html

Parses the coaching history table and saves raw records to:
    data/coaches_raw/{school_id}.json

Each record contains:
    name, year_from, year_to, g, w, l, ncaa_apps, ff, nc

Run from project root:
    python scripts/scrape_coaches.py              # scrape all, skip cached
    python scripts/scrape_coaches.py --force      # re-fetch even if cached
    python scripts/scrape_coaches.py --school duke # single school
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Comment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA_DIR      = Path(__file__).resolve().parent.parent / 'data'
RAW_DIR       = DATA_DIR / 'coaches_raw'
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL      = 'https://www.sports-reference.com/cbb/schools/{school_id}/men/coaches.html'
DELAY_SECONDS = 3   # be polite — SR will 429 you if you hammer it

# Sports-Reference school IDs for every program that made the NCAA tournament
# at least once between 2002 and 2026.
SCHOOL_IDS = [
    'air-force', 'akron', 'alabama', 'alabama-am', 'alabama-birmingham',
    'appalachian-state', 'arizona', 'arizona-state', 'arkansas',
    'arkansas-little-rock', 'arkansas-pine-bluff', 'army', 'auburn',
    'austin-peay', 'ball-state', 'baylor', 'belmont', 'bethune-cookman',
    'boise-state', 'boston-college', 'boston-university', 'bradley',
    'brigham-young', 'brown', 'bucknell', 'buffalo', 'butler',
    'cal-state-bakersfield', 'cal-state-fullerton', 'cal-state-northridge',
    'california', 'campbell', 'canisius', 'central-arkansas',
    'central-connecticut-state', 'central-florida', 'central-michigan',
    'charleston-southern', 'chattanooga', 'cincinnati', 'clemson',
    'cleveland-state', 'coastal-carolina', 'colgate', 'college-of-charleston',
    'colorado', 'colorado-state', 'columbia', 'connecticut', 'coppin-state',
    'cornell', 'creighton', 'dartmouth', 'davidson', 'dayton', 'depaul',
    'drake', 'drexel', 'duke', 'duquesne', 'east-carolina', 'east-tennessee-state',
    'eastern-illinois', 'eastern-kentucky', 'eastern-michigan',
    'eastern-washington', 'evansville', 'fairfield', 'fairleigh-dickinson',
    'florida', 'florida-am', 'florida-atlantic', 'florida-gulf-coast',
    'florida-international', 'florida-state', 'fordham', 'fresno-state',
    'furman', 'gardner-webb', 'george-mason', 'george-washington', 'georgetown',
    'georgia', 'georgia-state', 'georgia-tech', 'gonzaga', 'grambling',
    'grand-canyon', 'green-bay', 'hampton', 'hartford', 'harvard',
    'hawaii', 'high-point', 'hofstra', 'holy-cross', 'houston',
    'houston-baptist', 'howard', 'idaho', 'idaho-state', 'illinois',
    'illinois-chicago', 'illinois-state', 'indiana', 'indiana-state',
    'iona', 'iowa', 'iowa-state', 'jackson-state', 'jacksonville',
    'jacksonville-state', 'james-madison', 'kansas', 'kansas-state',
    'kennesaw-state', 'kent-state', 'kentucky', 'la-salle', 'lafayette',
    'lamar', 'lehigh', 'liberty', 'lipscomb', 'long-beach-state',
    'long-island-university', 'longwood', 'louisiana-lafayette',
    'louisiana-monroe', 'louisiana-state', 'louisiana-tech', 'louisville',
    'loyola-il', 'loyola-md', 'loyola-marymount', 'maine', 'manhattan',
    'marist', 'marquette', 'marshall', 'maryland', 'maryland-eastern-shore',
    'massachusetts', 'mcneese-state', 'memphis', 'mercer', 'miami-fl',
    'miami-oh', 'michigan', 'michigan-state', 'middle-tennessee',
    'minnesota', 'mississippi', 'mississippi-state', 'mississippi-valley-state',
    'missouri', 'missouri-kansas-city', 'missouri-state', 'monmouth',
    'montana', 'montana-state', 'morehead-state', 'morgan-state',
    'mount-st-marys', 'murray-state', 'navy', 'nebraska', 'nevada',
    'nevada-las-vegas', 'new-mexico', 'new-mexico-state', 'new-orleans',
    'niagara', 'nicholls-state', 'norfolk-state', 'north-carolina',
    'north-carolina-asheville', 'north-carolina-central',
    'north-carolina-greensboro', 'north-carolina-state', 'north-carolina-wilmington',
    'north-dakota', 'north-dakota-state', 'north-florida', 'north-texas',
    'northeastern', 'northern-arizona', 'northern-colorado', 'northern-illinois',
    'northern-iowa', 'northern-kentucky', 'northwestern', 'northwestern-state',
    'notre-dame', 'oakland', 'ohio', 'ohio-state', 'oklahoma',
    'oklahoma-state', 'old-dominion', 'oral-roberts', 'oregon',
    'oregon-state', 'pacific', 'penn-state', 'pennsylvania', 'pepperdine',
    'pittsburgh', 'portland', 'portland-state', 'prairie-view',
    'presbyterian', 'princeton', 'providence', 'purdue', 'ipfw',
    'quinnipiac', 'radford', 'richmond', 'rider', 'robert-morris',
    'rutgers', 'sacred-heart', 'saint-josephs', 'saint-louis',
    'saint-marys-ca', 'saint-peters', 'sam-houston-state', 'samford',
    'san-diego', 'san-diego-state', 'san-francisco', 'san-jose-state',
    'california-santa-barbara', 'seattle', 'seton-hall', 'siena', 'south-carolina',
    'south-carolina-state', 'south-dakota', 'south-dakota-state',
    'south-florida', 'southeastern-louisiana', 'southern-california',
    'southern-illinois', 'southern-methodist', 'southern-mississippi',
    'southern', 'southern-utah', 'st-bonaventure',
    'st-francis-ny', 'saint-francis-pa', 'st-johns-ny', 'stanford',
    'stephen-f-austin', 'stetson', 'stony-brook', 'syracuse',
    'temple', 'tennessee', 'tennessee-martin', 'tennessee-state',
    'tennessee-tech', 'texas', 'texas-am', 'texas-am-corpus-christi',
    'texas-christian', 'texas-san-antonio', 'texas-southern',
    'texas-state', 'texas-tech', 'toledo', 'towson', 'troy',
    'tulane', 'tulsa', 'ucla', 'north-carolina-wilmington', 'utah',
    'utah-state', 'utah-valley', 'valparaiso', 'vanderbilt',
    'vermont', 'villanova', 'virginia', 'virginia-commonwealth',
    'virginia-military-institute', 'virginia-tech', 'wagner',
    'wake-forest', 'washington', 'washington-state', 'weber-state',
    'west-virginia', 'western-carolina', 'western-illinois',
    'western-kentucky', 'western-michigan', 'wichita-state',
    'william-mary', 'winthrop', 'wisconsin', 'wofford', 'wright-state',
    'wyoming', 'xavier', 'yale',
]


# ── Parsing ────────────────────────────────────────────────────────────────────

def _int(val: str) -> int | None:
    """Parse integer from a cell string; return None if empty or non-numeric."""
    v = val.strip()
    if not v or v == '':
        return None
    try:
        return int(v.replace(',', ''))
    except ValueError:
        return None


def _find_coaches_table(soup: BeautifulSoup):
    """Find the coaches table, including when Sports-Reference hides it in a comment."""
    # First try: directly in the DOM
    table = soup.find('table', id='coaches')
    if table:
        return table

    # Second try: SR sometimes wraps tables in HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if 'id="coaches"' in comment:
            inner = BeautifulSoup(comment, 'html.parser')
            table = inner.find('table', id='coaches')
            if table:
                return table

    return None


def parse_coaches_table(html: str, school_id: str) -> list[dict]:
    """Parse the coaching history table from a school's coaches page HTML.

    Returns a list of coach records:
        name, year_from, year_to, g, w, l, ncaa_apps, ff, nc
    """
    soup  = BeautifulSoup(html, 'html.parser')
    table = _find_coaches_table(soup)

    if table is None:
        print(f'  [warn] no coaches table found for {school_id}')
        return []

    # Map header text → column index
    headers = [th.get_text(strip=True) for th in table.select('thead tr th')]
    col = {h: i for i, h in enumerate(headers)}

    records = []
    for tr in table.select('tbody tr'):
        # Skip spacer/filler rows
        if 'class' in tr.attrs and any(c in tr['class'] for c in ('thead', 'partial_table')):
            continue
        cells = tr.find_all(['td', 'th'])
        if not cells:
            continue

        def cell(name: str) -> str:
            idx = col.get(name)
            if idx is None or idx >= len(cells):
                return ''
            return cells[idx].get_text(strip=True)

        name = cell('Coach')
        if not name or name == 'Coach':   # skip header rows embedded in tbody
            continue

        records.append({
            'name':      name,
            'year_from': _int(cell('From')),
            'year_to':   _int(cell('To')),
            'g':         _int(cell('G')),
            'w':         _int(cell('W')),
            'l':         _int(cell('L')),
            'ncaa_apps': _int(cell('NCAA')),
            'ff':        _int(cell('FF')),
            'nc':        _int(cell('NC')),
        })

    return records


# ── Fetcher ────────────────────────────────────────────────────────────────────

def fetch_school(school_id: str, force: bool = False) -> list[dict] | None:
    """Fetch and parse coaching history for one school.

    Returns parsed records, or None on HTTP error.
    Caches raw HTML to data/coaches_raw/{school_id}.html to avoid re-fetching.
    """
    cache_html  = RAW_DIR / f'{school_id}.html'
    output_json = RAW_DIR / f'{school_id}.json'

    # Use cached HTML if available and not forcing
    if cache_html.exists() and not force:
        html = cache_html.read_text(encoding='utf-8')
    else:
        url = BASE_URL.format(school_id=school_id)
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        except requests.RequestException as e:
            print(f'  [error] {school_id}: {e}')
            return None

        if resp.status_code == 404:
            print(f'  [404] {school_id} — check school ID spelling')
            return None
        if resp.status_code == 429:
            print(f'  [429] rate-limited on {school_id} — increase DELAY_SECONDS')
            return None
        if resp.status_code != 200:
            print(f'  [HTTP {resp.status_code}] {school_id}')
            return None

        html = resp.text
        cache_html.write_text(html, encoding='utf-8')

    records = parse_coaches_table(html, school_id)

    if records:
        output_json.write_text(
            json.dumps({'school_id': school_id, 'coaches': records}, indent=2),
            encoding='utf-8',
        )

    return records


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Scrape coaching history from Sports-Reference.')
    parser.add_argument('--force',  action='store_true', help='Re-fetch even if HTML is cached')
    parser.add_argument('--school', default=None,        help='Scrape a single school ID only')
    args = parser.parse_args()

    schools = [args.school] if args.school else SCHOOL_IDS

    ok, warn, err = 0, 0, 0
    for i, school_id in enumerate(schools):
        out_path = RAW_DIR / f'{school_id}.json'
        if out_path.exists() and not args.force:
            print(f'[{i+1}/{len(schools)}] {school_id} — cached, skipping')
            ok += 1
            continue

        print(f'[{i+1}/{len(schools)}] {school_id}...', end=' ', flush=True)
        records = fetch_school(school_id, force=args.force)

        if records is None:
            err += 1
        elif not records:
            print(f'0 coaches parsed')
            warn += 1
        else:
            print(f'{len(records)} coaches')
            ok += 1

        if i < len(schools) - 1:
            time.sleep(DELAY_SECONDS)

    print(f'\nDone: {ok} ok, {warn} warnings, {err} errors')
    print(f'Output: {RAW_DIR}')


if __name__ == '__main__':
    main()
