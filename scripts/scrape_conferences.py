"""Scrape team conference + season stats from Sports Reference standings pages.

URL: https://www.sports-reference.com/cbb/seasons/men/{year}-standings.html

Columns captured per team:
  team, conf, conf_abbrev, season,
  w, l, wl_pct,
  conf_w, conf_l, conf_wl_pct,
  pts_pg, opp_pts_pg,
  srs, sos,
  ncaa_tourney (bool)

Output: config/conferences.parquet
"""
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup, Comment
from pathlib import Path

YEARS = list(range(2002, 2027))
YEARS.remove(2020)

OUT_PATH = Path(__file__).resolve().parent.parent / 'config' / 'conferences.parquet'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
}

def to_float(s):
    try:
        return float(str(s).strip())
    except (ValueError, TypeError):
        return None

def to_int(s):
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return None

def scrape_year(year: int) -> list:
    url = f'https://www.sports-reference.com/cbb/seasons/men/{year}-standings.html'
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')

    # Sports Reference hides tables in HTML comments
    comments = soup.find_all(string=lambda t: isinstance(t, Comment) and '<table' in t)
    for comment in comments:
        comment.replace_with(BeautifulSoup(str(comment), 'html.parser'))

    rows = []
    for table in soup.find_all('table', id=lambda i: i and i.startswith('standings_')):
        h2 = table.find_previous('h2')
        conf_full = h2.get_text(strip=True) if h2 else ''

        # Find the header row containing 'School'
        school_idx = None
        for tr in table.find_all('tr'):
            cells = [c.get_text(strip=True) for c in tr.find_all(['th', 'td'])]
            if 'School' in cells:
                school_idx = cells.index('School')
                break
        if school_idx is None:
            continue

        for tr in table.find_all('tr'):
            tds = tr.find_all(['td', 'th'])
            if len(tds) <= school_idx:
                continue
            a = tds[school_idx].find('a')
            if not a:
                continue

            def cell(idx):
                return tds[idx].get_text(strip=True) if idx < len(tds) else ''

            notes = cell(len(tds) - 1)

            rows.append({
                'team':          a.get_text(strip=True),
                'conf':          conf_full,
                'conf_abbrev':   cell(school_idx + 1),   # Conf column right after School
                'season':        year,
                'w':             to_int(cell(school_idx + 2)),
                'l':             to_int(cell(school_idx + 3)),
                'wl_pct':        to_float(cell(school_idx + 4)),
                'conf_w':        to_int(cell(school_idx + 6)),
                'conf_l':        to_int(cell(school_idx + 7)),
                'conf_wl_pct':   to_float(cell(school_idx + 8)),
                'pts_pg':        to_float(cell(school_idx + 10)),
                'opp_pts_pg':    to_float(cell(school_idx + 11)),
                'srs':           to_float(cell(school_idx + 13)),
                'sos':           to_float(cell(school_idx + 14)),
                'ncaa_tourney':  'NCAA Tournament' in notes,
            })

    return rows


all_rows = []
for year in YEARS:
    try:
        rows = scrape_year(year)
        print(f'{year}: {len(rows)} teams')
        all_rows.extend(rows)
    except Exception as e:
        print(f'{year}: ERROR — {e}')
    time.sleep(4.0)

df = pd.DataFrame(all_rows)
df.to_parquet(OUT_PATH, index=False)
print(f'\nSaved {len(df)} rows → {OUT_PATH}')
print(df[df['season'] == 2025].head(10).to_string(index=False))
