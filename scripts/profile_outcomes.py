"""
Outcome archetype profiles from historical tournament data (2002-2025).

Builds three archetypes from historical NCAA tournament teams:
  - Champion     : won the national championship
  - Final Four   : reached the Final Four (includes champs)
  - Upset Victim : seeded 1-6, lost in Round 1

For each 2026 top-100 team (by AdjEM rank), computes a 0-100 similarity score
for each archetype.  Score = percentile: "more similar than X% of historical
tournament teams."  Higher is more archetype-like.

Features used are auto-detected: any feature available for >= 50% of 2026
top-100 teams AND with > 100 non-NaN historical rows is included.
Initially (before 2026 scrapers run): KenPom + program only.
After scrapers: scouting + player + rolling features added automatically.

Output: analysis/outcome_profiles.md
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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

DATA_DIR     = Path('data')
ANALYSIS_DIR = Path('analysis')
ANALYSIS_DIR.mkdir(exist_ok=True)

KP_FEATURES  = ['AdjOE', 'AdjDE', 'AdjTempo', 'AdjEM']
HIST_YEARS   = [y for y in range(2002, 2026) if y != 2020]

ALL_FEATURE_CANDIDATES = (
    KP_FEATURES + SCOUTING_FEATURES + PLAYER_FEATURES + ROLLING_FEATURES + PROG_FEATURES
)


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_outcomes() -> pd.DataFrame:
    """Return one row per team-year that appeared in historical brackets.

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


def load_team_stats(year: int, conf_lkp, bracket_lkp, cutoffs: dict) -> pd.DataFrame:
    """All feature types for *year*, indexed by normalized team name.

    Loads KenPom, scouting, player, rolling, and program features.
    Returns NaN columns for any source that has no data for the given year.
    """
    kp = load_kenpom(year).copy()
    kp['TeamName'] = kp['TeamName'].map(normalize_name)
    kp['seed']     = kp['seed'].astype(float)
    kp = kp.set_index('TeamName')

    # Scouting
    sc = load_season_scouting(year)
    if not sc.empty:
        sc_cols = [c for c in SCOUTING_FEATURES if c in sc.columns]
        kp = kp.join(sc[sc_cols], how='left')

    # Player
    pl = load_player_features(year)
    if not pl.empty:
        kp = kp.join(pl[PLAYER_FEATURES], how='left')

    # Rolling (pre-tournament game logs)
    if year in cutoffs:
        rl = load_pretournament_rolling(year, cutoffs[year])
        if not rl.empty:
            rl_cols = [c for c in ROLLING_FEATURES if c in rl.columns]
            kp = kp.join(rl[rl_cols], how='left')

    # Program pedigree
    prog = load_program_features(year, conf_lkp, bracket_lkp)
    if not prog.empty:
        kp = kp.join(prog[PROG_FEATURES], how='left')

    return kp


# ── Core logic ─────────────────────────────────────────────────────────────────

def compute_similarity(z_vec: np.ndarray, centroid: np.ndarray,
                       hist_dists: np.ndarray,
                       weights: np.ndarray | None = None) -> int:
    """Return percentile similarity (0-100): % of hist tournament teams farther from centroid."""
    w = weights if weights is not None else np.ones(len(centroid))
    d = float(np.sqrt((w * (z_vec - centroid) ** 2).sum()))
    return int(round(100 * (hist_dists > d).mean()))


# ── Main ───────────────────────────────────────────────────────────────────────

print('Loading historical tournament outcomes...')
outcomes = load_outcomes()

print('Building lookups...')
conf_lkp    = _build_conf_lookup()
bracket_lkp = _build_bracket_depth_lookup()
cutoffs     = _load_cutoffs()

print('Loading historical team features...')
frames = []
for year in HIST_YEARS:
    try:
        df = load_team_stats(year, conf_lkp, bracket_lkp, cutoffs)
        df = df.reset_index().rename(columns={'TeamName': 'team'})
        df['year'] = year
        frames.append(df)
    except Exception as e:
        print(f'  {year}: skipped — {e}')

hist_df = pd.concat(frames, ignore_index=True)
hist_df = hist_df.merge(outcomes, on=['team', 'year'], how='inner')
hist_df = hist_df[hist_df['seed'].notna()].copy()
print(f'  {len(hist_df)} tournament team-seasons, {hist_df["year"].nunique()} years')

