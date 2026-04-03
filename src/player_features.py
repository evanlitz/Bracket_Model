"""Player roster features for tournament game prediction.

For each team, computes roster-level signals from players.parquet files:

    fr_min_pct        — fraction of team minutes played by freshmen
    returning_min_pct — fraction of this year's minutes from players who were
                        also on the roster last year (team cohesion)
    star_min_conc     — top player's share of total team minutes (concentration risk)
    star_eup          — best player's Efficient Usage Product (ortg × usage × minutes)
    depth_eup         — EUP sum of 4th–7th rotation players (supporting cast quality)
    two_way_depth     — sum of (ortg-100) × (blk+stl) × minutes across all players
                        captures two-way players who score AND defend
    interior_dom      — blk_pct × or_pct × pct_min for players ≥ 6'6", summed and
                        normalized; bigs who block AND rebound dominate the paint
    triple_threat     — max(fg2_pct × fg3_pct × ft_pct × pct_min/100) across all
                        players; identifies the one player the defense cannot stop
                        regardless of scheme (must score inside, outside, and at line)

EUP formula: ortg × (pct_poss/100) × (pct_min/100)
    — penalizes high-ORTG players with low usage or low playing time
    — a 130-ORTG player at 8% usage, 30% minutes contributes far less than
      a 122-ORTG player at 25% usage, 80% minutes

These are computed pre-tournament from season roster data.

Main entry point:
    build_player_matchup_df(bracket_df, years) -> pd.DataFrame
        One row per tournament matchup with player _diff columns.
        Merge with features.build_matchup_df() output on index.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.names import normalize_name


def _height_inches(h: str) -> float:
    """Parse '6-11' style height string to total inches. Returns NaN on failure."""
    try:
        feet, inches = str(h).split('-')
        return int(feet) * 12 + int(inches)
    except Exception:
        return float('nan')

DATA_DIR = Path(__file__).parent.parent / 'data'

PLAYER_FEATURES     = ['fr_min_pct', 'returning_min_pct', 'star_min_conc',
                       'star_eup', 'depth_eup', 'two_way_depth',
                       'interior_dom', 'triple_threat',
                       'roster_seniority', 'ft_clutch',
                       'playmaker_quality', 'perimeter_depth',
                       'to_exposure', 'bench_depth', 'rebounding_balance',
                       'foul_drawing', 'foul_trouble_risk',
                       'avg_rotation_height', 'ts_efficiency', 'rotation_depth']
PLAYER_DIFF_FEATURES = [f'{f}_diff' for f in PLAYER_FEATURES]


# ── Per-year loader ────────────────────────────────────────────────────────────

def load_player_features(year: int) -> pd.DataFrame:
    """Compute roster features for all teams in a given year.

    Returns DataFrame indexed by normalized team name with columns:
        fr_min_pct, returning_min_pct, star_min_conc,
        star_eup, depth_eup, two_way_depth, interior_dom, triple_threat.

    returning_min_pct requires the previous year's player directory;
    set to NaN if unavailable (e.g. first year of data, or missing 2020).
    """
    player_dir = DATA_DIR / str(year)   / 'players'
    prev_dir   = DATA_DIR / str(year - 1) / 'players'

    if not player_dir.exists():
        return pd.DataFrame()

    # Build {team_norm -> set of player names} for the previous year
    prev_names: dict[str, set[str]] = {}
    if prev_dir.exists():
        for p in prev_dir.glob('*.parquet'):
            df_p = pd.read_parquet(p)
            if df_p.empty or 'team' not in df_p.columns or 'name' not in df_p.columns:
                continue
            team_norm = normalize_name(df_p['team'].iloc[0])
            prev_names[team_norm] = set(df_p['name'].str.strip().str.lower())

    rows = []
    for p in player_dir.glob('*.parquet'):
        df = pd.read_parquet(p)
        if df.empty or 'team' not in df.columns or 'pct_min' not in df.columns:
            continue

        team_norm = normalize_name(df['team'].iloc[0])
        total_min = df['pct_min'].sum()
        if total_min <= 0:
            continue

        # Freshmen minute share
        fr_min_pct = df.loc[df['year'] == 'Fr', 'pct_min'].sum() / total_min

        # Top player's minute share (concentration risk)
        star_min_conc = df['pct_min'].max() / total_min

        # Returning minute share (requires previous year roster)
        if team_norm in prev_names:
            name_norm = df['name'].str.strip().str.lower()
            returning_min = df.loc[name_norm.isin(prev_names[team_norm]), 'pct_min'].sum()
            returning_min_pct = returning_min / total_min
        else:
            returning_min_pct = float('nan')

        # Efficient Usage Product: ortg × (pct_poss/100) × (pct_min/100)
        # Penalizes high-ORTG players with low usage or limited minutes.
        df = df.copy()
        df['eup'] = df['ortg'] * (df['pct_poss'] / 100) * (df['pct_min'] / 100)

        # Star EUP: best single player's full contribution
        star_eup = df['eup'].max()

        # Depth EUP: supporting cast quality — EUP sum of 4th–7th players by minutes.
        # These are the players who absorb load when starters are in foul trouble.
        rotation = df.nlargest(7, 'pct_min')
        depth_eup = rotation.iloc[3:]['eup'].sum() if len(rotation) >= 4 else float('nan')

        # Two-way depth: Σ (ortg-100) × (blk_pct + stl_pct)/100 × (pct_min/100)
        # Each term is already weighted by minute share, so the sum is the team-level
        # aggregate. Positive = team has players who score efficiently AND defend.
        df['two_way_contrib'] = (
            (df['ortg'] - 100)
            * (df['blk_pct'] + df['stl_pct']) / 100
            * (df['pct_min'] / 100)
        )
        two_way_depth = df['two_way_contrib'].sum()

        # Interior dominance: bigs (≥6'6" = 78 inches) who block AND rebound.
        # Σ (blk_pct × or_pct × pct_min) normalized by total team minutes.
        # Validated at +0.245 multi-year correlation with rounds advanced.
        df['height_in'] = df['height'].map(_height_inches)
        bigs = df[df['height_in'] >= 78]
        interior_dom = (
            (bigs['blk_pct'] * bigs['or_pct'] * bigs['pct_min']).sum() / total_min
            if len(bigs) > 0 else 0.0
        )

        # Triple threat scorer: the one player the defense cannot scheme away.
        # fg2_pct × fg3_pct × ft_pct × (pct_min/100) — must score inside, outside,
        # and at the line with real playing time. Validated at +0.169 multi-year.
        df['triple'] = (
            df['fg2_pct'] * df['fg3_pct'] * df['ft_pct'] * (df['pct_min'] / 100)
        )
        triple_threat = float(df['triple'].max())

        # Roster seniority: minutes-weighted average class year (Fr=1, So=2, Jr=3, Sr=4, Gr=5).
        # Graduate students count as 5 — they have senior experience plus an extra year.
        # Excludes players whose class is unknown (NaN class_num).
        class_map = {'Fr': 1, 'So': 2, 'Jr': 3, 'Sr': 4, 'Gr': 5, 'Gr5': 5, 'Grad': 5}
        df['class_num'] = df['year'].map(class_map)
        valid = df[df['class_num'].notna() & df['pct_min'].notna()]
        if len(valid) > 0 and valid['pct_min'].sum() > 0:
            roster_seniority = float(
                (valid['class_num'] * valid['pct_min']).sum() / valid['pct_min'].sum()
            )
        else:
            roster_seniority = float('nan')

        # Top-8 rotation (by minutes) — used by ft_clutch, playmaker_quality, to_exposure
        rotation8 = df.nlargest(8, 'pct_min')

        # FT clutch: minutes-weighted FT% across top-8 rotation players.
        # Tournament games are decided at the line; poor FT teams get exploited.
        valid_ft = rotation8[rotation8['ft_pct'].notna() & rotation8['pct_min'].notna()]
        if len(valid_ft) > 0 and valid_ft['pct_min'].sum() > 0:
            ft_clutch = float(
                (valid_ft['ft_pct'] * valid_ft['pct_min']).sum() / valid_ft['pct_min'].sum()
            )
        else:
            ft_clutch = float('nan')

        # Playmaker quality: best facilitator's clean assist contribution per team minute.
        # a_rate × (1 - to_rate/100) × (pct_min/100) — rewards high-assist, low-TO players
        # with real playing time. Penalizes turnover-prone passers.
        pm = rotation8[rotation8['a_rate'].notna() & rotation8['to_rate'].notna()]
        if len(pm) > 0:
            pm_scores = pm['a_rate'] * (1 - pm['to_rate'] / 100) * (pm['pct_min'] / 100)
            playmaker_quality = float(pm_scores.max())
        else:
            playmaker_quality = float('nan')

        # Perimeter depth: sum of fg3_pct × pct_min for reliable shooters (fg3_pct > 0.33).
        # Captures how many floor-spacers are in the rotation, not just the best one.
        shooters = df[(df['fg3_pct'] > 0.33) & (df['pct_min'] >= 5)]
        perimeter_depth = float((shooters['fg3_pct'] * shooters['pct_min']).sum())

        # Turnover exposure: minutes-weighted TO rate across top-8 rotation.
        # High-TO teams collapse under tournament press and trapping defenses.
        valid_to = rotation8[rotation8['to_rate'].notna() & rotation8['pct_min'].notna()]
        if len(valid_to) > 0 and valid_to['pct_min'].sum() > 0:
            to_exposure = float(
                (valid_to['to_rate'] * valid_to['pct_min']).sum() / valid_to['pct_min'].sum()
            )
        else:
            to_exposure = float('nan')

        # Bench depth: EUP sum of non-starters (starter == False).
        # Distinct from depth_eup (4th-7th by minutes) — specifically true bench players
        # who must absorb load when starters are in foul trouble.
        bench = df[df['starter'] == False]
        bench_depth = float(bench['eup'].sum()) if len(bench) > 0 else 0.0

        # Rebounding balance: minutes-weighted defensive rebounding rate across full roster.
        # Complements interior_dom (bigs, OR%) — this captures team-wide DR% commitment.
        valid_dr = df[df['dr_pct'].notna() & df['pct_min'].notna()]
        if len(valid_dr) > 0 and valid_dr['pct_min'].sum() > 0:
            rebounding_balance = float(
                (valid_dr['dr_pct'] * valid_dr['pct_min']).sum() / valid_dr['pct_min'].sum()
            )
        else:
            rebounding_balance = float('nan')

        # Foul drawing: minutes-weighted fd_per40 across top-8 rotation.
        # Teams that draw fouls force opponents into bonus early; a key tournament lever.
        # High fd_per40 = creates free throw opportunities regardless of FT accuracy.
        valid_fd = rotation8[rotation8['fd_per40'].notna() & rotation8['pct_min'].notna()]
        if len(valid_fd) > 0 and valid_fd['pct_min'].sum() > 0:
            foul_drawing = float(
                (valid_fd['fd_per40'] * valid_fd['pct_min']).sum() / valid_fd['pct_min'].sum()
            )
        else:
            foul_drawing = float('nan')

        # Foul trouble risk: minutes-weighted fc_per40 across top-5 players by minutes.
        # Key players who foul out or sit early change tournament game dynamics dramatically.
        top5 = df.nlargest(5, 'pct_min')
        valid_fc = top5[top5['fc_per40'].notna() & top5['pct_min'].notna()]
        if len(valid_fc) > 0 and valid_fc['pct_min'].sum() > 0:
            foul_trouble_risk = float(
                (valid_fc['fc_per40'] * valid_fc['pct_min']).sum() / valid_fc['pct_min'].sum()
            )
        else:
            foul_trouble_risk = float('nan')

        # Average rotation height: minutes-weighted height (inches) of top-8 rotation.
        # Captures physical profile of the actual playing unit — distinct from interior_dom
        # which only measures big-man performance. A 6'8" avg rotation vs 6'2" is a
        # fundamentally different stylistic identity.
        valid_h = rotation8[rotation8['height_in'].notna() & rotation8['pct_min'].notna()]
        if len(valid_h) > 0 and valid_h['pct_min'].sum() > 0:
            avg_rotation_height = float(
                (valid_h['height_in'] * valid_h['pct_min']).sum() / valid_h['pct_min'].sum()
            )
        else:
            avg_rotation_height = float('nan')

        # True shooting efficiency: minutes-weighted TS% of top-8 rotation.
        # TS% = pts / (2 × (fga + 0.44 × fta)) — accounts for 3-point value and free throws.
        # More holistic than fg2/fg3/ft separately; captures overall offensive efficiency
        # of the actual rotation independent of usage or role weighting.
        valid_ts = rotation8[rotation8['ts_pct'].notna() & rotation8['pct_min'].notna()]
        if len(valid_ts) > 0 and valid_ts['pct_min'].sum() > 0:
            ts_efficiency = float(
                (valid_ts['ts_pct'] * valid_ts['pct_min']).sum() / valid_ts['pct_min'].sum()
            )
        else:
            ts_efficiency = float('nan')

        # Rotation depth: count of players with ≥15% of team minutes.
        # Distinguishes 5-deep teams (one star + passengers) from 8-deep balanced rosters.
        # Threshold of 15% ≈ ~5.5 min/game in a 37-minute game — a real contributor, not a cameo.
        rotation_depth = int((df['pct_min'] >= 15).sum())

        rows.append({
            'team':               team_norm,
            'fr_min_pct':         fr_min_pct,
            'returning_min_pct':  returning_min_pct,
            'star_min_conc':      star_min_conc,
            'star_eup':           star_eup,
            'depth_eup':          depth_eup,
            'two_way_depth':      two_way_depth,
            'interior_dom':       interior_dom,
            'triple_threat':      triple_threat,
            'roster_seniority':   roster_seniority,
            'ft_clutch':          ft_clutch,
            'playmaker_quality':  playmaker_quality,
            'perimeter_depth':    perimeter_depth,
            'to_exposure':        to_exposure,
            'bench_depth':        bench_depth,
            'rebounding_balance': rebounding_balance,
            'foul_drawing':        foul_drawing,
            'foul_trouble_risk':   foul_trouble_risk,
            'avg_rotation_height': avg_rotation_height,
            'ts_efficiency':       ts_efficiency,
            'rotation_depth':      rotation_depth,
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).set_index('team')


# ── Matchup diff builder ───────────────────────────────────────────────────────

def build_player_matchup_df(
    bracket_df: pd.DataFrame,
    years: list[int],
) -> pd.DataFrame:
    """Build player feature diffs for every matchup in bracket_df.

    Args:
        bracket_df: Must have columns year, team1, team2.
        years:      Years to process (must match bracket_df years).

    Returns:
        DataFrame with same index as bracket_df plus PLAYER_DIFF_FEATURES
        columns. Rows where either team has no player data get NaN diffs.
    """
    print(f'Loading player features for {len(years)} seasons...')
    player_tables: dict[int, pd.DataFrame] = {
        y: load_player_features(y) for y in years
    }

    diff_rows = []
    for _, game in bracket_df.iterrows():
        year  = int(game['year'])
        t1    = game['team1']
        t2    = game['team2']
        table = player_tables.get(year, pd.DataFrame())

        row: dict = {'year': year, 'team1': t1, 'team2': t2}
        if not table.empty and t1 in table.index and t2 in table.index:
            f1 = table.loc[t1]
            f2 = table.loc[t2]
            for feat in PLAYER_FEATURES:
                row[f'{feat}_diff'] = float(f1[feat]) - float(f2[feat])
        else:
            for feat in PLAYER_FEATURES:
                row[f'{feat}_diff'] = float('nan')

        diff_rows.append(row)

    return pd.DataFrame(diff_rows)
