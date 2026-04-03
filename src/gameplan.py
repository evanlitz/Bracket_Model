"""Scraper and parser for KenPom game-plan (schedule) pages.

URL pattern: https://kenpom.com/gameplan.php?team=Maryland&y=2013

Each row in the schedule-table contains per-game efficiency, four-factor,
and shooting stats for both the team and its opponent.
"""
import json
import re
import urllib.parse
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

_COOKIES_PATH = Path(__file__).resolve().parent.parent / 'cookies.json'

# ── Columns in order of appearance in the schedule-table ─────────────────────
# Matches gameplan_features.py expectations and data/rules reference.
_COLUMNS = [
    'team', 'year', 'date', 'opp_kp_rank', 'opponent',
    'outcome', 'team_score', 'opp_score', 'location', 'pace',
    'off_eff', 'off_eff_rank',
    'off_efg', 'off_to_pct', 'off_or_pct', 'off_ftr',
    'fg2_made', 'fg2_att', 'fg2_pct',
    'fg3_made', 'fg3_att', 'fg3_pct',
    'fg3a_rate',
    'def_eff', 'def_eff_rank',
    'def_efg', 'def_to_pct', 'def_or_pct', 'def_ftr',
    'def_fg2_made', 'def_fg2_att', 'def_fg2_pct',
    'def_fg3_made', 'def_fg3_att', 'def_fg3_pct',
    'def_fg3a_rate',
]


# ── Session ───────────────────────────────────────────────────────────────────

def make_session():
    """Return a curl_cffi session pre-loaded with KenPom cookies."""
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate='chrome142')

    if _COOKIES_PATH.exists():
        cookies = json.loads(_COOKIES_PATH.read_text())
        for ck in cookies:
            session.cookies.set(
                ck['name'],
                ck['value'],
                domain=ck.get('domain', 'kenpom.com'),
            )

    return session


# ── Helpers ───────────────────────────────────────────────────────────────────

def _float(text: str):
    """Parse a float or return None."""
    if not text:
        return None
    text = text.strip()
    if not text or text == '-':
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int(text: str):
    """Parse an int or return None."""
    if not text:
        return None
    text = text.strip()
    try:
        return int(text)
    except ValueError:
        return None