# ── Load 2026 top-100 ──────────────────────────────────────────────────────────

print('\nLoading 2026 data...')
kp26   = load_team_stats(2026, conf_lkp, bracket_lkp, cutoffs)
top100 = kp26[kp26['RankAdjEM'] <= 100].copy()
print(f'  {len(top100)} teams in top-100 by AdjEM rank')

# Determine which features to use:
# - must be a column in top100
# - >= 50% of 2026 top-100 teams must have a non-NaN value
# - must have > 100 non-NaN rows in historical data
use_features = [
    f for f in ALL_FEATURE_CANDIDATES
    if f in top100.columns
    and top100[f].notna().mean() >= 0.50
    and f in hist_df.columns
    and hist_df[f].notna().sum() > 100
]
print(f'  {len(use_features)} features in use: {use_features}')

# ── Archetypes ─────────────────────────────────────────────────────────────────

champions     = hist_df[hist_df['is_champion']]
final_four    = hist_df[hist_df['max_round'] >= 5]
upset_victims = hist_df[(hist_df['seed'] <= 6) & (hist_df['max_round'] == 1)]
cinderellas   = hist_df[(hist_df['seed'] >= 11) & (hist_df['max_round'] >= 2)]
# Weight cinderellas by how far they advanced: won R1 only = 1, Sweet 16 = 2, etc.
cin_adv_w     = (cinderellas['max_round'] - 1).values

print(f'\nArchetype sizes:')
print(f'  Champions:     {len(champions)}')
print(f'  Final Four:    {len(final_four)}')
print(f'  Upset Victims: {len(upset_victims)}  (seeds 1-6 lost R1)')
print(f'  Cinderellas:   {len(cinderellas)}  (seeds 11-16 won R1, weighted by advancement)')

# ── Within-year normalization (removes KenPom efficiency inflation) ────────────
# Each team's z-score = how far above/below that year's tournament field average.
# This makes a 2005 champion directly comparable to a 2024 champion.

year_mu  = hist_df.groupby('year')[use_features].transform('mean')
year_sig = hist_df.groupby('year')[use_features].transform('std').fillna(1).replace(0, 1)

hist_z_df = ((hist_df[use_features] - year_mu) / year_sig).fillna(0)
hist_z    = hist_z_df.values

# Centroids = mean within-year z-score for each archetype
champ_z = hist_z_df.loc[champions.index].values.mean(axis=0)
f4_z    = hist_z_df.loc[final_four.index].values.mean(axis=0)
upset_z = hist_z_df.loc[upset_victims.index].values.mean(axis=0)
# Cinderella centroid: weighted mean (teams that went further count more)
cin_z   = np.average(hist_z_df.loc[cinderellas.index].values, weights=cin_adv_w, axis=0)

# For 2026: normalize against the top-100 pool (best available proxy for the
# 2026 tournament field before seeds are announced)
mu26  = top100[use_features].mean()
sig26 = top100[use_features].std().replace(0, 1)

# Filter to features that discriminate at least one archetype (|z| > 0.10)
max_abs_z  = np.abs(np.stack([champ_z, f4_z, upset_z, cin_z])).max(axis=0)
disc_mask  = max_abs_z > 0.10
disc_feats = [f for f, m in zip(use_features, disc_mask) if m]
print(f'  {len(disc_feats)}/{len(use_features)} discriminating features (|z|>0.10): {disc_feats}')

champ_z = champ_z[disc_mask]
f4_z    = f4_z[disc_mask]
upset_z = upset_z[disc_mask]
cin_z   = cin_z[disc_mask]
hist_z  = hist_z[:, disc_mask]

# Per-archetype weights = squared effect size, normalized to preserve scale
def _weights(cvec: np.ndarray) -> np.ndarray:
    w = cvec ** 2
    s = w.sum()
    return w / s * len(cvec) if s > 0 else np.ones(len(cvec))

champ_weights = _weights(champ_z)
f4_weights    = _weights(f4_z)
upset_weights = _weights(upset_z)

# Cinderella scoring ignores program pedigree — cinderellas by definition
# lack blue-blood history, so those features would just penalize them.
cin_z_adj = cin_z.copy()
for f in PROG_FEATURES:
    if f in disc_feats:
        cin_z_adj[disc_feats.index(f)] = 0.0
cin_weights = _weights(cin_z_adj)

