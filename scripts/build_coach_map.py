"""Build team->coach->year mapping from scraped coaching history.

Reads:  data/coaches_raw/{school_id}.json  (one per school)
Writes: config/team_coaches.json
    {
      "Iowa St.": {"2002": "Larry Eustachy", "2003": "Larry Eustachy", ...},
      ...
    }

Keys are canonical KenPom team names (same as used everywhere else in the
pipeline). Values are coach names exactly as they appear on Sports-Reference.

Run from project root:
    python scripts/build_coach_map.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA_DIR   = Path(__file__).resolve().parent.parent / 'data'
CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'
RAW_DIR    = DATA_DIR / 'coaches_raw'
OUT_PATH   = CONFIG_DIR / 'team_coaches.json'

# Only expand years in this range — earlier years are irrelevant to features
YEAR_MIN = 1960   # need pre-2002 history for career cumulative stats
YEAR_MAX = 2026

# ── SR school ID -> canonical KenPom team name ─────────────────────────────────
# Canonical names must match what normalize_name() resolves to in src/names.py.
SR_TO_NORMALIZED = {
    'air-force':                  'Air Force',
    'akron':                      'Akron',
    'alabama':                    'Alabama',
    'alabama-am':                 'Alabama A&M',
    'alabama-birmingham':         'UAB',
    'appalachian-state':          'Appalachian St.',
    'arizona':                    'Arizona',
    'arizona-state':              'Arizona St.',
    'arkansas':                   'Arkansas',
    'arkansas-little-rock':       'Little Rock',
    'arkansas-pine-bluff':        'Arkansas Pine Bluff',
    'army':                       'Army',
    'auburn':                     'Auburn',
    'austin-peay':                'Austin Peay',
    'ball-state':                 'Ball St.',
    'baylor':                     'Baylor',
    'belmont':                    'Belmont',
    'bethune-cookman':            'Bethune Cookman',
    'boise-state':                'Boise St.',
    'boston-college':             'Boston College',
    'boston-university':          'Boston University',
    'bradley':                    'Bradley',
    'brigham-young':              'BYU',
    'brown':                      'Brown',
    'bucknell':                   'Bucknell',
    'buffalo':                    'Buffalo',
    'butler':                     'Butler',
    'cal-state-bakersfield':      'Cal St. Bakersfield',
    'cal-state-fullerton':        'Cal St. Fullerton',
    'cal-state-northridge':       'Cal St. Northridge',
    'california':                 'California',
    'california-santa-barbara':   'UC Santa Barbara',
    'campbell':                   'Campbell',
    'canisius':                   'Canisius',
    'central-arkansas':           'Central Arkansas',
    'central-connecticut-state':  'Central Connecticut',
    'central-florida':            'UCF',
    'central-michigan':           'Central Michigan',
    'charleston-southern':        'Charleston Southern',
    'chattanooga':                'Chattanooga',
    'cincinnati':                 'Cincinnati',
    'clemson':                    'Clemson',
    'cleveland-state':            'Cleveland St.',
    'coastal-carolina':           'Coastal Carolina',
    'colgate':                    'Colgate',
    'college-of-charleston':      'Charleston',
    'colorado':                   'Colorado',
    'colorado-state':             'Colorado St.',
    'columbia':                   'Columbia',
    'connecticut':                'Connecticut',
    'coppin-state':               'Coppin St.',
    'cornell':                    'Cornell',
    'creighton':                  'Creighton',
    'dartmouth':                  'Dartmouth',
    'davidson':                   'Davidson',
    'dayton':                     'Dayton',
    'depaul':                     'DePaul',
    'drake':                      'Drake',
    'drexel':                     'Drexel',
    'duke':                       'Duke',
    'duquesne':                   'Duquesne',
    'east-carolina':              'East Carolina',
    'east-tennessee-state':       'East Tennessee St.',
    'eastern-illinois':           'Eastern Illinois',
    'eastern-kentucky':           'Eastern Kentucky',
    'eastern-michigan':           'Eastern Michigan',
    'eastern-washington':         'Eastern Washington',
    'evansville':                 'Evansville',
    'fairfield':                  'Fairfield',
    'fairleigh-dickinson':        'Fairleigh Dickinson',
    'florida':                    'Florida',
    'florida-am':                 'Florida A&M',
    'florida-atlantic':           'Florida Atlantic',
    'florida-gulf-coast':         'Florida Gulf Coast',
    'florida-international':      'FIU',
    'florida-state':              'Florida St.',
    'fordham':                    'Fordham',
    'fresno-state':               'Fresno St.',
    'furman':                     'Furman',
    'gardner-webb':               'Gardner Webb',
    'george-mason':               'George Mason',
    'george-washington':          'George Washington',
    'georgetown':                 'Georgetown',
    'georgia':                    'Georgia',
    'georgia-state':              'Georgia St.',
    'georgia-tech':               'Georgia Tech',
    'gonzaga':                    'Gonzaga',
    'grambling':                  'Grambling St.',
    'grand-canyon':               'Grand Canyon',
    'green-bay':                  'Green Bay',
    'hampton':                    'Hampton',
    'hartford':                   'Hartford',
    'harvard':                    'Harvard',
    'hawaii':                     'Hawaii',
    'high-point':                 'High Point',
    'hofstra':                    'Hofstra',
    'holy-cross':                 'Holy Cross',
    'houston':                    'Houston',
    'houston-baptist':            'Houston Christian',
    'howard':                     'Howard',
    'idaho':                      'Idaho',
    'idaho-state':                'Idaho St.',
    'illinois':                   'Illinois',
    'illinois-chicago':           'Illinois Chicago',
    'illinois-state':             'Illinois St.',
    'indiana':                    'Indiana',
    'indiana-state':              'Indiana St.',
    'iona':                       'Iona',
    'iowa':                       'Iowa',
    'iowa-state':                 'Iowa St.',
    'ipfw':                       'IPFW',  # split into IPFW (≤2018) / Purdue Fort Wayne (≥2019) below
    'jackson-state':              'Jackson St.',
    'jacksonville':               'Jacksonville',
    'jacksonville-state':         'Jacksonville St.',
    'james-madison':              'James Madison',
    'kansas':                     'Kansas',
    'kansas-state':               'Kansas St.',
    'kennesaw-state':             'Kennesaw St.',
    'kent-state':                 'Kent St.',
    'kentucky':                   'Kentucky',
    'la-salle':                   'La Salle',
    'lafayette':                  'Lafayette',
    'lamar':                      'Lamar',
    'lehigh':                     'Lehigh',
    'liberty':                    'Liberty',
    'lipscomb':                   'Lipscomb',
    'long-beach-state':           'Long Beach St.',
    'long-island-university':     'LIU',
    'longwood':                   'Longwood',
    'louisiana-lafayette':        'Louisiana',
    'louisiana-monroe':           'Louisiana Monroe',
    'louisiana-state':            'LSU',
    'louisiana-tech':             'Louisiana Tech',
    'louisville':                 'Louisville',
    'loyola-il':                  'Loyola Chicago',
    'loyola-md':                  'Loyola MD',
    'loyola-marymount':           'Loyola Marymount',
    'maine':                      'Maine',
    'manhattan':                  'Manhattan',
    'marist':                     'Marist',
    'marquette':                  'Marquette',
    'marshall':                   'Marshall',
    'maryland':                   'Maryland',
    'maryland-eastern-shore':     'Maryland Eastern Shore',
    'massachusetts':              'Massachusetts',
    'mcneese-state':              'McNeese St.',
    'memphis':                    'Memphis',
    'mercer':                     'Mercer',
    'miami-fl':                   'Miami FL',
    'miami-oh':                   'Miami OH',
    'michigan':                   'Michigan',
    'michigan-state':             'Michigan St.',
    'middle-tennessee':           'Middle Tennessee',
    'minnesota':                  'Minnesota',
    'mississippi':                'Mississippi',
    'mississippi-state':          'Mississippi St.',
    'mississippi-valley-state':   'Mississippi Valley St.',
    'missouri':                   'Missouri',
    'missouri-kansas-city':       'UMKC',
    'missouri-state':             'Missouri St.',
    'monmouth':                   'Monmouth',
    'montana':                    'Montana',
    'montana-state':              'Montana St.',
    'morehead-state':             'Morehead St.',
    'morgan-state':               'Morgan St.',
    'mount-st-marys':             "Mount St. Mary's",
    'murray-state':               'Murray St.',
    'navy':                       'Navy',
    'nebraska':                   'Nebraska',
    'nevada':                     'Nevada',
    'nevada-las-vegas':           'UNLV',
    'new-mexico':                 'New Mexico',
    'new-mexico-state':           'New Mexico St.',
    'new-orleans':                'New Orleans',
    'niagara':                    'Niagara',
    'nicholls-state':             'Nicholls St.',
    'norfolk-state':              'Norfolk St.',
    'north-carolina':             'North Carolina',
    'north-carolina-asheville':   'UNC Asheville',
    'north-carolina-central':     'North Carolina Central',
    'north-carolina-greensboro':  'UNC Greensboro',
    'north-carolina-state':       'N.C. State',
    'north-carolina-wilmington':  'UNC Wilmington',
    'north-dakota':               'North Dakota',
    'north-dakota-state':         'North Dakota St.',
    'north-florida':              'North Florida',
    'north-texas':                'North Texas',
    'northeastern':               'Northeastern',
    'northern-arizona':           'Northern Arizona',
    'northern-colorado':          'Northern Colorado',
    'northern-illinois':          'Northern Illinois',
    'northern-iowa':              'Northern Iowa',
    'northern-kentucky':          'Northern Kentucky',
    'northwestern':               'Northwestern',
    'northwestern-state':         'Northwestern St.',
    'notre-dame':                 'Notre Dame',
    'oakland':                    'Oakland',
    'ohio':                       'Ohio',
    'ohio-state':                 'Ohio St.',
    'oklahoma':                   'Oklahoma',
    'oklahoma-state':             'Oklahoma St.',
    'old-dominion':               'Old Dominion',
    'oral-roberts':               'Oral Roberts',
    'oregon':                     'Oregon',
    'oregon-state':               'Oregon St.',
    'pacific':                    'Pacific',
    'penn-state':                 'Penn St.',
    'pennsylvania':               'Penn',
    'pepperdine':                 'Pepperdine',
    'pittsburgh':                 'Pittsburgh',
    'portland':                   'Portland',
    'portland-state':             'Portland St.',
    'prairie-view':               'Prairie View A&M',
    'presbyterian':               'Presbyterian',
    'princeton':                  'Princeton',
    'providence':                 'Providence',
    'purdue':                     'Purdue',
    'quinnipiac':                 'Quinnipiac',
    'radford':                    'Radford',
    'richmond':                   'Richmond',
    'rider':                      'Rider',
    'robert-morris':              'Robert Morris',
    'rutgers':                    'Rutgers',
    'sacred-heart':               'Sacred Heart',
    'saint-francis-pa':           'St. Francis PA',
    'saint-josephs':              "Saint Joseph's",
    'saint-louis':                'Saint Louis',
    'saint-marys-ca':             "Saint Mary's",
    'saint-peters':               "Saint Peter's",
    'sam-houston-state':          'Sam Houston St.',
    'samford':                    'Samford',
    'san-diego':                  'San Diego',
    'san-diego-state':            'San Diego St.',
    'san-francisco':              'San Francisco',
    'san-jose-state':             'San Jose St.',
    'seattle':                    'Seattle',
    'seton-hall':                 'Seton Hall',
    'siena':                      'Siena',
    'south-carolina':             'South Carolina',
    'south-carolina-state':       'South Carolina St.',
    'south-dakota':               'South Dakota',
    'south-dakota-state':         'South Dakota St.',
    'south-florida':              'South Florida',
    'southeastern-louisiana':     'Southeastern Louisiana',
    'southern':                   'Southern',
    'southern-california':        'USC',
    'southern-illinois':          'Southern Illinois',
    'southern-methodist':         'SMU',
    'southern-mississippi':       'Southern Miss',
    'southern-utah':              'Southern Utah',
    'st-bonaventure':             'St. Bonaventure',
    'st-francis-ny':              'St. Francis NY',
    'st-johns-ny':                "St. John's",
    'stanford':                   'Stanford',
    'stephen-f-austin':           'Stephen F. Austin',
    'stetson':                    'Stetson',
    'stony-brook':                'Stony Brook',
    'syracuse':                   'Syracuse',
    'temple':                     'Temple',
    'tennessee':                  'Tennessee',
    'tennessee-martin':           'Tennessee Martin',
    'tennessee-state':            'Tennessee St.',
    'tennessee-tech':             'Tennessee Tech',
    'texas':                      'Texas',
    'texas-am':                   'Texas A&M',
    'texas-am-corpus-christi':    'Texas A&M Corpus Chris',
    'texas-christian':            'TCU',
    'texas-san-antonio':          'UTSA',
    'texas-southern':             'Texas Southern',
    'texas-state':                'Texas St.',
    'texas-tech':                 'Texas Tech',
    'toledo':                     'Toledo',
    'towson':                     'Towson',
    'troy':                       'Troy',
    'tulane':                     'Tulane',
    'tulsa':                      'Tulsa',
    'ucla':                       'UCLA',
    'utah':                       'Utah',
    'utah-state':                 'Utah St.',
    'utah-valley':                'Utah Valley',
    'valparaiso':                 'Valparaiso',
    'vanderbilt':                 'Vanderbilt',
    'vermont':                    'Vermont',
    'villanova':                  'Villanova',
    'virginia':                   'Virginia',
    'virginia-commonwealth':      'VCU',
    'virginia-military-institute':'VMI',
    'virginia-tech':              'Virginia Tech',
    'wagner':                     'Wagner',
    'wake-forest':                'Wake Forest',
    'washington':                 'Washington',
    'washington-state':           'Washington St.',
    'weber-state':                'Weber St.',
    'west-virginia':              'West Virginia',
    'western-carolina':           'Western Carolina',
    'western-illinois':           'Western Illinois',
    'western-kentucky':           'Western Kentucky',
    'western-michigan':           'Western Michigan',
    'wichita-state':              'Wichita St.',
    'william-mary':               'William & Mary',
    'winthrop':                   'Winthrop',
    'wisconsin':                  'Wisconsin',
    'wofford':                    'Wofford',
    'wright-state':               'Wright St.',
    'wyoming':                    'Wyoming',
    'xavier':                     'Xavier',
    'yale':                       'Yale',
}


# ── Builder ────────────────────────────────────────────────────────────────────

def build_coach_map() -> dict[str, dict[str, str]]:
    """Read all coaches_raw/*.json and build {team: {year: coach_name}}.

    Returns the mapping keyed by canonical team name.
    Prints warnings for any SR school IDs missing from SR_TO_NORMALIZED.
    """
    raw_files = sorted(RAW_DIR.glob('*.json'))
    if not raw_files:
        print(f'No files found in {RAW_DIR}. Run scrape_coaches.py first.')
        sys.exit(1)

    team_coaches: dict[str, dict[str, str]] = {}
    unmapped: list[str] = []

    for path in raw_files:
        school_id = path.stem
        team_name = SR_TO_NORMALIZED.get(school_id)

        if team_name is None:
            unmapped.append(school_id)
            continue

        raw = json.loads(path.read_text(encoding='utf-8'))
        coaches = raw.get('coaches', [])

        year_map: dict[str, str] = {}
        for entry in coaches:
            y_from = entry.get('year_from')
            y_to   = entry.get('year_to')
            name   = entry.get('name', '').strip()
            if not name or y_from is None or y_to is None:
                continue
            for year in range(max(y_from, YEAR_MIN), min(y_to, YEAR_MAX) + 1):
                year_map[str(year)] = name

        if year_map:
            # IPFW renamed to Purdue Fort Wayne in 2019 — KenPom uses both names.
            # Split into two separate entries so the feature builder finds the right key.
            if school_id == 'ipfw':
                ipfw_years        = {y: c for y, c in year_map.items() if int(y) <= 2018}
                pfw_years         = {y: c for y, c in year_map.items() if int(y) >= 2019}
                if ipfw_years:
                    team_coaches['IPFW'] = ipfw_years
                if pfw_years:
                    team_coaches['Purdue Fort Wayne'] = pfw_years
            else:
                team_coaches[team_name] = year_map

    if unmapped:
        print(f'\n[warn] {len(unmapped)} school IDs not in SR_TO_NORMALIZED — skipped:')
        for sid in sorted(unmapped):
            print(f'  {sid}')

    return team_coaches


def main():
    print('Building team->coach->year mapping...')
    mapping = build_coach_map()

    OUT_PATH.write_text(
        json.dumps(mapping, indent=2, sort_keys=True),
        encoding='utf-8',
    )

    # Write SR school ID -> normalized name mapping so src/coach_features.py
    # can use it without importing from scripts/.
    sr_map_path = CONFIG_DIR / 'sr_school_map.json'
    sr_map_path.write_text(
        json.dumps(SR_TO_NORMALIZED, indent=2, sort_keys=True),
        encoding='utf-8',
    )
    print(f'Wrote SR school map -> {sr_map_path}')

    total_entries = sum(len(v) for v in mapping.values())
    print(f'\nWrote {len(mapping)} teams, {total_entries} team-year entries -> {OUT_PATH}')

    # Spot-check a few known coaches
    checks = [
        ('Iowa St.',   '2002', 'Larry Eustachy'),
        ('Iowa St.',   '2015', 'Fred Hoiberg'),
        ('Kentucky',   '2012', 'John Calipari'),
        ('Duke',       '2015', 'Mike Krzyzewski'),
        ('Kansas',     '2022', 'Bill Self'),
    ]
    print('\nSpot checks:')
    for team, year, expected in checks:
        from src.names import normalize_name
        t = normalize_name(team)
        got = mapping.get(t, {}).get(year, '—')
        status = 'OK' if expected.lower() in got.lower() else 'MISMATCH'
        print(f'  [{status}] {team} {year}: expected "{expected}", got "{got}"')


if __name__ == '__main__':
    main()
