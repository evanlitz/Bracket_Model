"""Scraper and parser for KenPom team scouting report pages.
URL pattern: https://kenpom.com/team.php?team=Iowa+St.&y=2024

Most cell values are NOT in the raw HTML td text. KenPom populates the
empty <td id="OE"> etc. cells via an inline tableStart() JavaScript function.
We extract those values by regex-parsing that <script> block directly.

A handful of rows (SOS Components, SOS Overall, Non-conference, Personnel)
ARE statically rendered and are parsed from the HTML table as usual.
"""
import re
import urllib.parse
from bs4 import BeautifulSoup


# ── JavaScript-populated cells ────────────────────────────────────────────────
# The tableStart() function in the page's <script> contains lines like:
#   $("td#OE").html("<a href=\"...\">113.9</a> <span class=\"seed\">52</span>");
# This maps td ID → column name for those cells.
_JS_TD_MAP = {
    'OE':        'adj_oe',
    'DE':        'adj_de',
    'Tempo':     'adj_tempo',
    'APLO':      'apl_off',
    'APLD':      'apl_def',
    'eFG':       'efg_pct_off',
    'DeFG':      'efg_pct_def',
    'TOPct':     'to_pct_off',
    'DTOPct':    'to_pct_def',
    'ORPct':     'or_pct_off',
    'DORPct':    'or_pct_def',
    'FTR':       'ftr_off',
    'DFTR':      'ftr_def',
    '3Pct':      'fg3_pct_off',
    'D3Pct':     'fg3_pct_def',
    '2Pct':      'fg2_pct_off',
    'D2Pct':     'fg2_pct_def',
    'FTPct':     'ft_pct_off',
    'DFTPct':    'ft_pct_def',
    'BlockPct':  'blk_pct_off',
    'DBlockPct': 'blk_pct_def',
    'StlRate':   'stl_rate_off',
    'DStlRate':  'stl_rate_def',
    'NSTRate':   'nst_rate_off',
    'DNSTRate':  'nst_rate_def',
    'ShotDist':  'shot_dist_off',
    'DShotDist': 'shot_dist_def',
    '3PARate':   'fg3a_rate_off',
    'D3PARate':  'fg3a_rate_def',
    'ARate':     'ast_rate_off',
    'DARate':    'ast_rate_def',
    'PD3':       'pd3_off',
    'DPD3':      'pd3_def',
    'PD2':       'pd2_off',
    'DPD2':      'pd2_def',
    'PD1':       'pd1_off',
    'DPD1':      'pd1_def',
}

# ── Statically rendered pair rows (4 tds) ─────────────────────────────────────
# label_fragment, off_col, def_col
_STATIC_PAIR_ROWS = [
    ('Components:', 'sos_off', 'sos_def'),   # SOS offensive / defensive
]

# ── Statically rendered single rows (3 tds) ───────────────────────────────────
# label_fragment, col
_STATIC_SINGLE_ROWS = [
    ('Overall:',            'sos_overall'),
    ('Non-conference:',     'sos_nc'),
    ('Bench Minutes:',      'bench_min'),
    ('D-1 Experience:',     'd1_exp'),
    ('Minutes Continuity:', 'min_cont'),
    ('Average Height:',     'avg_height'),
    ('2-Foul',              'foul2_pct'),   # matches '2-Foul Participation:'
]

