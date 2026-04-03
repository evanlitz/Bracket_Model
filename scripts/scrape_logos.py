"""Scrape team logos for all historical tournament teams (2002-2026) from ESPN.

Downloads one PNG per team to app/frontend/public/logos/{team_slug}.png.
Uses ESPN's public teams API (no auth required).
Skips teams whose logo file already exists unless --force is passed.

Run from project root:
    python scripts/scrape_logos.py
    python scripts/scrape_logos.py --force   # re-download existing files
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import pandas as pd
from src.kenpom import load_kenpom
from src.names import normalize_name

LOGOS_DIR = Path(__file__).resolve().parent.parent / 'app' / 'frontend' / 'public' / 'logos'

# KenPom name -> ESPN displayName (full nickname form ESPN uses)
ESPN_OVERRIDES = {
    'Abilene Christian':      'Abilene Christian Wildcats',
    'Air Force':              'Air Force Falcons',
    'Akron':                  'Akron Zips',
    'Alabama':                'Alabama Crimson Tide',
    'Alabama A&M':            'Alabama A&M Bulldogs',
    'Alabama St.':            'Alabama State Hornets',
    'Albany':                 'UAlbany Great Danes',
    'Alcorn St.':             'Alcorn State Braves',
    'American':               'American University Eagles',
    'Appalachian St.':        'App State Mountaineers',
    'Arizona':                'Arizona Wildcats',
    'Arizona St.':            'Arizona State Sun Devils',
    'Arkansas':               'Arkansas Razorbacks',
    'Arkansas Little Rock':   'Little Rock Trojans',
    'Arkansas Pine Bluff':    'Arkansas-Pine Bluff Golden Lions',
    'Auburn':                 'Auburn Tigers',
    'Austin Peay':            'Austin Peay Governors',
    'BYU':                    'BYU Cougars',
    'Baylor':                 'Baylor Bears',
    'Belmont':                'Belmont Bruins',
    'Binghamton':             'Binghamton Bearcats',
    'Boise St.':              'Boise State Broncos',
    'Boston College':         'Boston College Eagles',
    'Boston University':      'Boston University Terriers',
    'Bradley':                'Bradley Braves',
    'Bryant':                 'Bryant Bulldogs',
    'Bucknell':               'Bucknell Bison',
    'Buffalo':                'Buffalo Bulls',
    'Butler':                 'Butler Bulldogs',
    'Cal Baptist':            'California Baptist Lancers',
    'Cal Poly':               'Cal Poly Mustangs',
    'Cal St. Bakersfield':    'Cal State Bakersfield Roadrunners',
    'Cal St. Fullerton':      'Cal State Fullerton Titans',
    'Cal St. Northridge':     'Cal State Northridge Matadors',
    'California':             'California Golden Bears',
    'Central Connecticut':    'Central Connecticut Blue Devils',
    'Central Michigan':       'Central Michigan Chippewas',
    'Charleston':             'Charleston Cougars',
    'Charlotte':              'Charlotte 49ers',
    'Chattanooga':            'Chattanooga Mocs',
    'Cincinnati':             'Cincinnati Bearcats',
    'Clemson':                'Clemson Tigers',
    'Cleveland St.':          'Cleveland State Vikings',
    'Coastal Carolina':       'Coastal Carolina Chanticleers',
    'Colgate':                'Colgate Raiders',
    'College of Charleston':  'Charleston Cougars',
    'Colorado':               'Colorado Buffaloes',
    'Colorado St.':           'Colorado State Rams',
    'Connecticut':            'UConn Huskies',
    'Coppin St.':             'Coppin State Eagles',
    'Cornell':                'Cornell Big Red',
    'Creighton':              'Creighton Bluejays',
    'Davidson':               'Davidson Wildcats',
    'Dayton':                 'Dayton Flyers',
    'DePaul':                 'DePaul Blue Demons',
    'Delaware':               'Delaware Blue Hens',
    'Delaware St.':           'Delaware State Hornets',
    'Detroit':                'Detroit Mercy Titans',
    'Drake':                  'Drake Bulldogs',
    'Drexel':                 'Drexel Dragons',
    'Duke':                   'Duke Blue Devils',
    'Duquesne':               'Duquesne Dukes',
    'East Tennessee St.':     'East Tennessee State Buccaneers',
    'Eastern Kentucky':       'Eastern Kentucky Colonels',
    'Eastern Washington':     'Eastern Washington Eagles',
    'Fairleigh Dickinson':    'Fairleigh Dickinson Knights',
    'Florida':                'Florida Gators',
    'Florida A&M':            'Florida A&M Rattlers',
    'Florida Atlantic':       'Florida Atlantic Owls',
    'Florida Gulf Coast':     'Florida Gulf Coast Eagles',
    'Florida St.':            'Florida State Seminoles',
    'Fresno St.':             'Fresno State Bulldogs',
    'Furman':                 'Furman Paladins',
    'Gardner Webb':           "Gardner-Webb Runnin' Bulldogs",
    'George Mason':           'George Mason Patriots',
    'George Washington':      'George Washington Revolutionaries',
    'Georgetown':             'Georgetown Hoyas',
    'Georgia':                'Georgia Bulldogs',
    'Georgia St.':            'Georgia State Panthers',
    'Georgia Tech':           'Georgia Tech Yellow Jackets',
    'Gonzaga':                'Gonzaga Bulldogs',
    'Grambling St.':          'Grambling Tigers',
    'Grand Canyon':           'Grand Canyon Lopes',
    'Green Bay':              'Green Bay Phoenix',
    'Hampton':                'Hampton Pirates',
    'Harvard':                'Harvard Crimson',
    'Hawaii':                 "Hawai'i Rainbow Warriors",
    'High Point':             'High Point Panthers',
    'Hofstra':                'Hofstra Pride',
    'Holy Cross':             'Holy Cross Crusaders',
    'Houston':                'Houston Cougars',
    'Howard':                 'Howard Bison',
    'IUPUI':                  'IU Indianapolis Jaguars',
    'Idaho':                  'Idaho Vandals',
    'Illinois':               'Illinois Fighting Illini',
    'Illinois Chicago':       'UIC Flames',
    'Indiana':                'Indiana Hoosiers',
    'Indiana St.':            'Indiana State Sycamores',
    'Iona':                   'Iona Gaels',
    'Iowa':                   'Iowa Hawkeyes',
    'Iowa St.':               'Iowa State Cyclones',
    'Jackson St.':            'Jackson State Tigers',
    'Jacksonville St.':       'Jacksonville State Gamecocks',
    'James Madison':          'James Madison Dukes',
    'Kansas':                 'Kansas Jayhawks',
    'Kansas St.':             'Kansas State Wildcats',
    'Kennesaw St.':           'Kennesaw State Owls',
    'Kent St.':               'Kent State Golden Flashes',
    'Kentucky':               'Kentucky Wildcats',
    'LIU':                    'Long Island University Sharks',
    'LIU Brooklyn':           'Long Island University Sharks',
    'LSU':                    'LSU Tigers',
    'La Salle':               'La Salle Explorers',
    'Lafayette':              'Lafayette Leopards',
    'Lamar':                  'Lamar Cardinals',
    'Lehigh':                 'Lehigh Mountain Hawks',
    'Liberty':                'Liberty Flames',
    'Lipscomb':               'Lipscomb Bisons',
    'Long Beach St.':         'Long Beach State Beach',
    'Longwood':               'Longwood Lancers',
    'Louisiana':              "Louisiana Ragin' Cajuns",
    'Louisiana Lafayette':    "Louisiana Ragin' Cajuns",
    'Louisville':             'Louisville Cardinals',
    'Loyola Chicago':         'Loyola Chicago Ramblers',
    'Loyola MD':              'Loyola Maryland Greyhounds',
    'Manhattan':              'Manhattan Jaspers',
    'Marquette':              'Marquette Golden Eagles',
    'Marshall':               'Marshall Thundering Herd',
    'Maryland':               'Maryland Terrapins',
    'Massachusetts':          'Massachusetts Minutemen',
    'McNeese':                'McNeese Cowboys',
    'McNeese St.':            'McNeese Cowboys',
    'Memphis':                'Memphis Tigers',
    'Mercer':                 'Mercer Bears',
    'Miami FL':               'Miami Hurricanes',
    'Miami OH':               'Miami (OH) RedHawks',
    'Michigan':               'Michigan Wolverines',
    'Michigan St.':           'Michigan State Spartans',
    'Middle Tennessee':       'Middle Tennessee Blue Raiders',
    'Milwaukee':              'Milwaukee Panthers',
    'Minnesota':              'Minnesota Golden Gophers',
    'Mississippi':            'Ole Miss Rebels',
    'Mississippi St.':        'Mississippi State Bulldogs',
    'Mississippi Valley St.': 'Mississippi Valley State Delta Devils',
    'Missouri':               'Missouri Tigers',
    'Monmouth':               'Monmouth Hawks',
    'Montana':                'Montana Grizzlies',
    'Montana St.':            'Montana State Bobcats',
    'Morehead St.':           'Morehead State Eagles',
    'Morgan St.':             'Morgan State Bears',
    "Mount St. Mary's":       "Mount St. Mary's Mountaineers",
    'Murray St.':             'Murray State Racers',
    'N.C. State':             'NC State Wolfpack',
    'Nebraska':               'Nebraska Cornhuskers',
    'Nebraska Omaha':         'Omaha Mavericks',
    'Nevada':                 'Nevada Wolf Pack',
    'New Mexico':             'New Mexico Lobos',
    'New Mexico St.':         'New Mexico State Aggies',
    'New Orleans':            'New Orleans Privateers',
    'Niagara':                'Niagara Purple Eagles',
    'Norfolk St.':            'Norfolk State Spartans',
    'North Carolina':         'North Carolina Tar Heels',
    'North Carolina A&T':     'North Carolina A&T Aggies',
    'North Carolina Central': 'North Carolina Central Eagles',
    'North Carolina St.':     'NC State Wolfpack',
    'North Dakota':           'North Dakota Fighting Hawks',
    'North Dakota St.':       'North Dakota State Bison',
    'North Florida':          'North Florida Ospreys',
    'North Texas':            'North Texas Mean Green',
    'Northeastern':           'Northeastern Huskies',
    'Northern Colorado':      'Northern Colorado Bears',
    'Northern Iowa':          'Northern Iowa Panthers',
    'Northern Kentucky':      'Northern Kentucky Norse',
    'Northwestern':           'Northwestern Wildcats',
    'Northwestern St.':       'Northwestern State Demons',
    'Notre Dame':             'Notre Dame Fighting Irish',
    'Oakland':                'Oakland Golden Grizzlies',
    'Ohio':                   'Ohio Bobcats',
    'Ohio St.':               'Ohio State Buckeyes',
    'Oklahoma':               'Oklahoma Sooners',
    'Oklahoma St.':           'Oklahoma State Cowboys',
    'Old Dominion':           'Old Dominion Monarchs',
    'Oral Roberts':           'Oral Roberts Golden Eagles',
    'Oregon':                 'Oregon Ducks',
    'Oregon St.':             'Oregon State Beavers',
    'Pacific':                'Pacific Tigers',
    'Penn':                   'Pennsylvania Quakers',
    'Penn St.':               'Penn State Nittany Lions',
    'Pepperdine':             'Pepperdine Waves',
    'Pittsburgh':             'Pittsburgh Panthers',
    'Portland St.':           'Portland State Vikings',
    'Prairie View A&M':       'Prairie View A&M Panthers',
    'Princeton':              'Princeton Tigers',
    'Providence':             'Providence Friars',
    'Purdue':                 'Purdue Boilermakers',
    'Queens':                 'Queens University Royals',
    'Radford':                'Radford Highlanders',
    'Rhode Island':           'Rhode Island Rams',
    'Richmond':               'Richmond Spiders',
    'Robert Morris':          'Robert Morris Colonials',
    'Rutgers':                'Rutgers Scarlet Knights',
    'SIUE':                   'SIUE Cougars',
    'SMU':                    'SMU Mustangs',
    'Saint Francis':          'Saint Francis Red Flash',
    "Saint Joseph's":         "Saint Joseph's Hawks",
    'Saint Louis':            'Saint Louis Billikens',
    "Saint Mary's":           "Saint Mary's Gaels",
    "Saint Peter's":          "Saint Peter's Peacocks",
    'Sam Houston St.':        'Sam Houston Bearkats',
    'Samford':                'Samford Bulldogs',
    'San Diego':              'San Diego Toreros',
    'San Diego St.':          'San Diego State Aztecs',
    'San Francisco':          'San Francisco Dons',
    'Santa Clara':            'Santa Clara Broncos',
    'Seton Hall':             'Seton Hall Pirates',
    'Siena':                  'Siena Saints',
    'SIUE':                   'SIU Edwardsville Cougars',
    'South Alabama':          'South Alabama Jaguars',
    'South Carolina':         'South Carolina Gamecocks',
    'South Carolina St.':     'South Carolina State Bulldogs',
    'South Dakota St.':       'South Dakota State Jackrabbits',
    'South Florida':          'South Florida Bulls',
    'Southeast Missouri St.': 'Southeast Missouri State Redhawks',
    'Southeastern Louisiana': 'SE Louisiana Lions',
    'Southern':               'Southern Jaguars',
    'Southern Illinois':      'Southern Illinois Salukis',
    'Southern Miss':          'Southern Miss Golden Eagles',
    'St. Bonaventure':        'St. Bonaventure Bonnies',
    "St. John's":             "St. John's Red Storm",
    'Stanford':               'Stanford Cardinal',
    'Stephen F. Austin':      'Stephen F. Austin Lumberjacks',
    'Stetson':                'Stetson Hatters',
    'Stony Brook':            'Stony Brook Seawolves',
    'Syracuse':               'Syracuse Orange',
    'TCU':                    'TCU Horned Frogs',
    'Temple':                 'Temple Owls',
    'Tennessee':              'Tennessee Volunteers',
    'Tennessee St.':          'Tennessee State Tigers',
    'Texas':                  'Texas Longhorns',
    'Texas A&M':              'Texas A&M Aggies',
    'Texas A&M Corpus Chris': 'Texas A&M-Corpus Christi Islanders',
    'Texas Southern':         'Texas Southern Tigers',
    'Texas Tech':             'Texas Tech Red Raiders',
    'Troy':                   'Troy Trojans',
    'Troy St.':               'Troy Trojans',
    'Tulsa':                  'Tulsa Golden Hurricane',
    'UAB':                    'UAB Blazers',
    'UC Davis':               'UC Davis Aggies',
    'UC Irvine':              'UC Irvine Anteaters',
    'UC San Diego':           'UC San Diego Tritons',
    'UC Santa Barbara':       'UC Santa Barbara Gauchos',
    'UCF':                    'UCF Knights',
    'UCLA':                   'UCLA Bruins',
    'UMBC':                   'UMBC Retrievers',
    'UNC Asheville':          'UNC Asheville Bulldogs',
    'UNC Greensboro':         'UNC Greensboro Spartans',
    'UNC Wilmington':         'UNC Wilmington Seahawks',
    'UNLV':                   'UNLV Rebels',
    'USC':                    'USC Trojans',
    'UT Arlington':           'UT Arlington Mavericks',
    'UTEP':                   'UTEP Miners',
    'UTSA':                   'UTSA Roadrunners',
    'Utah':                   'Utah Utes',
    'Utah St.':               'Utah State Aggies',
    'VCU':                    'VCU Rams',
    'Valparaiso':             'Valparaiso Beacons',
    'Vanderbilt':             'Vanderbilt Commodores',
    'Vermont':                'Vermont Catamounts',
    'Villanova':              'Villanova Wildcats',
    'Virginia':               'Virginia Cavaliers',
    'Virginia Tech':          'Virginia Tech Hokies',
    'Wagner':                 'Wagner Seahawks',
    'Wake Forest':            'Wake Forest Demon Deacons',
    'Washington':             'Washington Huskies',
    'Washington St.':         'Washington State Cougars',
    'Weber St.':              'Weber State Wildcats',
    'West Virginia':          'West Virginia Mountaineers',
    'Western Kentucky':       'Western Kentucky Hilltoppers',
    'Western Michigan':       'Western Michigan Broncos',
    'Wichita St.':            'Wichita State Shockers',
    'Wisconsin':              'Wisconsin Badgers',
    'Winthrop':               'Winthrop Eagles',
    'Wofford':                'Wofford Terriers',
    'Wright St.':             'Wright State Raiders',
    'Wyoming':                'Wyoming Cowboys',
    'Xavier':                 'Xavier Musketeers',
    'Yale':                   'Yale Bulldogs',
}


def team_slug(name: str) -> str:
    return name.replace(' ', '_').replace('.', '').replace("'", '').replace('&', 'and').replace('(', '').replace(')', '')


def fetch_espn_teams() -> dict:
    """Return {displayName: {id, logo_url}} for all ESPN D-I teams."""
    url = ('https://site.api.espn.com/apis/site/v2/sports/basketball'
           '/mens-college-basketball/teams?limit=500')
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    out = {}
    for entry in r.json()['sports'][0]['leagues'][0]['teams']:
        t = entry['team']
        logos = t.get('logos', [])
        if logos:
            out[t['displayName']] = {
                'id':       t['id'],
                'logo_url': logos[0]['href'],
            }
    return out


def download_logo(url: str, dest: Path, session: requests.Session) -> bool:
    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f'    ERROR downloading {url}: {e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Scrape ESPN logos for all historical tournament teams')
    parser.add_argument('--force', action='store_true', help='Re-download existing files')
    args = parser.parse_args()

    LOGOS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect unique seeded teams across all years 2002-2026 (no 2020)
    all_years = [y for y in range(2002, 2027) if y != 2020]
    team_set = set()
    for year in all_years:
        try:
            kp = load_kenpom(year)
            seeded = kp[kp['seed'].notna()]['TeamName'].tolist()
            team_set.update(seeded)
        except Exception:
            pass
    seeded_teams = sorted(team_set)
    print(f'Unique tournament teams across all years: {len(seeded_teams)}')

    # Fetch ESPN team index
    print('Fetching ESPN team index...')
    espn_teams = fetch_espn_teams()
    print(f'ESPN teams found: {len(espn_teams)}\n')

    session  = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    ok       = []
    skipped  = []
    failed   = []

    for team in seeded_teams:
        slug  = team_slug(team)
        dest  = LOGOS_DIR / f'{slug}.png'

        if dest.exists() and not args.force:
            skipped.append(team)
            continue

        # Resolve ESPN display name
        espn_name = ESPN_OVERRIDES.get(team, team)
        info      = espn_teams.get(espn_name)

        if info is None:
            print(f'  [NO MATCH]  {team!r}  (tried ESPN name: {espn_name!r})')
            failed.append(team)
            continue

        success = download_logo(info['logo_url'], dest, session)
        if success:
            print(f'  [OK]  {team:<30}  ->  {slug}.png')
            ok.append(team)
        else:
            failed.append(team)

        time.sleep(0.1)  # be polite

    print(f'\nDone.')
    print(f'  Downloaded : {len(ok)}')
    print(f'  Skipped    : {len(skipped)}  (already exist, use --force to re-download)')
    if failed:
        print(f'  Failed     : {len(failed)}')
        for t in failed:
            print(f'    - {t}')
        print('\nFor failed teams, add the correct ESPN displayName to ESPN_OVERRIDES in this script.')
    else:
        print(f'  Failed     : 0')
    print(f'\nLogos saved to: {LOGOS_DIR}')


if __name__ == '__main__':
    main()