# Pre-compute weighted historical distances
hist_dist_champ = np.sqrt((champ_weights * (hist_z - champ_z) ** 2).sum(axis=1))
hist_dist_f4    = np.sqrt((f4_weights    * (hist_z - f4_z)    ** 2).sum(axis=1))
hist_dist_upset = np.sqrt((upset_weights * (hist_z - upset_z) ** 2).sum(axis=1))
hist_dist_cin   = np.sqrt((cin_weights   * (hist_z - cin_z_adj) ** 2).sum(axis=1))

# ── Compute 2026 similarity scores ─────────────────────────────────────────────

mid_teams = kp26[(kp26['RankAdjEM'] >= 40) & (kp26['RankAdjEM'] <= 120)].copy()
print(f'  {len(mid_teams)} teams in ranks 40-120 for cinderella scoring')

print('\nComputing 2026 similarity scores...')
results = []

for team, row in top100.iterrows():
    z26 = ((pd.to_numeric(row[use_features], errors='coerce') - mu26) / sig26).fillna(0).values[disc_mask]

    def _get(col):
        v = row.get(col)
        return round(float(v), 2) if pd.notna(v) else None

    results.append({
        'team':           team,
        'em_rank':        int(row['RankAdjEM']),
        'adj_em':         round(float(row['AdjEM']), 2),
        'adj_oe':         round(float(row['AdjOE']), 1),
        'adj_de':         round(float(row['AdjDE']), 1),
        'prog_t5':        _get('program_tourney_rate_l5'),
        'prog_f4_10':     _get('program_f4_rate_l10'),
        'champion_sim':   compute_similarity(z26, champ_z, hist_dist_champ, champ_weights),
        'final_four_sim': compute_similarity(z26, f4_z,    hist_dist_f4,    f4_weights),
        'upset_risk':     compute_similarity(z26, upset_z, hist_dist_upset, upset_weights),
    })

results_df = pd.DataFrame(results).sort_values('champion_sim', ascending=False)

# Cinderella scores for ranks 40-120
cin_results = []
for team, row in mid_teams.iterrows():
    z26 = ((pd.to_numeric(row[use_features], errors='coerce') - mu26) / sig26).fillna(0).values[disc_mask]

    def _get(col):
        v = row.get(col)
        return round(float(v), 2) if pd.notna(v) else None

    cin_results.append({
        'team':        team,
        'em_rank':     int(row['RankAdjEM']),
        'adj_em':      round(float(row['AdjEM']), 2),
        'adj_oe':      round(float(row['AdjOE']), 1),
        'adj_de':      round(float(row['AdjDE']), 1),
        'prog_t5':     _get('program_tourney_rate_l5'),
        'prog_f4_10':  _get('program_f4_rate_l10'),
        'cin_sim':     compute_similarity(z26, cin_z_adj, hist_dist_cin, cin_weights),
    })

cin_df = pd.DataFrame(cin_results).sort_values('cin_sim', ascending=False)

# ── Print archetype profiles ────────────────────────────────────────────────────

print('\n-- Archetype mean stats -------------------------------------------------')
profile_groups = {
    'All tournament teams':      hist_df,
    'Champions':                 champions,
    'Final Four':                final_four,
    'Upset victims (S1-6)':      upset_victims,
    'Cinderellas (S11-16 won R1)': cinderellas,
}
for label, grp in profile_groups.items():
    vals = {f: round(float(grp[f].mean()), 3) for f in use_features if f in grp.columns}
    print(f'\n  {label} (n={len(grp)}):')
    for k, v in vals.items():
        print(f'    {k:<35} {v}')

# ── Write markdown ──────────────────────────────────────────────────────────────

out_path = ANALYSIS_DIR / 'outcome_profiles.md'

lines = [
    '# 2026 Tournament Outcome Similarity Profiles',
    '',
    f'Features used ({len(use_features)}): {", ".join(use_features)}',
    '',
    '**Score interpretation:** percentile similarity — "more archetype-like than X% of',
    'historical tournament teams (2002-2025)."  100 = most similar, 0 = least similar.',
    '',
    '---',
    '',
    '## Archetype Mean Profiles',
    '',
    '| Stat | All Tourney | Champion | Final Four | Upset Victim | Cinderella |',
    '|---|---|---|---|---|---|',
]
for f in use_features:
    a  = round(float(hist_df[f].mean()), 3)
    c  = round(float(champions[f].mean()), 3)
    ff = round(float(final_four[f].mean()), 3)
    uv = round(float(upset_victims[f].mean()), 3) if len(upset_victims) > 0 else 'n/a'
    ci = round(float(cinderellas[f].mean()), 3) if len(cinderellas) > 0 else 'n/a'
    lines.append(f'| {f} | {a} | {c} | {ff} | {uv} | {ci} |')