# ── D-I average column map ────────────────────────────────────────────────────
_AVG_COL_MAP = {
    'Avg. Poss. Length':  'apl_avg',
    'Effective FG%':      'efg_pct_avg',
    'Turnover %':         'to_pct_avg',
    'Off. Reb. %':        'or_pct_avg',
    'FTA/FGA':            'ftr_avg',
    '3P%':                'fg3_pct_avg',
    '2P%':                'fg2_pct_avg',
    'FT%':                'ft_pct_avg',
    'Block%':             'blk_pct_avg',
    'Steal%':             'stl_rate_avg',
    'Non-Stl TO%':        'nst_rate_avg',
    'Avg 2PA':            'shot_dist_avg',
    '3PA/FGA':            'fg3a_rate_avg',
    'A/FGM':              'ast_rate_avg',
    '3-Pointers':         'pd3_avg',
    '2-Pointers':         'pd2_avg',
    'Free Throws':        'pd1_avg',
    'Components':         'sos_components_avg',
    'Overall':            'sos_overall_avg',
    'Non-conference':     'sos_nc_avg',
    'Bench Minutes':      'bench_min_avg',
    'D-1 Experience':     'd1_exp_avg',
    'Minutes Continuity': 'min_cont_avg',
    'Average Height':     'avg_height_avg',
    '2-Foul':             'foul2_pct_avg',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _player_cell_val(td) -> str:
    """Get the stat value from a player-table td, ignoring plrank rank spans."""
    return ''.join(td.find_all(string=True, recursive=False)).strip()


def _parse(s):
    """Convert '52.0%', '77.5"', '2.11 yrs', '+10.43' → float or None."""
    if not s:
        return None
    s = str(s).strip().rstrip('%"').replace(' yrs', '')
    try:
        return float(s)
    except ValueError:
        return None


def _cell(td) -> tuple:
    """Extract (value_float_or_None, rank_int_or_None) from a report-table td."""
    if td is None:
        return None, None
    a = td.find('a')
    raw = a.get_text(strip=True) if a else td.get_text(strip=True)
    seed = td.find('span', class_='seed')
    rank_text = seed.get_text(strip=True) if seed else ''
    rank = int(rank_text) if rank_text.isdigit() else None
    return _parse(raw), rank


def _row_tds(table, label_fragment: str) -> list:
    """Return tds for the first row whose first td contains label_fragment."""
    for tr in table.find_all('tr'):
        tds = tr.find_all('td')
        if tds and label_fragment in tds[0].get_text():
            return tds
    return []


def _parse_table_start(html: str) -> dict:
    """Extract JS-populated cell values from the inline tableStart() function.

    Returns {col_name: (value_float, rank_int_or_None)} for all JS cells.
    The function body contains lines like:
      $("td#OE").html("<a href=\\"...\">113.9</a> <span class=\\"seed\\">52</span>");
    """
    match = re.search(r'function tableStart\(\)\s*\{(.*?)\n\}', html, re.DOTALL)
    if not match:
        return {}

    body = match.group(1)
    # Match: $("td#ID").html("...JS-escaped HTML...");
    pattern = r'\$\("td#(\w+)"\)\.html\("((?:[^"\\]|\\.)*)"\)'

    result = {}
    for td_id, escaped_html in re.findall(pattern, body):
        if td_id not in _JS_TD_MAP:
            continue
        col = _JS_TD_MAP[td_id]
        actual_html = escaped_html.replace('\\"', '"')
        cell_soup = BeautifulSoup(actual_html, 'html.parser')
        a = cell_soup.find('a')
        raw = a.get_text(strip=True) if a else cell_soup.get_text(strip=True)
        seed = cell_soup.find('span', class_='seed')
        rank_text = seed.get_text(strip=True) if seed else ''
        rank = int(rank_text) if rank_text.isdigit() else None
        result[col] = (_parse(raw), rank)

    return result


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_scouting_report(html: str, team: str, year: int) -> dict:
    """Parse a team.php HTML string into a flat feature dict.

    JS-populated stats (adj efficiency, tempo, four factors, style, point
    distribution) come from the inline tableStart() script block.
    SOS and Personnel rows are parsed from the static HTML table.
    Missing fields are set to None.
    """
    rec: dict = {'team': team, 'season': year}

    # ── JS-populated stats ────────────────────────────────────────────────────
    js_vals = _parse_table_start(html)
    for col, (val, rank) in js_vals.items():
        rec[col] = val
        rec[f'{col}_rank'] = rank

    # Ensure every JS col is present even if tableStart() parsing missed it
    for col in _JS_TD_MAP.values():
        if col not in rec:
            rec[col] = None
            rec[f'{col}_rank'] = None

    # ── Statically rendered rows ──────────────────────────────────────────────
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='report-table')
    if table is None:
        raise ValueError(f'report-table not found for {team} {year}')

    for label, off_col, def_col in _STATIC_PAIR_ROWS:
        tds = _row_tds(table, label)
        if len(tds) >= 4:
            val, rank = _cell(tds[1])
            rec[off_col] = val
            rec[f'{off_col}_rank'] = rank
            val, rank = _cell(tds[2])
            rec[def_col] = val
            rec[f'{def_col}_rank'] = rank
        else:
            rec[off_col] = None;       rec[f'{off_col}_rank'] = None
            rec[def_col] = None;       rec[f'{def_col}_rank'] = None

    for label, col in _STATIC_SINGLE_ROWS:
        tds = _row_tds(table, label)
        if len(tds) >= 2:
            val, rank = _cell(tds[1])
            rec[col] = val
            rec[f'{col}_rank'] = rank
        else:
            rec[col] = None
            rec[f'{col}_rank'] = None

    return rec


