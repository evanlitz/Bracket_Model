"""DataCache: precomputes all historical tournament team feature vectors at startup.

Dual feature spaces:
  - Team space:   KenPom efficiency + scouting + rolling + program pedigree
  - Player space: roster composition (fr%, star EUP, depth, interior dom, etc.)

Within-year z-score normalization removes KenPom efficiency inflation across eras,
so a 2005 champion is directly comparable to a 2024 champion.

Non-historical years (e.g. 2026) use the global average of all historical
tournament-field normalizations, placing the query in the same z-space as the
historical pool so Euclidean distances are meaningful.
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd

# Make project root importable from app/backend/
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.kenpom import load_kenpom
from src.names import normalize_name
from src.features import load_season_scouting, SCOUTING_FEATURES
from src.player_features import load_player_features, PLAYER_FEATURES
from src.gameplan_features import load_pretournament_rolling, ROLLING_FEATURES, _load_cutoffs
from src.program_features import (
    _build_conf_lookup,
    _build_bracket_depth_lookup,
    load_program_features,
    PROGRAM_FEATURES as PROG_FEATURES,
)

DATA_DIR   = _ROOT / 'data'
CONFIG_DIR = _ROOT / 'config'
CACHE_FILE = DATA_DIR / 'datacache.pkl'
HIST_YEARS = [y for y in range(2002, 2026) if y != 2020]
KP_FEATURES = ['AdjOE', 'AdjDE', 'AdjTempo', 'AdjEM']

TEAM_FEATURE_CANDIDATES   = KP_FEATURES + SCOUTING_FEATURES + ROLLING_FEATURES + PROG_FEATURES
PLAYER_FEATURE_CANDIDATES = PLAYER_FEATURES


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_outcomes() -> pd.DataFrame:
    """Return one row per (team, year) that appeared in historical brackets.
    Columns: team, year, max_round, is_champion
    """
    records: dict[tuple, int] = {}
    champs:  dict[int, str]   = {}

    for year in HIST_YEARS:
        path = DATA_DIR / str(year) / 'bracket.csv'
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            rnd    = int(row['Round'])
            winner = normalize_name(str(row['Winner']))
            for col in ('Team1', 'Team2'):
                key = (normalize_name(str(row[col])), year)
                records[key] = max(records.get(key, 0), rnd)
            if rnd == 6:
                champs[year] = winner

    return pd.DataFrame([
        {'team': t, 'year': y, 'max_round': r, 'is_champion': t == champs.get(y, '')}
        for (t, y), r in records.items()
    ])


def _load_regions() -> pd.DataFrame:
    """Return {(team, year): region} from bracket.csv round-1 games."""
    rows = []
    for year in HIST_YEARS:
        path = DATA_DIR / str(year) / 'bracket.csv'
        if not path.exists():
            continue
        df = pd.read_csv(path)
        r1 = df[df['Round'] == 1]
        for _, row in r1.iterrows():
            region = str(row['Region'])
            for col in ('Team1', 'Team2'):
                rows.append({'team': normalize_name(str(row[col])), 'year': year, 'region': region})
    rdf = pd.DataFrame(rows)
    return rdf.drop_duplicates(['team', 'year'])


def _load_team_stats(year: int, conf_lkp, bracket_lkp, cutoffs: dict) -> pd.DataFrame:
    """All feature types for year, indexed by normalized team name."""
    kp = load_kenpom(year).copy()
    kp['TeamName'] = kp['TeamName'].map(normalize_name)
    kp['seed'] = kp['seed'].astype(float)
    kp = kp.set_index('TeamName')

    sc = load_season_scouting(year)
    if not sc.empty:
        sc_cols = [c for c in SCOUTING_FEATURES if c in sc.columns]
        kp = kp.join(sc[sc_cols], how='left')

    pl = load_player_features(year)
    if not pl.empty:
        kp = kp.join(pl[PLAYER_FEATURES], how='left')

    if year in cutoffs:
        rl = load_pretournament_rolling(year, cutoffs[year])
        if not rl.empty:
            rl_cols = [c for c in ROLLING_FEATURES if c in rl.columns]
            kp = kp.join(rl[rl_cols], how='left')

    prog = load_program_features(year, conf_lkp, bracket_lkp)
    if not prog.empty:
        kp = kp.join(prog[PROG_FEATURES], how='left')

    return kp


def _round_label(max_round: int) -> str:
    return {1: 'R64', 2: 'R32', 3: 'Sweet 16', 4: 'Elite 8',
            5: 'Final Four', 6: 'Champion'}.get(max_round, f'R{max_round}')


# ── DataCache ──────────────────────────────────────────────────────────────────

class DataCache:
    """Precomputed feature matrix for all historical tournament team-seasons.

    Attributes after .build():
        teams_meta    list[dict] — metadata for each of the N tournament teams
        hist_team_z   np.ndarray [N, D_team]   — within-year z-scores, team space
        hist_player_z np.ndarray [N, D_player] — within-year z-scores, player space
        team_feats    list[str]  — feature names for hist_team_z columns
        player_feats  list[str]  — feature names for hist_player_z columns
        raw_df        pd.DataFrame — raw (unnormalized) values, same row order as meta
        _year_team_mu/sig    dict[int, pd.Series] — per-year normalization for team feats
        _year_player_mu/sig  dict[int, pd.Series] — per-year normalization for player feats
        seed_lkp      dict[(team,year)->float] — KenPom seeds
    """

    def __init__(self):
        self.teams_meta: list[dict] = []
        self.hist_team_z: np.ndarray | None = None
        self.hist_player_z: np.ndarray | None = None
        self.team_feats: list[str] = []
        self.player_feats: list[str] = []
        self.raw_df: pd.DataFrame | None = None
        self._year_team_mu: dict  = {}
        self._year_team_sig: dict = {}
        self._year_player_mu: dict  = {}
        self._year_player_sig: dict = {}
        self.seed_lkp: dict = {}
        self._player_path_index: dict = {}   # {(year, team): Path}
        self._player_roster_cache: dict = {} # {(year, team): list[dict]}
        self._conf_yearly_lkp: dict = {}     # {(team, year): conf_str}
        # raw stats for a query team (team+year that's NOT in hist pool)
        self._query_raw_cache: dict = {}

    def build(self):
        print('[DataCache] Building lookups...')
        conf_lkp    = _build_conf_lookup()
        bracket_lkp = _build_bracket_depth_lookup()
        cutoffs     = _load_cutoffs()

        print('[DataCache] Loading outcomes...')
        outcomes = _load_outcomes()
        outcomes_lkp = {
            (r['team'], r['year']): {'max_round': r['max_round'], 'is_champion': r['is_champion']}
            for _, r in outcomes.iterrows()
        }

        print('[DataCache] Loading regions...')
        regions_df = _load_regions()
        region_lkp = {(r['team'], r['year']): r['region'] for _, r in regions_df.iterrows()}

        print('[DataCache] Loading conferences...')
        conf_raw = pd.read_parquet(CONFIG_DIR / 'conferences.parquet')
        conf_raw['team'] = conf_raw['team'].map(normalize_name)
        conf_yearly_lkp = {(r['team'], r['season']): r['conf'] for _, r in conf_raw.iterrows()}
        self._conf_yearly_lkp = conf_yearly_lkp

        print('[DataCache] Loading all historical team stats...')
        frames = []
        for year in HIST_YEARS:
            try:
                df = _load_team_stats(year, conf_lkp, bracket_lkp, cutoffs)
                df = df.reset_index().rename(columns={'TeamName': 'team', 'index': 'team'})
                df['year'] = year
                frames.append(df)
            except Exception as e:
                print(f'  {year}: skipped — {e}')

        full_df = pd.concat(frames, ignore_index=True)

        # Join outcomes, filter to tournament teams
        full_df = full_df.merge(outcomes, on=['team', 'year'], how='inner')
        full_df = full_df[full_df['seed'].notna()].copy()
        full_df = full_df.reset_index(drop=True)
        print(f'  {len(full_df)} tournament team-seasons across {full_df["year"].nunique()} years')

        # Seed lookup (for all D1 teams)
        for _, row in full_df.iterrows():
            self.seed_lkp[(row['team'], int(row['year']))] = float(row['seed'])

        # Also load 2026 for seed lookup (even though seeds aren't assigned yet)
        try:
            kp26 = load_kenpom(2026)
            kp26['TeamName'] = kp26['TeamName'].map(normalize_name)
            for _, r in kp26.iterrows():
                if pd.notna(r['seed']):
                    self.seed_lkp[(r['TeamName'], 2026)] = float(r['seed'])
        except Exception:
            pass

        # Auto-detect team features (≥50% coverage in tournament teams, >100 hist rows)
        all_possible_team = [f for f in TEAM_FEATURE_CANDIDATES if f in full_df.columns]
        team_feats = [
            f for f in all_possible_team
            if full_df[f].notna().mean() >= 0.20  # looser threshold for hist pool
            and full_df[f].notna().sum() > 100
        ]

        # Auto-detect player features
        all_possible_player = [f for f in PLAYER_FEATURE_CANDIDATES if f in full_df.columns]
        player_feats = [
            f for f in all_possible_player
            if full_df[f].notna().mean() >= 0.20
            and full_df[f].notna().sum() > 100
        ]

        self.team_feats   = team_feats
        self.player_feats = player_feats
        print(f'  Team features ({len(team_feats)}): {team_feats}')
        print(f'  Player features ({len(player_feats)}): {player_feats}')

        # Within-year z-normalization — team space
        for feat_list, z_attr, mu_dict, sig_dict in [
            (team_feats,   'hist_team_z',   self._year_team_mu,   self._year_team_sig),
            (player_feats, 'hist_player_z', self._year_player_mu, self._year_player_sig),
        ]:
            if not feat_list:
                setattr(self, z_attr, np.zeros((len(full_df), 0)))
                continue
            mu_yr  = full_df.groupby('year')[feat_list].transform('mean')
            sig_yr = full_df.groupby('year')[feat_list].transform('std').fillna(1).replace(0, 1)
            z_df   = ((full_df[feat_list] - mu_yr) / sig_yr).fillna(0)
            setattr(self, z_attr, z_df.values.astype(np.float32))
            for yr in full_df['year'].unique():
                mask = full_df['year'] == yr
                mu_dict[yr]  = full_df.loc[mask, feat_list].mean()
                sig_dict[yr] = full_df.loc[mask, feat_list].std().fillna(1).replace(0, 1)

        # Load 2026 data for query use (no special normalization — _znorm_row falls
        # through to global historical average, keeping it in the same z-space)
        try:
            df26 = _load_team_stats(2026, conf_lkp, bracket_lkp, cutoffs)
            df26 = df26.reset_index().rename(columns={'TeamName': 'team', 'index': 'team'})
            df26['year'] = 2026
            self._query_raw_cache[2026] = df26.set_index('team')
        except Exception as e:
            print(f'  2026 load: {e}')

        # Build metadata list (parallel to hist_team_z rows)
        self.teams_meta = []
        for _, row in full_df.iterrows():
            team = row['team']
            year = int(row['year'])
            self.teams_meta.append({
                'team':        team,
                'year':        year,
                'seed':        int(row['seed']) if pd.notna(row['seed']) else None,
                'conf':        conf_yearly_lkp.get((team, year), ''),
                'region':      region_lkp.get((team, year), ''),
                'max_round':   int(row['max_round']),
                'round_label': _round_label(int(row['max_round'])),
                'is_champion': bool(row['is_champion']),
            })

        self.raw_df = full_df.reset_index(drop=True)

        # ── Player roster path index ───────────────────────────────────────────
        # Build from filenames only — no file reads needed.
        # Files are named: {Team_Name}_players.parquet (underscores for spaces)
        print('[DataCache] Indexing player roster files...')
        for year in HIST_YEARS + [2026]:
            player_dir = DATA_DIR / str(year) / 'players'
            if not player_dir.exists():
                continue
            for p in player_dir.glob('*.parquet'):
                raw = p.stem.removesuffix('_players').replace('_', ' ')
                tn  = normalize_name(raw)
                self._player_path_index[(year, tn)] = p

        print('[DataCache] Saving cache to disk...')
        try:
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f'[DataCache] Cache saved → {CACHE_FILE}')
        except Exception as e:
            print(f'[DataCache] Cache save failed: {e}')

        print('[DataCache] Build complete.')

    # ── Query team z-vector ────────────────────────────────────────────────────

    def get_query_z(self, year: int, team: str):
        """Return (team_z, player_z) numpy arrays for a query (year, team).

        Returns None if team not found for that year.
        For historical tournament teams, pulls from cached raw_df.
        For 2026 or non-tournament teams, loads fresh.
        """
        # Check if it's in the historical pool
        if self.raw_df is not None:
            mask = (self.raw_df['team'] == team) & (self.raw_df['year'] == year)
            if mask.any():
                row = self.raw_df[mask].iloc[0]
                team_z   = self._znorm_row(row, self.team_feats,   year, 'team')
                player_z = self._znorm_row(row, self.player_feats, year, 'player')
                return team_z, player_z, row

        # Try cached year data
        if year in self._query_raw_cache:
            df_yr = self._query_raw_cache[year]
            if team in df_yr.index:
                row = df_yr.loc[team]
                team_z   = self._znorm_row(row, self.team_feats,   year, 'team')
                player_z = self._znorm_row(row, self.player_feats, year, 'player')
                return team_z, player_z, row

        return None, None, None

    def _znorm_row(self, row, feats: list[str], year: int, space: str) -> np.ndarray:
        """Z-normalize a raw feature row for a given year and space.

        Historical tournament years use that year's tournament-field mu/sig.
        Any other year (e.g. 2026) uses the global average of all historical
        tournament-field normalizations, putting the query in the same z-space
        as the historical pool so Euclidean distances are meaningful.
        """
        if not feats:
            return np.zeros(0, dtype=np.float32)

        vals = pd.to_numeric(pd.Series({f: row.get(f, float('nan')) for f in feats}), errors='coerce')

        mu_dict  = self._year_team_mu   if space == 'team' else self._year_player_mu
        sig_dict = self._year_team_sig  if space == 'team' else self._year_player_sig

        if year in mu_dict:
            mu  = mu_dict[year]
            sig = sig_dict[year]
        else:
            mu  = pd.concat(mu_dict.values(),  axis=1).mean(axis=1) if mu_dict  else pd.Series()
            sig = pd.concat(sig_dict.values(), axis=1).mean(axis=1) if sig_dict else pd.Series()

        if mu is None or len(mu) == 0:
            return np.zeros(len(feats), dtype=np.float32)

        z = ((vals - mu) / sig).fillna(0).values.astype(np.float32)
        return z

    def get_raw_stats(self, year: int, team: str) -> dict | None:
        """Return raw feature values for a team as a plain dict."""
        if self.raw_df is not None:
            mask = (self.raw_df['team'] == team) & (self.raw_df['year'] == year)
            if mask.any():
                row = self.raw_df[mask].iloc[0]
                return _row_to_stats_dict(row, self.team_feats + self.player_feats)

        if year in self._query_raw_cache:
            df_yr = self._query_raw_cache[year]
            if team in df_yr.index:
                row = df_yr.loc[team]
                return _row_to_stats_dict(row, self.team_feats + self.player_feats)

        return None

    def get_player_roster(self, year: int, team: str) -> list[dict]:
        """Return top players by minutes for (year, team), cached after first load."""
        key = (year, team)
        if key in self._player_roster_cache:
            return self._player_roster_cache[key]

        path = self._player_path_index.get(key)
        if path is None:
            self._player_roster_cache[key] = []
            return []

        try:
            df = pd.read_parquet(path)
            df = df.dropna(subset=['pct_min']).sort_values('pct_min', ascending=False).head(10)
            result = []
            for _, r in df.iterrows():
                # Compute PPG from raw counting stats
                games  = r.get('games')
                ftm    = r.get('ftm', 0) or 0
                fg2m   = r.get('fg2m', 0) or 0
                fg3m   = r.get('fg3m', 0) or 0
                pts    = ftm + 2 * fg2m + 3 * fg3m
                ppg    = round(pts / games, 1) if games and games > 0 else None
                # Overall FG%
                fg2a   = r.get('fg2a', 0) or 0
                fg3a   = r.get('fg3a', 0) or 0
                fga    = fg2a + fg3a
                fgm    = fg2m + fg3m
                fg_pct = round(fgm / fga * 100, 1) if fga > 0 else None
                result.append({
                    'name':       str(r.get('name', '')),
                    'year_class': str(r.get('year', '')),
                    'starter':    bool(r.get('starter', False)),
                    'height':     str(r.get('height', '')),
                    # ESPN box score order
                    'games':      int(games) if games is not None else None,
                    'ppg':        ppg,
                    'fg_pct':     fg_pct,
                    'fg3_pct':    _sf(r.get('fg3_pct'), 3),
                    'ft_pct':     _sf(r.get('ft_pct'), 3),
                    'or_pct':     _sf(r.get('or_pct'), 1),
                    'dr_pct':     _sf(r.get('dr_pct'), 1),
                    'a_rate':     _sf(r.get('a_rate'), 1),
                    'to_rate':    _sf(r.get('to_rate'), 1),
                    'stl_pct':    _sf(r.get('stl_pct'), 1),
                    'blk_pct':    _sf(r.get('blk_pct'), 1),
                    # Advanced
                    'pct_min':    _sf(r.get('pct_min'), 1),
                    'ortg':       _sf(r.get('ortg'), 0),
                    'pct_poss':   _sf(r.get('pct_poss'), 1),
                    'efg_pct':    _sf(r.get('efg_pct'), 3),
                    'ts_pct':     _sf(r.get('ts_pct'), 3),
                })
        except Exception:
            result = []

        self._player_roster_cache[key] = result
        return result

    def all_tournament_teams(self) -> list[dict]:
        """Return sorted list of all {team, year, seed, conf} for the selector.

        Includes historical tournament teams + 2026 top-200 by AdjEM rank.
        """
        seen = set()
        result = []
        for meta in self.teams_meta:
            key = (meta['team'], meta['year'])
            if key not in seen:
                seen.add(key)
                result.append(meta)

        # Add 2026 teams (pre-tournament — no seed/bracket data yet)
        if 2026 in self._query_raw_cache:
            df26 = self._query_raw_cache[2026]
            for team, row in df26.iterrows():
                if (team, 2026) in seen:
                    continue
                rank = row.get('RankAdjEM')
                if pd.isna(rank) or int(rank) > 200:
                    continue
                seen.add((team, 2026))
                result.append({
                    'team':        team,
                    'year':        2026,
                    'seed':        None,
                    'conf':        self._conf_yearly_lkp.get((team, 2025), ''),
                    'region':      '',
                    'max_round':   None,
                    'round_label': None,
                    'is_champion': False,
                })

        return sorted(result, key=lambda x: (x['year'], x['seed'] or 999, x['team']))


def _sf(v, decimals: int = 2):
    """Safe float conversion; returns None on NaN/None."""
    try:
        f = float(v)
        return None if np.isnan(f) else round(f, decimals)
    except (TypeError, ValueError):
        return None


def _row_to_stats_dict(row, feats: list[str]) -> dict:
    out = {}
    for f in feats:
        v = row.get(f)
        if v is not None and pd.notna(v):
            out[f] = round(float(v), 4)
        else:
            out[f] = None
    # Always include key display fields
    for col in ['AdjEM', 'AdjOE', 'AdjDE', 'AdjTempo', 'seed', 'RankAdjEM']:
        v = row.get(col)
        if col not in out:
            out[col] = round(float(v), 2) if (v is not None and pd.notna(v)) else None
    return out


def build_or_load() -> DataCache:
    """Return a ready DataCache — from disk cache if available, else build fresh.

    Delete data/datacache.pkl to force a full rebuild.
    """
    if CACHE_FILE.exists():
        print(f'[DataCache] Loading from cache ({CACHE_FILE.name})...')
        try:
            with open(CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
            print('[DataCache] Cache loaded.')
            return cache
        except Exception as e:
            print(f'[DataCache] Cache load failed ({e}), rebuilding...')

    cache = DataCache()
    cache.build()
    return cache