def _split_made_att(text: str):
    """Parse 'made-att' string like '19-35' -> (19, 35)."""
    m = re.match(r'(\d+)-(\d+)', text.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _parse_result(text: str):
    """Parse 'W, 67-45' or 'L, 72-69' -> (outcome, team_score, opp_score)."""
    m = re.match(r'([WL]),\s*(\d+)-(\d+)', text.strip())
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return None, None, None


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_gameplan(html: str, team: str, year: int) -> pd.DataFrame:
    """Parse the schedule-table from a gameplan.php HTML page.

    Returns a DataFrame with one row per game. Non-game rows (correlations,
    averages) are skipped. Only rows with tr class 'w' or 'l' are parsed.
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='schedule-table')
    if table is None:
        raise ValueError(f'schedule-table not found for {team} {year}')

    rows = []
    for tr in table.find_all('tr'):
        cls = tr.get('class', [])
        if not cls or cls[0] not in ('w', 'l'):
            continue

        tds = tr.find_all('td')
        if len(tds) < 28:
            continue

        # td[0] date
        date = tds[0].get_text(strip=True)

        # td[1] opponent KP rank (inside <span class="seed">)
        seed_span = tds[1].find('span', class_='seed')
        opp_kp_rank = _int(seed_span.get_text(strip=True)) if seed_span else None

        # td[2] opponent name
        opp_link = tds[2].find('a')
        opponent = opp_link.get_text(strip=True) if opp_link else tds[2].get_text(strip=True)

        # td[3] result: "W, 67-45"
        result_text = tds[3].get_text(' ', strip=True)
        outcome, team_score, opp_score = _parse_result(result_text)

        # td[4] location
        location = tds[4].get_text(strip=True)

        # td[5] pace
        pace = _float(tds[5].get_text(strip=True))

        # td[6] off_eff, td[7] off_eff_rank
        off_eff      = _float(tds[6].get_text(strip=True))
        off_eff_rank = _int(tds[7].get_text(strip=True))

        # td[8] off_efg, td[9] off_to_pct, td[10] off_or_pct, td[11] off_ftr
        off_efg    = _float(tds[8].get_text(strip=True))
        off_to_pct = _float(tds[9].get_text(strip=True))
        off_or_pct = _float(tds[10].get_text(strip=True))
        off_ftr    = _float(tds[11].get_text(strip=True))

        # td[12] fg2 made-att, td[13] fg2_pct
        fg2_made, fg2_att = _split_made_att(tds[12].get_text(strip=True))
        fg2_pct = _float(tds[13].get_text(strip=True))

        # td[14] fg3 made-att, td[15] fg3_pct
        fg3_made, fg3_att = _split_made_att(tds[14].get_text(strip=True))
        fg3_pct = _float(tds[15].get_text(strip=True))

        # td[16] fg3a_rate (3PA%)
        fg3a_rate = _float(tds[16].get_text(strip=True))

        # td[17] def_eff, td[18] def_eff_rank
        def_eff      = _float(tds[17].get_text(strip=True))
        def_eff_rank = _int(tds[18].get_text(strip=True))

        # td[19] def_efg, td[20] def_to_pct, td[21] def_or_pct, td[22] def_ftr
        def_efg    = _float(tds[19].get_text(strip=True))
        def_to_pct = _float(tds[20].get_text(strip=True))
        def_or_pct = _float(tds[21].get_text(strip=True))
        def_ftr    = _float(tds[22].get_text(strip=True))

        # td[23] def_fg2 made-att, td[24] def_fg2_pct
        def_fg2_made, def_fg2_att = _split_made_att(tds[23].get_text(strip=True))
        def_fg2_pct = _float(tds[24].get_text(strip=True))

        # td[25] def_fg3 made-att, td[26] def_fg3_pct
        def_fg3_made, def_fg3_att = _split_made_att(tds[25].get_text(strip=True))
        def_fg3_pct = _float(tds[26].get_text(strip=True))

        # td[27] def_fg3a_rate (opponent 3PA%)
        def_fg3a_rate = _float(tds[27].get_text(strip=True))

        rows.append({
            'team':          team,
            'year':          year,
            'date':          date,
            'opp_kp_rank':   opp_kp_rank,
            'opponent':      opponent,
            'outcome':       outcome,
            'team_score':    team_score,
            'opp_score':     opp_score,
            'location':      location,
            'pace':          pace,
            'off_eff':       off_eff,
            'off_eff_rank':  off_eff_rank,
            'off_efg':       off_efg,
            'off_to_pct':    off_to_pct,
            'off_or_pct':    off_or_pct,
            'off_ftr':       off_ftr,
            'fg2_made':      fg2_made,
            'fg2_att':       fg2_att,
            'fg2_pct':       fg2_pct,
            'fg3_made':      fg3_made,
            'fg3_att':       fg3_att,
            'fg3_pct':       fg3_pct,
            'fg3a_rate':     fg3a_rate,
            'def_eff':       def_eff,
            'def_eff_rank':  def_eff_rank,
            'def_efg':       def_efg,
            'def_to_pct':    def_to_pct,
            'def_or_pct':    def_or_pct,
            'def_ftr':       def_ftr,
            'def_fg2_made':  def_fg2_made,
            'def_fg2_att':   def_fg2_att,
            'def_fg2_pct':   def_fg2_pct,
            'def_fg3_made':  def_fg3_made,
            'def_fg3_att':   def_fg3_att,
            'def_fg3_pct':   def_fg3_pct,
            'def_fg3a_rate': def_fg3a_rate,
        })

    return pd.DataFrame(rows, columns=_COLUMNS)


# ── Network ───────────────────────────────────────────────────────────────────

def fetch_gameplan(session, team: str, year: int) -> pd.DataFrame:
    """Fetch and parse the KenPom gameplan page for one team-season."""
    url = f'https://kenpom.com/gameplan.php?team={urllib.parse.quote(team)}&y={year}'
    r = session.get(url)
    r.raise_for_status()
    return parse_gameplan(r.text, team, year)
