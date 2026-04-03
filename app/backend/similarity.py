"""Dual similarity engine: team-stat space + player-stat space.

Scoring: Gaussian decay — score = 100 * exp(-0.5 * (d / (1.5 * sigma))^2)
where sigma = median distance of ALL historical teams from the query.

The 1.5x sigma multiplier corrects for the curse of dimensionality: with 35+
team features and 20+ player features, Euclidean distances compress together in
high-D space — even the nearest neighbor is only ~37% closer than the median
team. Without the multiplier, the best realistic match scores ~82; with 1.5x,
top matches reach 90-95 and the scale is actually usable:

  d=0:              100  (identical clone)
  d=0.5*sigma:       94  (extremely similar)
  d=sigma:           80  (very similar — above median pool)
  d=1.5*sigma:       61  (moderately similar — median pool team)
  d=2*sigma:         41  (somewhat similar)
  d=2.5*sigma:       25  (weak match)

Combined distance: each space is normalized to unit-median before blending so
the team_weight/player_weight slider actually controls the contribution split.
Raw Euclidean distances scale with sqrt(D), so without normalization a 35-feature
team space would dominate a 20-feature player space regardless of the weights.
"""

import numpy as np


KEY_TEAM_STATS   = ['AdjEM', 'AdjOE', 'AdjDE', 'AdjTempo',
                    'efg_pct_off', 'efg_pct_def', 'to_pct_off', 'to_pct_def',
                    'or_pct_off', 'ftr_off', 'blk_pct_def', 'stl_rate_def',
                    'd1_exp', 'avg_height', 'program_tourney_rate_l5']

KEY_PLAYER_STATS = ['star_eup', 'depth_eup', 'triple_threat', 'interior_dom',
                    'two_way_depth', 'returning_min_pct', 'star_min_conc',
                    'roster_seniority', 'ft_clutch', 'ts_efficiency',
                    'rotation_depth', 'avg_rotation_height', 'perimeter_depth']


_SIGMA_SCALE = 1.5  # broadens the Gaussian so top matches reach 90-95 range


def _gauss_sim(dists: np.ndarray) -> np.ndarray:
    """Convert distance array to 0-100 Gaussian similarity scores.

    sigma = 1.5 * median distance. The 1.5 multiplier corrects for high-D distance
    compression: without it, best matches cluster at 80-85 because the nearest
    neighbor is only ~37% closer than the median team (curse of dimensionality).
    Scores above 61 mean closer than the median pool team.
    """
    sigma = float(np.median(dists)) * _SIGMA_SCALE
    if sigma < 1e-9:
        sigma = 1.0
    sims = 100.0 * np.exp(-0.5 * (dists / sigma) ** 2)
    return np.clip(np.round(sims), 0, 100).astype(int)


def _median_normalize(dists: np.ndarray) -> np.ndarray:
    """Scale distances so their median = 1.0.

    This makes distances from spaces with different dimensionality comparable
    before blending. Without this, a 35-feature team space produces naturally
    larger Euclidean distances than a 20-feature player space (scales with sqrt(D)),
    so the weight slider would be misleading.
    """
    med = float(np.median(dists))
    return dists / med if med > 1e-9 else dists


def find_similar(
    cache,
    query_year: int,
    query_team: str,
    top_n: int = 10,
    team_weight: float = 0.40,
    player_weight: float = 0.60,
) -> list[dict]:
    """Find top-N historical tournament teams most similar to query.

    Returns list sorted by combined_sim descending.
    """
    team_z_q, player_z_q, raw_row = cache.get_query_z(query_year, query_team)
    if team_z_q is None:
        return []

    hist_team_z   = cache.hist_team_z
    hist_player_z = cache.hist_player_z

    # ── Team space ────────────────────────────────────────────────────────────
    has_team = (hist_team_z is not None and hist_team_z.shape[1] > 0 and len(team_z_q) > 0)
    if has_team:
        team_dists = np.sqrt(((hist_team_z - team_z_q) ** 2).sum(axis=1))
        team_sims  = _gauss_sim(team_dists)
    else:
        team_dists = np.zeros(len(cache.teams_meta))
        team_sims  = np.full(len(cache.teams_meta), 50)

    # ── Player space ──────────────────────────────────────────────────────────
    has_player = (hist_player_z is not None and hist_player_z.shape[1] > 0 and len(player_z_q) > 0)
    if has_player:
        player_dists = np.sqrt(((hist_player_z - player_z_q) ** 2).sum(axis=1))
        player_sims  = _gauss_sim(player_dists)
    else:
        player_dists = np.zeros(len(cache.teams_meta))
        player_sims  = np.full(len(cache.teams_meta), 50)

    # ── Combined: normalize to unit-median per space, then blend ─────────────
    # Individual sims use raw distances (self-calibrated per space via Gaussian).
    # Combined uses median-normalized distances so the weight slider is honest:
    # "60% player" means player contributes 60% of the combined distance signal,
    # not 60% of a number that's inherently larger due to higher dimensionality.
    tw = team_weight / (team_weight + player_weight) if (team_weight + player_weight) > 0 else 0.5
    pw = 1.0 - tw

    if has_team and has_player:
        combined_dists = tw * _median_normalize(team_dists) + pw * _median_normalize(player_dists)
        combined_sims  = _gauss_sim(combined_dists)
    elif has_team:
        combined_sims = team_sims.copy()
    elif has_player:
        combined_sims = player_sims.copy()
    else:
        combined_sims = np.full(len(cache.teams_meta), 50)

    # Rank by combined, exclude self
    ranked = sorted(range(len(cache.teams_meta)), key=lambda i: -combined_sims[i])

    results = []
    for i in ranked:
        meta = cache.teams_meta[i]
        if meta['team'] == query_team and meta['year'] == query_year:
            continue
        if len(results) >= top_n:
            break

        match_stats = cache.get_raw_stats(meta['year'], meta['team']) or {}
        results.append({
            **meta,
            'team_sim':     int(team_sims[i]),
            'player_sim':   int(player_sims[i]),
            'combined_sim': int(combined_sims[i]),
            'key_stats':    _select_key_stats(match_stats),
        })

    return results


def get_query_profile(cache, year: int, team: str) -> dict | None:
    """Return raw stats + metadata for the query team."""
    _, _, raw_row = cache.get_query_z(year, team)
    if raw_row is None:
        return None

    raw  = cache.get_raw_stats(year, team) or {}
    meta = next((m for m in cache.teams_meta if m['team'] == team and m['year'] == year), None)

    seed        = raw.get('seed') or (meta['seed'] if meta else None)
    adj_em      = raw.get('AdjEM')
    adj_em_rank = raw.get('RankAdjEM')

    return {
        'team':        team,
        'year':        year,
        'seed':        seed,
        'adj_em':      adj_em,
        'adj_em_rank': adj_em_rank,
        'max_round':   meta['max_round']   if meta else None,
        'round_label': meta['round_label'] if meta else None,
        'is_champion': meta['is_champion'] if meta else None,
        'key_stats':   _select_key_stats(raw),
    }


def _select_key_stats(raw: dict) -> dict:
    out = {}
    for k in KEY_TEAM_STATS + KEY_PLAYER_STATS:
        if k in raw and raw[k] is not None:
            out[k] = raw[k]
    return out