def parse_d1_averages(html: str, year: int) -> dict:
    """Extract the D-I Average column from a team.php page.

    The D-I avg is the same for every team in a given year — only needs
    to be scraped once per year from any team's page.
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='report-table')
    if table is None:
        raise ValueError('report-table not found')

    rec: dict = {'season': year}

    for tr in table.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) < 2:
            continue
        if 'label' in (tds[0].get('class') or []):
            continue  # skip section headers

        label = tds[0].get_text(strip=True)
        avg_val = _parse(tds[-1].get_text(strip=True))

        for fragment, col in _AVG_COL_MAP.items():
            if fragment in label:
                rec[col] = avg_val
                break

    return rec


def parse_player_table(html: str, team: str, year: int) -> list:
    """Parse all player rows from the player-table on a team.php page.

    Returns a list of dicts (one per player), all tiers combined.
    %Min can be used to filter by playing time.  National ranks from
    <span class="plrank"> are stripped from stat values.
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='player-table')
    if table is None:
        return []

    def to_float(s):
        s = str(s).strip().lstrip('.').rstrip('%"')
        # restore leading decimal that was stripped (e.g. '.728' → '0.728')
        try:
            return float('0.' + s) if s and '.' not in s and len(s) <= 3 else float(s or 'x')
        except ValueError:
            return None

    def to_int(s):
        try:
            return int(str(s).strip())
        except ValueError:
            return None

    def parse_pct(s):
        """Handle both '77.7' and '.728' style floats."""
        s = str(s).strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def parse_ma(s):
        """Parse '147-202' → (147, 202), returns (None, None) on failure."""
        parts = str(s).split('-')
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                pass
        return None, None

    # Detect layout: 2014+ has a 'S' (starts) column; 2002-2013 does not.
    # With starts: 28 tds/row.  Without: 27 tds/row, indices shift by -1 after G.
    has_starts = table.find('th', class_='S') is not None
    s = 1 if has_starts else 0   # index offset for every column after G

    players = []
    for tr in table.find_all('tr'):
        tr_class = tr.get('class', [])
        if 'label' in tr_class:
            continue  # tier header rows
        if 'player' not in tr_class and 'benchwarmer' not in tr_class:
            continue  # thead etc.

        tds = tr.find_all('td')
        if len(tds) < 27 + s:
            continue

        name_td = tds[1]
        name_a = name_td.find('a')
        name = name_a.get_text(strip=True) if name_a else ''
        starter = name_td.find('b') is not None

        ftm,  fta  = parse_ma(_player_cell_val(tds[21 + s]))
        fg2m, fg2a = parse_ma(_player_cell_val(tds[23 + s]))
        fg3m, fg3a = parse_ma(_player_cell_val(tds[25 + s]))

        players.append({
            'team':      team,
            'season':    year,
            'jersey':    to_int(_player_cell_val(tds[0])),
            'name':      name,
            'starter':   starter,
            'height':    _player_cell_val(tds[2]),
            'weight':    to_int(_player_cell_val(tds[3])),
            'year':      _player_cell_val(tds[4]),
            'games':     to_int(_player_cell_val(tds[5])),
            'starts':    to_int(_player_cell_val(tds[6])) if has_starts else None,
            'pct_min':   parse_pct(_player_cell_val(tds[6  + s])),
            'ortg':      parse_pct(_player_cell_val(tds[7  + s])),
            'pct_poss':  parse_pct(_player_cell_val(tds[8  + s])),
            'pct_shots': parse_pct(_player_cell_val(tds[9  + s])),
            'efg_pct':   parse_pct(_player_cell_val(tds[10 + s])),
            'ts_pct':    parse_pct(_player_cell_val(tds[11 + s])),
            'or_pct':    parse_pct(_player_cell_val(tds[12 + s])),
            'dr_pct':    parse_pct(_player_cell_val(tds[13 + s])),
            'a_rate':    parse_pct(_player_cell_val(tds[14 + s])),
            'to_rate':   parse_pct(_player_cell_val(tds[15 + s])),
            'blk_pct':   parse_pct(_player_cell_val(tds[16 + s])),
            'stl_pct':   parse_pct(_player_cell_val(tds[17 + s])),
            'fc_per40':  parse_pct(_player_cell_val(tds[18 + s])),
            'fd_per40':  parse_pct(_player_cell_val(tds[19 + s])),
            'ft_rate':   parse_pct(_player_cell_val(tds[20 + s])),
            'ftm':       ftm,
            'fta':       fta,
            'ft_pct':    parse_pct(_player_cell_val(tds[22 + s])),
            'fg2m':      fg2m,
            'fg2a':      fg2a,
            'fg2_pct':   parse_pct(_player_cell_val(tds[24 + s])),
            'fg3m':      fg3m,
            'fg3a':      fg3a,
            'fg3_pct':   parse_pct(_player_cell_val(tds[26 + s])),
        })

    return players


# ── Network ───────────────────────────────────────────────────────────────────

def fetch_team_page(session, team: str, year: int) -> str:
    """Fetch raw HTML for a KenPom team page (team.php)."""
    url = f'https://kenpom.com/team.php?team={urllib.parse.quote(team)}&y={year}'
    r = session.get(url)
    r.raise_for_status()
    return r.text


def fetch_scouting_report(session, team: str, year: int) -> dict:
    """Fetch and parse team scouting stats only (no D-I avg)."""
    return parse_scouting_report(fetch_team_page(session, team, year), team, year)