lines += [
    '',
    f'*Champions: {len(champions)} | Final Four: {len(final_four)} | '
    f'Upset Victims (seeds 1-6 lost R1): {len(upset_victims)} | '
    f'Cinderellas (seeds 11-16 won R1): {len(cinderellas)}*',
    '',
    '---',
    '',
    '## 2026 Team Similarity Scores — Top 100 by AdjEM Rank',
    '',
    '> **upset_risk** is most meaningful for likely top seeds (~top 24 by AdjEM).',
    '> Seed assignments available after Selection Sunday.',
    '',
    '| Rank | Team | AdjEM | AdjOE | AdjDE | prog_t5 | prog_f4_10 | champion_sim | final_four_sim | upset_risk |',
    '|---|---|---|---|---|---|---|---|---|---|',
]

for _, r in results_df.iterrows():
    lines.append(
        f'| {r["em_rank"]} | {r["team"]} | {r["adj_em"]} | {r["adj_oe"]} | {r["adj_de"]} | '
        f'{r["prog_t5"]} | {r["prog_f4_10"]} | '
        f'{r["champion_sim"]} | {r["final_four_sim"]} | {r["upset_risk"]} |'
    )

lines += [
    '',
    '---',
    '',
    '## 2026 Cinderella Watch — KenPom Ranks 40-120',
    '',
    '> Similarity to historical seeds 11-16 that won at least one tournament game.',
    '> Weighted by advancement: teams reaching Sweet 16+ count more toward the archetype.',
    '',
    '| Rank | Team | AdjEM | AdjOE | AdjDE | prog_t5 | prog_f4_10 | cin_sim |',
    '|---|---|---|---|---|---|---|---|',
]
for _, r in cin_df.iterrows():
    lines.append(
        f'| {r["em_rank"]} | {r["team"]} | {r["adj_em"]} | {r["adj_oe"]} | {r["adj_de"]} | '
        f'{r["prog_t5"]} | {r["prog_f4_10"]} | {r["cin_sim"]} |'
    )

lines += [
    '',
    '---',
    '',
    '## Notes',
    '',
    '- **champion_sim**: closeness to historical champion stat profile. Program pedigree',
    '  (tourney_rate_l5, f4_rate_l10) matters as much as raw efficiency.',
    '- **final_four_sim**: closeness to teams that reached the Final Four.',
    '- **upset_risk**: closeness to seeds 1-6 that lost in Round 1. High value for a',
    '  top-ranked team is a red flag — they resemble historical false favorites.',
    '- **cin_sim**: closeness to seeds 11-16 that won R1. Centroid weighted by advancement',
    '  so Sweet 16 cinderellas (e.g. 12-seeds going deep) pull the archetype more than',
    '  one-and-done upsets. High cin_sim for a rank-40-120 team = potential bracket-buster.',
    '',
    f'*Generated from {len(hist_df)} historical tournament team-seasons '
    f'using {len(use_features)} features.*',
    f'*Features expand automatically as 2026 scrapers are run.*',
]

out_path.write_text('\n'.join(lines), encoding='utf-8')
print(f'\nWrote: {out_path}')

# ── Console preview ─────────────────────────────────────────────────────────────

print('\n-- Top 15 by champion_sim -----------------------------------------------')
cols = ['em_rank', 'team', 'adj_em', 'champion_sim', 'final_four_sim', 'upset_risk']
print(results_df[cols].head(15).to_string(index=False))

print('\n-- Top 15 upset_risk among top-30 by AdjEM -----------------------------')
top30 = results_df[results_df['em_rank'] <= 30]
print(top30.sort_values('upset_risk', ascending=False)[cols].head(15).to_string(index=False))

print('\n-- Top 20 cinderella candidates (ranks 40-120) --------------------------')
cin_cols = ['em_rank', 'team', 'adj_em', 'cin_sim']
print(cin_df[cin_cols].head(20).to_string(index=False))
