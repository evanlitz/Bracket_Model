"""FastAPI backend for the Team Similarity Machine.

Endpoints:
  GET /api/teams                          → all tournament team-seasons
  GET /api/team/{year}/{team}             → full stat profile
  GET /api/similar/{year}/{team}          → top-N similar teams
  GET /api/bracket/{year}/{team}          → game-by-game bracket path

Run with:
  uvicorn app.backend.main:app --reload --app-dir .
  (from project root: c:/Users/evan/OneDrive/CODE/Bracket_Model_26)
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

import json as _json
import numpy as np
import pandas as pd

from app.backend.data_loader import DataCache, build_or_load
from app.backend.similarity import find_similar, get_query_profile
from app.backend.bracket_path import get_bracket_path
from src.names import normalize_name
from src.features import DIFF_FEATURES

_DATA_DIR = _ROOT / 'data'
_CONFIG_DIR = _ROOT / 'config'
_MODEL_PATH = _ROOT / 'model.joblib'

# ── Global cache + model ───────────────────────────────────────────────────────

cache: DataCache | None = None
_model = None   # lazy-loaded trained model
_pmat_cache: dict = {}  # year → (teams_list, tidx, pmat) — invalidated on model reload


_INFERENCE_YEAR = 2026  # never train on the current prediction year

def _get_model():
    """Load or train the full-dataset model, cached in memory.

    Excludes _INFERENCE_YEAR from training so the model never sees
    tournament outcomes it is being asked to predict.
    """
    global _model
    if _model is not None:
        return _model
    import joblib
    if _MODEL_PATH.exists():
        _model = joblib.load(_MODEL_PATH)
        print('Model loaded from disk.')
    else:
        print('model.joblib not found — training now (~30s)...')
        from src.features import build_matchup_df
        from src.model import train, save
        df = build_matchup_df()
        df = df[df['year'] != _INFERENCE_YEAR]
        _model = train(df)
        save(_model, _MODEL_PATH)
        print('Model trained and saved.')
    return _model


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache
    cache = build_or_load()
    print('Data cache ready.')
    yield


app = FastAPI(title='Team Similarity Machine', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['GET'],
    allow_headers=['*'],
)

# ── API routes ────────────────────────────────────────────────────────────────

@app.get('/api/teams')
def list_teams():
    """All tournament team-seasons available for querying."""
    return cache.all_tournament_teams()


@app.get('/api/team/{year}/{team}')
def team_profile(year: int, team: str):
    """Full stat profile + metadata for a single team-season."""
    team_norm = normalize_name(team)
    profile = get_query_profile(cache, year, team_norm)
    if profile is None:
        raise HTTPException(404, f'{team} ({year}) not found')
    profile['player_roster'] = cache.get_player_roster(year, team_norm)
    return profile


@app.get('/api/similar/{year}/{team}')
def similar_teams(
    year: int,
    team: str,
    top_n: int       = Query(10, ge=1, le=20),
    team_weight: float  = Query(0.40, ge=0.0, le=1.0),
    player_weight: float = Query(0.60, ge=0.0, le=1.0),
):
    """Top-N most similar historical tournament teams."""
    team_norm = normalize_name(team)
    matches = find_similar(cache, year, team_norm, top_n, team_weight, player_weight)
    if not matches:
        raise HTTPException(404, f'{team} ({year}) not found or no matches')

    year_seed_lkps: dict[int, dict] = {}
    for m in matches:
        yr = m['year']
        if yr not in year_seed_lkps:
            year_seed_lkps[yr] = {
                t: d['seed']
                for t, d in [
                    (meta['team'], meta)
                    for meta in cache.teams_meta
                    if meta['year'] == yr and meta['seed'] is not None
                ]
            }
        m['bracket_path']  = get_bracket_path(yr, m['team'], year_seed_lkps[yr])
        m['player_roster'] = cache.get_player_roster(yr, m['team'])

    query = get_query_profile(cache, year, team_norm)
    if query:
        query['player_roster'] = cache.get_player_roster(year, team_norm)

    return {'query': query, 'matches': matches}


@app.get('/api/bracket/{year}/{team}')
def bracket_path(year: int, team: str):
    """Game-by-game tournament path for a historical team."""
    team_norm  = normalize_name(team)
    seed_lkp   = {m['team']: m['seed'] for m in cache.teams_meta if m['year'] == year and m['seed'] is not None}
    path       = get_bracket_path(year, team_norm, seed_lkp)
    if not path:
        raise HTTPException(404, f'No bracket data for {team} ({year})')
    return path


# ── Feature importance endpoint ───────────────────────────────────────────────

@app.get('/api/feature-importance')
def get_feature_importance():
    """Return precomputed feature importance by round."""
    p = _CONFIG_DIR / 'feature_importance.json'
    if not p.exists():
        raise HTTPException(
            404,
            'No precomputed feature importance data. '
            'Run: python scripts/precompute_feature_importance.py'
        )
    return _json.loads(p.read_text())


@app.get('/api/matchup/{year1}/{team1}/{year2}/{team2}')
def matchup(year1: int, team1: str, year2: int, team2: str):
    """Head-to-head win probability for any two team-seasons."""
    t1 = normalize_name(team1)
    t2 = normalize_name(team2)

    # Identical team-seasons are always 50/50 by definition
    if t1 == t2 and year1 == year2:
        def _meta(team, year):
            row = next((m for m in cache.teams_meta if m['year'] == year and
                        normalize_name(m['team']) == team), None)
            return {'seed': row['seed'] if row else None,
                    'conference': row.get('conference') if row else None}
        meta = _meta(t1, year1)
        return {
            'team1': t1, 'year1': year1,
            'team2': t2, 'year2': year2,
            'prob1': 0.5, 'prob2': 0.5,
            'features': [],
            'team1_meta': meta,
            'team2_meta': meta,
        }

    # Raw stats for both teams
    stats1 = cache.get_raw_stats(year1, t1)
    stats2 = cache.get_raw_stats(year2, t2)
    if stats1 is None:
        raise HTTPException(404, f'{team1} ({year1}) not found')
    if stats2 is None:
        raise HTTPException(404, f'{team2} ({year2}) not found')

    LABELS = {
        'AdjEM': 'Efficiency Margin', 'AdjOE': 'Adj Offense', 'AdjDE': 'Adj Defense',
        'AdjTempo': 'Tempo', 'net_score_rate': 'Net Score Rate',
        'efg_pct_off': 'eFG% Off', 'efg_pct_def': 'eFG% Def',
        'to_pct_off': 'TO% Off', 'to_pct_def': 'TO% Def',
        'or_pct_off': 'Off Reb%', 'or_pct_def': 'Def Reb%',
        'ftr_off': 'FT Rate Off', 'ftr_def': 'FT Rate Def',
        'fg3a_rate_off': '3PA Rate Off', 'fg3a_rate_def': '3PA Rate Def',
        'fg3_pct_off': '3P% Off', 'fg2_pct_off': '2P% Off',
        'blk_pct_def': 'Block Rate', 'stl_rate_def': 'Steal Rate',
        'avg_height': 'Avg Height', 'd1_exp': 'D1 Exp',
        'apl_off': 'Ast/TO Off', 'apl_def': 'Ast/TO Def',
        'pd3_off': '3-Pt Share Off', 'pd3_def': '3-Pt Share Def',
        'l10_net_eff': 'L10 Net Eff', 'l10_off_eff': 'L10 Off Eff',
        'l10_def_eff': 'L10 Def Eff', 'l10_win_pct': 'L10 Win%',
        'l10_opp_rank': 'L10 Opp Rank', 'l10_efg': 'L10 eFG%',
        'l10_to_pct': 'L10 TO%',
        'program_tourney_rate_l5': 'Tourney Rate (L5)',
        'program_f4_rate_l10': 'F4 Rate (L10)',
        'two_way_depth': 'Two-Way Depth', 'star_eup': 'Star EUP',
        'depth_eup': 'Depth EUP', 'interior_dom': 'Interior Dom',
        'returning_min_pct': 'Returning Min%',
        'coach_career_tourney_apps': 'Coach Tourney Apps',
        'coach_career_ff':           'Coach Final Fours',
        'conf_tourney_win_pct':      'Conf Tourney Win%',
    }
    CATEGORIES = {
        'Efficiency':    ['AdjEM','AdjOE','AdjDE','AdjTempo','net_score_rate'],
        'Four Factors':  ['efg_pct_off','efg_pct_def','to_pct_off','or_pct_off',
                          'ftr_off','fg3a_rate_def','blk_pct_def','stl_rate_def'],
        'Shooting':      ['fg3_pct_off','fg2_pct_off','fg3a_rate_off','apl_off','apl_def'],
        'Momentum':      ['l10_net_eff','l10_off_eff','l10_def_eff',
                          'l10_win_pct','l10_opp_rank','l10_efg','l10_to_pct'],
        'Roster':        ['avg_height','d1_exp','two_way_depth','star_eup',
                          'depth_eup','interior_dom','returning_min_pct'],
        'Program':       ['program_tourney_rate_l5','program_f4_rate_l10',
                          'coach_career_tourney_apps','coach_career_ff','conf_tourney_win_pct'],
    }
    feat_to_cat = {f: cat for cat, feats in CATEGORIES.items() for f in feats}

    # Build diff row and feature breakdown
    diff_row = {}
    feature_breakdown = []
    for diff_col in DIFF_FEATURES:
        raw = diff_col.replace('_diff', '')
        v1_raw = stats1.get(raw)
        v2_raw = stats2.get(raw)
        v1 = float(v1_raw) if v1_raw is not None and not (isinstance(v1_raw, float) and np.isnan(v1_raw)) else None
        v2 = float(v2_raw) if v2_raw is not None and not (isinstance(v2_raw, float) and np.isnan(v2_raw)) else None

        diff_row[diff_col] = (v1 - v2) if (v1 is not None and v2 is not None) else float('nan')

        if v1 is not None and v2 is not None:
            feature_breakdown.append({
                'key':      diff_col,
                'raw_key':  raw,
                'label':    LABELS.get(raw, raw.replace('_', ' ').title()),
                'category': feat_to_cat.get(raw, 'Other'),
                'v1':       round(v1, 3),
                'v2':       round(v2, 3),
                'diff':     round(v1 - v2, 3),
            })

    # Run model — use exact feature columns it was trained on
    model = _get_model()
    try:
        train_cols = list(model.feature_names_in_)
    except AttributeError:
        train_cols = DIFF_FEATURES
    row_vals = [diff_row.get(c, float('nan')) for c in train_cols]
    X = pd.DataFrame([row_vals], columns=train_cols)
    try:
        # Symmetrize: average forward and reversed prediction to cancel
        # any positional bias in the model (e.g. team1 = higher seed in training)
        prob_fwd = float(model.predict_proba(X)[:, 1][0])
        row_vals_rev = [-diff_row.get(c, float('nan')) for c in train_cols]
        X_rev = pd.DataFrame([row_vals_rev], columns=train_cols)
        prob_rev = float(model.predict_proba(X_rev)[:, 1][0])
        prob1 = (prob_fwd + (1.0 - prob_rev)) / 2.0
    except Exception:
        prob1 = 0.5

    # Team metadata
    def _meta(team, year):
        for m in cache.teams_meta:
            if m['team'] == team and m['year'] == year:
                return m
        return {}

    meta1 = _meta(t1, year1)
    meta2 = _meta(t2, year2)

    # Same-year: did these teams actually meet?
    same_year_result = None
    if year1 == year2:
        bracket_path = get_bracket_path(year1, t1,
            {m['team']: m['seed'] for m in cache.teams_meta if m['year'] == year1 and m['seed']})
        for game in bracket_path:
            opp = game.get('opponent', '')
            if normalize_name(opp) == t2:
                same_year_result = {
                    'played': True,
                    'winner': game.get('result', ''),
                    'round':  game.get('round_name', ''),
                    'score':  game.get('score', ''),
                }
                break

    return {
        'team1': t1, 'year1': year1,
        'team2': t2, 'year2': year2,
        'prob1': round(prob1, 4),
        'prob2': round(1 - prob1, 4),
        'features': feature_breakdown,
        'team1_meta': meta1,
        'team2_meta': meta2,
        'team1_roster': cache.get_player_roster(year1, t1),
        'team2_roster': cache.get_player_roster(year2, t2),
        'same_year_result': same_year_result,
    }


@app.get('/api/simulate/{year}')
def simulate_bracket(year: int, n: int = Query(default=5000, ge=100, le=20000)):
    """Monte Carlo bracket simulation — returns per-team per-round advancement rates."""
    import random as _rnd
    import warnings as _warn
    from src.bracket import load_team_features, _precompute_team_vectors
    from src.kenpom import load_kenpom

    bracket_path = _DATA_DIR / str(year) / 'bracket.csv'
    if not bracket_path.exists():
        raise HTTPException(404, f'No bracket for {year}')

    # Load features + bracket structure
    try:
        team_table = load_team_features(year)
    except Exception as e:
        raise HTTPException(500, f'Failed to load features for {year}: {e}')

    raw = pd.read_csv(bracket_path)
    raw['Team1'] = raw['Team1'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    raw['Team2'] = raw['Team2'].map(lambda x: normalize_name(x) if isinstance(x, str) else x)
    bracket = raw.set_index('MatchID')

    # Build feeder map (WinnerNextMatchID chains)
    feeders: dict[int, list[int]] = {}
    for mid, row in bracket.iterrows():
        nxt = row.get('WinnerNextMatchID')
        if pd.notna(nxt):
            feeders.setdefault(int(nxt), []).append(int(mid))
    for mid in feeders:
        feeders[mid].sort()

    rounds_sorted = sorted(bracket['Round'].unique())

    # Get all R1 teams + their regions
    r1 = bracket[bracket['Round'] == 1]
    all_teams: set[str] = set()
    team_region: dict[str, str] = {}
    for _, row in r1.iterrows():
        for key in ('Team1', 'Team2'):
            t = row[key]
            all_teams.add(t)
            if pd.notna(row.get('Region')):
                team_region[t] = str(row['Region'])

    # Precompute per-team vectors, then full pairwise probability matrix (batched + cached)
    model = _get_model()

    if year in _pmat_cache:
        teams_list, tidx, pmat = _pmat_cache[year]
    else:
        team_vecs = _precompute_team_vectors(team_table, model)
        teams_list = sorted(all_teams)
        tidx = {t: i for i, t in enumerate(teams_list)}
        N = len(teams_list)
        pmat = np.full((N, N), 0.5)

        # Build all upper-triangle pairs in one batch for speed
        pair_rows, pair_i, pair_j = [], [], []
        for i in range(N):
            for j in range(i + 1, N):
                t1, t2 = teams_list[i], teams_list[j]
                if t1 in team_vecs and t2 in team_vecs:
                    pair_rows.append(team_vecs[t1] - team_vecs[t2])
                    pair_i.append(i)
                    pair_j.append(j)

        if pair_rows:
            X_all = np.array(pair_rows)
            with _warn.catch_warnings():
                _warn.simplefilter('ignore')
                probs = model.predict_proba(X_all)[:, 1]
            for k, (i, j) in enumerate(zip(pair_i, pair_j)):
                pmat[i, j] = probs[k]
                pmat[j, i] = 1.0 - probs[k]

        _pmat_cache[year] = (teams_list, tidx, pmat)

    # Pre-parse bracket into ordered game list for fast simulation
    ROUND_KEYS = {1: 'r64', 2: 'r32', 3: 's16', 4: 'e8', 5: 'f4', 6: 'champ'}
    game_order = []  # (match_id, round, slot_type, t1_or_feed1, t2_or_feed2, region)
    det_info = []
    for rnd in rounds_sorted:
        for mid, row in bracket[bracket['Round'] == rnd].iterrows():
            mid = int(mid)
            region = str(row.get('Region', ''))
            if rnd == 1:
                game_order.append((mid, int(rnd), 'fixed', row['Team1'], row['Team2'], region))
            else:
                feeds = feeders.get(mid, [])
                if len(feeds) >= 2:
                    game_order.append((mid, int(rnd), 'feeder', feeds[0], feeds[1], region))

    # Monte Carlo simulations
    adv_counts = {t: {rk: 0 for rk in ROUND_KEYS.values()} for t in teams_list}
    rng = _rnd.Random(42)

    for _ in range(n):
        pred: dict[int, str] = {}
        for mid, rnd, slot, a, b, _ in game_order:
            t1 = a if slot == 'fixed' else pred.get(a, '')
            t2 = b if slot == 'fixed' else pred.get(b, '')
            if not t1 or not t2:
                continue
            i1, i2 = tidx.get(t1), tidx.get(t2)
            p = pmat[i1, i2] if (i1 is not None and i2 is not None) else 0.5
            winner = t1 if rng.random() < p else t2
            pred[mid] = winner
            rk = ROUND_KEYS.get(rnd)
            if rk and winner in adv_counts:
                adv_counts[winner][rk] += 1

    # Deterministic bracket (argmax each game)
    det_pred: dict[int, str] = {}
    det_games = []
    for mid, rnd, slot, a, b, region in game_order:
        t1 = a if slot == 'fixed' else det_pred.get(a, '')
        t2 = b if slot == 'fixed' else det_pred.get(b, '')
        if not t1 or not t2:
            continue
        i1, i2 = tidx.get(t1), tidx.get(t2)
        p = float(pmat[i1, i2]) if (i1 is not None and i2 is not None) else 0.5
        winner = t1 if p >= 0.5 else t2
        det_pred[mid] = winner
        det_games.append({
            'match_id': mid, 'round': rnd,
            'round_name': ROUND_KEYS.get(rnd, f'r{rnd}').upper(),
            'region': region,
            't1': t1, 't2': t2,
            'prob': round(p, 4), 'winner': winner,
        })

    # Build response — seeds from KenPom CSV (teams_meta may not carry seeds for current year)
    year_meta = {m['team']: m for m in cache.teams_meta if m['year'] == year}
    try:
        kp = load_kenpom(year)
        kenpom_seeds = {}
        for _, row in kp.iterrows():
            name = normalize_name(str(row['TeamName'])) if pd.notna(row.get('TeamName')) else None
            seed_val = row.get('seed')
            if name and pd.notna(seed_val):
                try:
                    kenpom_seeds[name] = int(seed_val)
                except (ValueError, TypeError):
                    pass
    except Exception:
        kenpom_seeds = {}

    teams_out = []
    for team in teams_list:
        meta = year_meta.get(team, {})
        seed = meta.get('seed') or kenpom_seeds.get(team)
        adv = {rk: round(adv_counts[team][rk] / n, 4) for rk in ROUND_KEYS.values()}
        teams_out.append({
            'team': team,
            'seed': seed,
            'region': meta.get('region') or team_region.get(team, ''),
            'adv': adv,
        })

    teams_out.sort(key=lambda x: (-x['adv']['champ'], x['seed'] or 99))

    return {
        'year': year,
        'n_sims': n,
        'teams': teams_out,
        'deterministic': det_games,
    }


@app.get('/api/analytics')
def get_analytics():
    """Return precomputed analytics data (calibration, yearly accuracy, era comparison, etc.)."""
    p = _CONFIG_DIR / 'analytics.json'
    if not p.exists():
        raise HTTPException(
            404,
            'No precomputed analytics data. '
            'Run: python scripts/precompute_analytics.py'
        )
    return Response(content=p.read_text(), media_type='application/json')


# ── Live scorecard endpoint ────────────────────────────────────────────────────

@app.get('/api/scorecard/{year}')
def scorecard(year: int):
    """Model predictions vs actual results for a tournament year."""
    loo_path     = _DATA_DIR / str(year) / 'bracket_loo.json'
    bracket_path = _DATA_DIR / str(year) / 'bracket.csv'

    if not loo_path.exists():
        raise HTTPException(404, f'No LOO predictions for {year}. Run: python scripts/precompute_brackets.py --year {year}')
    if not bracket_path.exists():
        raise HTTPException(404, f'No bracket data for {year}')

    predictions = {g['match_id']: g for g in _json.loads(loo_path.read_text())['games']}

    bracket = pd.read_csv(bracket_path)

    ROUND_NAMES = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}

    games_out = []
    for _, row in bracket.iterrows():
        mid  = int(row['MatchID'])
        pred = predictions.get(mid, {})
        rnd  = int(row['Round'])

        raw_t1 = str(row['Team1']) if pd.notna(row.get('Team1')) else ''
        raw_t2 = str(row['Team2']) if pd.notna(row.get('Team2')) else ''
        t1 = normalize_name(raw_t1) if raw_t1 else pred.get('team1', '')
        t2 = normalize_name(raw_t2) if raw_t2 else pred.get('team2', '')

        raw_winner = row.get('Winner', '')
        actual_winner = normalize_name(str(raw_winner)) if pd.notna(raw_winner) and str(raw_winner).strip() else None

        prob     = pred.get('prob')          # prob that team1 wins
        model_w  = pred.get('winner')

        completed = bool(actual_winner)
        correct   = (model_w == actual_winner) if (completed and model_w) else None

        if actual_winner and prob is not None:
            aw_prob = prob if actual_winner == t1 else round(1.0 - prob, 4)
        else:
            aw_prob = None

        s1 = int(row['Score1']) if pd.notna(row.get('Score1')) and str(row.get('Score1', '')).strip() else None
        s2 = int(row['Score2']) if pd.notna(row.get('Score2')) and str(row.get('Score2', '')).strip() else None

        games_out.append({
            'match_id':          mid,
            'round':             rnd,
            'round_name':        ROUND_NAMES.get(rnd, f'R{rnd}'),
            'region':            str(row.get('Region', '')),
            'team1':             t1,
            'team2':             t2,
            'score1':            s1,
            'score2':            s2,
            'model_winner':      model_w,
            'model_prob_t1':     round(prob, 4) if prob is not None else None,
            'actual_winner':     actual_winner,
            'actual_winner_prob': aw_prob,
            'completed':         completed,
            'correct':           correct,
        })

    # Accuracy stats
    done  = [g for g in games_out if g['completed'] and g['correct'] is not None]
    total_correct   = sum(1 for g in done if g['correct'])
    total_completed = len(done)

    by_round: dict = {}
    for g in done:
        rk = str(g['round'])
        if rk not in by_round:
            by_round[rk] = {'correct': 0, 'total': 0, 'round_name': g['round_name']}
        by_round[rk]['total'] += 1
        if g['correct']:
            by_round[rk]['correct'] += 1
    for rk, r in by_round.items():
        r['accuracy'] = round(r['correct'] / r['total'], 4) if r['total'] else None

    return {
        'year':     year,
        'games':    games_out,
        'accuracy': {
            'overall':  round(total_correct / total_completed, 4) if total_completed else None,
            'correct':  total_correct,
            'total':    total_completed,
            'by_round': by_round,
        },
    }


# ── Upset finder endpoint ──────────────────────────────────────────────────────

@app.get('/api/upsets')
def get_upsets():
    """All upset-eligible games (all years) + historical seed advancement baselines.

    Uses the actual trained model on real bracket teams for model_upset_prob.
    LOO simulation probabilities are only used as a fallback because in rounds 2+
    the LOO carries forward predicted (not actual) winners, so the teams and
    probabilities may not correspond to the real matchup.
    """
    from src.kenpom import load_kenpom

    HIST_YEARS   = [y for y in range(2002, 2026) if y != 2020]
    ALL_YEARS    = HIST_YEARS + [2026]
    ROUND_NAMES  = {1:'R64', 2:'R32', 3:'S16', 4:'E8', 5:'F4', 6:'NCG'}
    ADV_KEY      = {1:'r32', 2:'s16', 3:'e8', 4:'f4', 5:'ncg', 6:'champ'}

    seed_tally = {s: {k: 0 for k in ('r32','s16','e8','f4','ncg','champ','total')}
                  for s in range(1, 17)}

    # ── Phase 1: collect all upset-eligible matchups ──────────────────────────
    raw_matchups: list[dict] = []

    for year in ALL_YEARS:
        loo_path     = _DATA_DIR / str(year) / 'bracket_loo.json'
        bracket_path = _DATA_DIR / str(year) / 'bracket.csv'
        if not loo_path.exists() or not bracket_path.exists():
            continue

        try:
            kp = load_kenpom(year)
            yr_seeds: dict = {}
            for _, row in kp.iterrows():
                nm = normalize_name(str(row['TeamName'])) if pd.notna(row.get('TeamName')) else None
                sv = row.get('seed')
                if nm and pd.notna(sv):
                    try: yr_seeds[nm] = int(sv)
                    except: pass
        except Exception:
            yr_seeds = {}

        loo_data    = _json.loads(loo_path.read_text())
        pred_by_id  = {g['match_id']: g for g in loo_data['games']}

        bdf = pd.read_csv(bracket_path)
        act_by_id: dict = {}
        for _, row in bdf.iterrows():
            mid = int(row['MatchID'])
            raw_w = row.get('Winner', '')
            aw  = normalize_name(str(raw_w)) if pd.notna(raw_w) and str(raw_w).strip() else None
            t1r = str(row.get('Team1','')) if pd.notna(row.get('Team1')) else ''
            t2r = str(row.get('Team2','')) if pd.notna(row.get('Team2')) else ''
            act_by_id[mid] = {
                'actual_winner': aw,
                'score1':  int(row['Score1']) if pd.notna(row.get('Score1')) and str(row.get('Score1','')).strip() else None,
                'score2':  int(row['Score2']) if pd.notna(row.get('Score2')) and str(row.get('Score2','')).strip() else None,
                'round':   int(row['Round']),
                'region':  str(row.get('Region','')),
                'team1':   normalize_name(t1r) if t1r else '',
                'team2':   normalize_name(t2r) if t2r else '',
            }

        # Seed baselines (historical only)
        if year != 2026:
            for mid, act in act_by_id.items():
                aw = act['actual_winner']
                if not aw: continue
                rnd   = act['round']
                t1, t2 = act['team1'], act['team2']
                loser = t2 if aw == t1 else t1
                sw, sl = yr_seeds.get(aw), yr_seeds.get(loser)
                if rnd == 1:
                    if sw and 1 <= sw <= 16: seed_tally[sw]['total'] += 1
                    if sl and 1 <= sl <= 16: seed_tally[sl]['total'] += 1
                adv_k = ADV_KEY.get(rnd)
                if adv_k and sw and 1 <= sw <= 16:
                    seed_tally[sw][adv_k] += 1

        # Collect upset-eligible games
        for mid, pred in pred_by_id.items():
            act = act_by_id.get(mid, {})
            rnd = int(pred.get('round', act.get('round', 1)))

            t1 = act.get('team1') or pred.get('team1', '')
            t2 = act.get('team2') or pred.get('team2', '')
            if not t1 or not t2: continue

            s1, s2 = yr_seeds.get(t1), yr_seeds.get(t2)
            if not s1 or not s2: continue

            seed_diff = abs(s1 - s2)
            if seed_diff < 2: continue

            if s1 > s2:   # t1 is underdog
                fav, und, fs, us = t2, t1, s2, s1
                p_und_loo = pred.get('prob', 0.5)
            else:
                fav, und, fs, us = t1, t2, s1, s2
                p_und_loo = 1.0 - pred.get('prob', 0.5)

            aw        = act.get('actual_winner')
            completed = bool(aw)
            sf = act.get('score1') if act.get('team1') == fav else act.get('score2')
            su = act.get('score1') if act.get('team1') == und else act.get('score2')

            raw_matchups.append({
                'year': year, 'match_id': mid, 'rnd': rnd,
                'region': pred.get('region', act.get('region', '')),
                'fav': fav, 'und': und, 'fs': fs, 'us': us, 'seed_diff': seed_diff,
                'p_und_loo': p_und_loo,
                'aw': aw, 'completed': completed,
                'upset_happened': (aw == und) if completed else None,
                'sf': sf, 'su': su,
            })

    # ── Phase 2: batch compute model probabilities for actual matchups ────────
    # The LOO bracket carries forward predicted winners in rounds 2+, so its
    # probabilities often reflect a different matchup than what actually played.
    # Running the model on the real teams gives the correct upset probability.
    model_probs: dict[tuple, float] = {}
    try:
        model_obj = _get_model()
        feat_cols = list(model_obj.feature_names_in_)

        batch_rows:  list[dict]  = []
        batch_keys:  list[tuple] = []
        seen_keys:   set         = set()

        for m in raw_matchups:
            key = (m['year'], m['fav'], m['und'])
            if key in seen_keys:
                continue
            seen_keys.add(key)

            sf = cache.get_raw_stats(m['year'], m['fav']) if cache else None
            su = cache.get_raw_stats(m['year'], m['und']) if cache else None
            if not sf or not su:
                continue

            row: dict = {}
            for dc in feat_cols:
                base = dc[:-5] if dc.endswith('_diff') else dc
                vf, vu = sf.get(base), su.get(base)
                if vf is not None and vu is not None:
                    try:
                        vff, vuu = float(vf), float(vu)
                        row[dc] = float('nan') if (np.isnan(vff) or np.isnan(vuu)) else vff - vuu
                    except (TypeError, ValueError):
                        row[dc] = float('nan')
                else:
                    row[dc] = float('nan')
            batch_rows.append(row)
            batch_keys.append(key)

        if batch_rows:
            X = pd.DataFrame(batch_rows, columns=feat_cols)
            probs_fav = model_obj.predict_proba(X)[:, 1]  # prob fav wins
            for key, p_fav in zip(batch_keys, probs_fav):
                model_probs[key] = 1.0 - float(p_fav)    # prob und wins

    except Exception as e:
        print(f'[upsets] Batch prediction error: {e}')

    # ── Phase 3: assemble final game list ─────────────────────────────────────
    upset_games: list = []
    for m in raw_matchups:
        key   = (m['year'], m['fav'], m['und'])
        p_und = model_probs.get(key, m['p_und_loo'])   # actual model; LOO fallback
        upset_games.append({
            'year':               m['year'],
            'match_id':           m['match_id'],
            'round':              m['rnd'],
            'round_name':         ROUND_NAMES.get(m['rnd'], f'R{m["rnd"]}'),
            'region':             m['region'],
            'favorite':           m['fav'],
            'favorite_seed':      m['fs'],
            'underdog':           m['und'],
            'underdog_seed':      m['us'],
            'seed_diff':          m['seed_diff'],
            'model_upset_prob':   round(p_und, 4),
            'actual_winner':      m['aw'],
            'upset_happened':     m['upset_happened'],
            'model_called_upset': p_und > 0.5,
            'completed':          m['completed'],
            'score_fav':          m['sf'],
            'score_und':          m['su'],
        })

    # ── Seed baselines ────────────────────────────────────────────────────────
    baselines: dict = {}
    for seed in range(1, 17):
        t     = seed_tally[seed]
        total = t['total'] or 1
        baselines[str(seed)] = {
            'r32':   round(t['r32']   / total, 3),
            's16':   round(t['s16']   / total, 3),
            'e8':    round(t['e8']    / total, 3),
            'f4':    round(t['f4']    / total, 3),
            'ncg':   round(t['ncg']   / total, 3),
            'champ': round(t['champ'] / total, 3),
            'total': t['total'],
        }

    return {'upset_games': upset_games, 'seed_baselines': baselines}


# ── Model Report endpoint ─────────────────────────────────────────────────────

@app.get('/api/model-report')
def model_report():
    """Aggregate LYO accuracy stats across all historical years for the flagship report page."""
    HIST_YEARS  = [y for y in range(2002, 2026) if y != 2020]
    ROUND_NAMES = {1:'R64', 2:'R32', 3:'S16', 4:'E8', 5:'F4', 6:'NCG'}
    ROUND_ORDER = ['R64','R32','S16','E8','F4','NCG']

    # Load analytics.json for calibration + per-year seed baseline
    analytics_path = _CONFIG_DIR / 'analytics.json'
    analytics = _json.loads(analytics_path.read_text()) if analytics_path.exists() else {}

    round_agg: dict = {}   # round_name → {correct, total}
    all_games: list = []   # flat list for best/worst calls

    for year in HIST_YEARS:
        loo_path = _DATA_DIR / str(year) / 'bracket_loo.json'
        if not loo_path.exists():
            continue
        data = _json.loads(loo_path.read_text())
        for g in data['games']:
            if g.get('correct') is None:
                continue
            rn = ROUND_NAMES.get(int(g['round']), f"R{g['round']}")
            if rn not in round_agg:
                round_agg[rn] = {'correct': 0, 'total': 0}
            round_agg[rn]['total'] += 1
            if g['correct']:
                round_agg[rn]['correct'] += 1
            prob = g.get('prob', 0.5)
            confidence = round(max(prob, 1.0 - prob), 4)
            all_games.append({
                'year':          year,
                'round_name':    rn,
                'team1':         g.get('team1', ''),
                'team2':         g.get('team2', ''),
                'model_winner':  g.get('winner', ''),
                'actual_winner': g.get('actual_winner', ''),
                'correct':       g['correct'],
                'confidence':    confidence,
                'region':        g.get('region', ''),
                'score1':        g.get('score1'),
                'score2':        g.get('score2'),
            })

    round_accuracy = []
    for rn in ROUND_ORDER:
        if rn in round_agg:
            agg = round_agg[rn]
            acc = round(agg['correct'] / agg['total'], 4) if agg['total'] else None
            round_accuracy.append({'round_name': rn, 'correct': agg['correct'],
                                   'total': agg['total'], 'accuracy': acc})

    total_correct = sum(r['correct'] for r in round_accuracy)
    total_games   = sum(r['total']   for r in round_accuracy)

    # Best/worst calls
    best_calls  = sorted([g for g in all_games if g['correct']],      key=lambda g: -g['confidence'])[:15]
    worst_calls = sorted([g for g in all_games if not g['correct']],   key=lambda g: -g['confidence'])[:15]

    # Per-year chaos annotation: flag if accuracy < mean - 0.05 or upset_rate > mean + 0.05
    ya = analytics.get('yearly_accuracy', [])
    if ya:
        mean_acc   = sum(d['accuracy']   for d in ya) / len(ya)
        mean_upset = sum(d['upset_rate'] for d in ya) / len(ya)
        for d in ya:
            d['chaos'] = (d['accuracy'] < mean_acc - 0.05) or (d['upset_rate'] > mean_upset + 0.05)
            d['strong'] = d['accuracy'] > mean_acc + 0.05

    return {
        'overall_accuracy':  round(total_correct / total_games, 4) if total_games else None,
        'total_games':       total_games,
        'n_seasons':         len([y for y in HIST_YEARS if (_DATA_DIR / str(y) / 'bracket_loo.json').exists()]),
        'baseline_seed':     0.580,
        'baseline_adjEM':    0.650,
        'round_accuracy':    round_accuracy,
        'yearly_accuracy':   ya,
        'calibration':       analytics.get('calibration', []),
        'best_calls':        best_calls,
        'worst_calls':       worst_calls,
        'upset_by_seed':     (analytics.get('upset_analysis') or {}).get('by_seed_matchup', []),
    }


# ── LOO bracket predictor endpoints ───────────────────────────────────────────

@app.get('/api/bracket/years')
def bracket_years():
    """List years with precomputed LOO bracket data."""
    years = [
        y for y in range(2002, 2027)
        if y != 2020 and (_DATA_DIR / str(y) / 'bracket_loo.json').exists()
    ]
    return sorted(years)


@app.get('/api/bracket/{year}')
def bracket_loo(year: int):
    """Return LOO bracket prediction enriched with actual results and seeds."""
    from src.kenpom import load_kenpom

    p = _DATA_DIR / str(year) / 'bracket_loo.json'
    if not p.exists():
        raise HTTPException(
            404,
            f'No precomputed bracket for {year}. '
            f'Run: python scripts/precompute_brackets.py --year {year}'
        )

    data = _json.loads(p.read_text())

    # ── Enrich games with actual results from bracket.csv ─────────────────────
    bracket_path = _DATA_DIR / str(year) / 'bracket.csv'
    if bracket_path.exists():
        actual = pd.read_csv(bracket_path)
        actual_by_id = {int(r['MatchID']): r for _, r in actual.iterrows()}
        games_by_id  = {g['match_id']: g for g in data['games']}

        for mid, row in actual_by_id.items():
            if mid not in games_by_id:
                continue
            g = games_by_id[mid]
            raw_w = row.get('Winner', '')
            aw = normalize_name(str(raw_w)) if pd.notna(raw_w) and str(raw_w).strip() else None
            s1 = int(row['Score1']) if pd.notna(row.get('Score1')) and str(row.get('Score1','')).strip() else None
            s2 = int(row['Score2']) if pd.notna(row.get('Score2')) and str(row.get('Score2','')).strip() else None
            g['actual_winner'] = aw
            g['score1']  = s1
            g['score2']  = s2
            g['correct'] = (g.get('winner') == aw) if aw and g.get('winner') else None

        # Recompute accuracy from enriched games
        done = [g for g in data['games'] if g.get('correct') is not None]
        total_correct   = sum(1 for g in done if g['correct'])
        total_completed = len(done)
        by_round: dict = {}
        for g in done:
            rk = str(g['round'])
            if rk not in by_round:
                by_round[rk] = {'correct': 0, 'total': 0}
            by_round[rk]['total'] += 1
            if g['correct']:
                by_round[rk]['correct'] += 1
        for rk, r in by_round.items():
            r['accuracy'] = round(r['correct'] / r['total'], 4) if r['total'] else None

        data['accuracy']          = round(total_correct / total_completed, 4) if total_completed else None
        data['accuracy_by_round'] = {rk: r['accuracy'] for rk, r in by_round.items()}

    # ── Add seed lookup from KenPom CSV ────────────────────────────────────────
    try:
        kp = load_kenpom(year)
        seeds: dict = {}
        for _, row in kp.iterrows():
            name = normalize_name(str(row['TeamName'])) if pd.notna(row.get('TeamName')) else None
            sv   = row.get('seed')
            if name and pd.notna(sv):
                try:
                    seeds[name] = int(sv)
                except (ValueError, TypeError):
                    pass
        data['seeds'] = seeds
    except Exception:
        data['seeds'] = {}

    return data



# ── Serve React build (must be last — catch-all would intercept API routes) ───

_DIST = _ROOT / 'app' / 'frontend' / 'dist'
if _DIST.exists():
    app.mount('/assets', StaticFiles(directory=str(_DIST / 'assets')), name='assets')

    @app.get('/', include_in_schema=False)
    def serve_root():
        return FileResponse(str(_DIST / 'index.html'))

    @app.get('/{full_path:path}', include_in_schema=False)
    def serve_spa(full_path: str):
        p = _DIST / full_path
        if p.exists() and p.is_file():
            return FileResponse(str(p))
        return FileResponse(str(_DIST / 'index.html'))
