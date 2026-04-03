"""Generate a Sweet 16+ HTML bracket from sweet16_prediction.json.

Renders only Sweet 16, Elite 8, Final Four, and Championship.
Rounds 1 and 2 are omitted.

Run from project root:
    python scripts/generate_sweet16_html.py
    python scripts/generate_sweet16_html.py --out outputs/my_sweet16.html
"""

import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.kenpom import load_kenpom
from src.names import normalize_name

DATA_DIR   = Path(__file__).resolve().parent.parent / 'data'
LOGOS_DIR  = DATA_DIR / 'logos'
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs'

# ── Helpers ───────────────────────────────────────────────────────────────────

def team_slug(name: str) -> str:
    return (name.replace(' ', '_').replace('.', '').replace("'", '')
                .replace('&', 'and').replace('(', '').replace(')', ''))

def load_logo_b64(name: str) -> str | None:
    p = LOGOS_DIR / f'{team_slug(name)}.png'
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return None

def load_seeds() -> dict:
    kp = load_kenpom(2026)
    out = {}
    for _, row in kp.iterrows():
        s = row.get('seed')
        if pd.notna(s) and str(s).strip() not in ('', 'nan'):
            out[normalize_name(str(row['TeamName']).strip())] = int(float(s))
    return out

def load_games() -> dict:
    """Load sweet16_prediction.json and normalize to the same shape as bracket_loo.json."""
    data = json.loads((DATA_DIR / '2026' / 'sweet16_prediction.json').read_text())
    games = {}
    for g in data['games']:
        games[int(g['match_id'])] = {
            'match_id': g['match_id'],
            'round':    g['round'],
            'team1':    g['team1'],
            'team2':    g['team2'],
            'prob':     g['team1_win_pct'],   # P(team1 wins)
            'winner':   g['winner'],
        }
    return games

# ── Game card HTML ─────────────────────────────────────────────────────────────

def game_card(mid: int, games: dict, seeds: dict, logo_cache: dict, mirror: bool = False) -> str:
    if mid not in games:
        return '<div class="game-card empty"></div>'
    g      = games[mid]
    t1, t2 = g['team1'], g['team2']
    winner = g['winner']
    prob   = g['prob']  # P(t1 wins)

    t1_pct = prob
    t2_pct = 1 - prob

    def row(name, pct, is_winner):
        b64  = logo_cache.get(name) or load_logo_b64(name)
        logo_cache[name] = b64
        logo = (f'<img class="logo" src="data:image/png;base64,{b64}">'
                if b64 else '<div class="logo"></div>')
        seed  = seeds.get(name, '')
        seed_html = f'<span class="seed">{seed}</span>' if seed != '' else '<span class="seed"></span>'
        short = name if len(name) <= 18 else name[:17] + '…'
        cls   = 'row winner' if is_winner else 'row loser'
        pct_html = f'<span class="pct">{int(round(pct * 100))}%</span>'
        if mirror:
            return f'<div class="{cls}">{pct_html}<span class="tname">{short}</span>{seed_html}{logo}</div>'
        else:
            return f'<div class="{cls}">{logo}{seed_html}<span class="tname">{short}</span>{pct_html}</div>'

    r1 = row(t1, t1_pct, winner == t1)
    r2 = row(t2, t2_pct, winner == t2)
    return f'<div class="game-card">{r1}{r2}</div>'

# ── Round column HTML ──────────────────────────────────────────────────────────

def round_col(match_ids: list, games: dict, seeds: dict, logo_cache: dict,
              mirror: bool = False, connector: str = 'right') -> str:
    slots = []
    for i, mid in enumerate(match_ids):
        pair_pos = 'odd' if i % 2 == 0 else 'even'
        card = game_card(mid, games, seeds, logo_cache, mirror=mirror)
        conn_cls = f'conn-{connector}-{pair_pos}' if connector else ''
        if len(match_ids) == 1:
            conn_cls = ''
        slots.append(f'<div class="slot {conn_cls}">{card}</div>')
    n = len(match_ids)
    return f'<div class="round n{n}">{"".join(slots)}</div>'

# ── Region HTML ────────────────────────────────────────────────────────────────

def region_block(label: str, rounds: list, games: dict, seeds: dict,
                 logo_cache: dict, mirror: bool = False) -> str:
    cols = []
    for i, match_ids in enumerate(rounds):
        is_last = (i == len(rounds) - 1)
        connector = None if is_last else ('left' if mirror else 'right')
        cols.append(round_col(match_ids, games, seeds, logo_cache,
                               mirror=mirror, connector=connector))
    direction = 'row-reverse' if mirror else 'row'
    return f'''
    <div class="region">
      <div class="region-label">{label}</div>
      <div class="rounds" style="flex-direction:{direction}">
        {"".join(cols)}
      </div>
    </div>'''

# ── CSS ────────────────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #08080f;
  font-family: 'Segoe UI', system-ui, sans-serif;
  color: #fff;
  padding: 24px;
}

h1 {
  text-align: center;
  font-size: 22px;
  letter-spacing: 3px;
  color: #c8a96e;
  margin-bottom: 6px;
  text-transform: uppercase;
}
.subtitle {
  text-align: center;
  font-size: 11px;
  color: #555;
  letter-spacing: 2px;
  margin-bottom: 24px;
  text-transform: uppercase;
}

/* ── Top-level layout ── */
.bracket {
  display: flex;
  align-items: stretch;
  gap: 0;
  min-width: 1500px;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
}

/* ── Region ── */
.region {
  display: flex;
  flex-direction: column;
}
.region-label {
  font-size: 10px;
  letter-spacing: 3px;
  color: #c8a96e;
  text-align: center;
  padding: 4px 0 6px;
  text-transform: uppercase;
}
.rounds {
  display: flex;
  align-items: stretch;
}

/* ── Round column (Sweet 16 bracket — starts at S16) ── */
.round {
  display: flex;
  flex-direction: column;
  width: 210px;
  flex-shrink: 0;
}
/* n2 = Sweet 16 (2 games per region), n1 = Elite 8 (1 game) */
.round.n2  { --slot-h: 120px; }
.round.n1  { --slot-h: 240px; }

.slot {
  height: var(--slot-h, 120px);
  display: flex;
  align-items: center;
  position: relative;
}

/* ── Round labels ── */
.round-label {
  font-size: 9px;
  letter-spacing: 2px;
  color: #444;
  text-align: center;
  text-transform: uppercase;
  padding-bottom: 4px;
  width: 210px;
}

/* ── Connectors (right side) ── */
.conn-right-odd::after,
.conn-right-even::after {
  content: '';
  position: absolute;
  right: 0;
  width: 12px;
}
.conn-right-odd::after {
  top: 50%;
  height: calc(var(--slot-h, 120px) / 2);
  border-right: 1px solid #3a3a4a;
  border-bottom: 1px solid #3a3a4a;
}
.conn-right-even::after {
  bottom: 50%;
  height: calc(var(--slot-h, 120px) / 2);
  border-right: 1px solid #3a3a4a;
  border-top: 1px solid #3a3a4a;
}

/* ── Connectors (left side, mirrored) ── */
.conn-left-odd::after,
.conn-left-even::after {
  content: '';
  position: absolute;
  left: 0;
  width: 12px;
}
.conn-left-odd::after {
  top: 50%;
  height: calc(var(--slot-h, 120px) / 2);
  border-left: 1px solid #3a3a4a;
  border-bottom: 1px solid #3a3a4a;
}
.conn-left-even::after {
  bottom: 50%;
  height: calc(var(--slot-h, 120px) / 2);
  border-left: 1px solid #3a3a4a;
  border-top: 1px solid #3a3a4a;
}

/* ── Game card ── */
.game-card {
  width: 196px;
  border: 1px solid #222230;
  border-radius: 5px;
  overflow: hidden;
  flex-shrink: 0;
}
.game-card.empty {
  height: 54px;
  background: transparent;
  border-color: transparent;
}

.row {
  display: flex;
  align-items: center;
  padding: 3px 6px;
  height: 27px;
  gap: 4px;
}
.row.winner {
  background: #13132a;
}
.row.loser {
  background: #0c0c18;
  opacity: 0.55;
}
.logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
  border-radius: 50%;
  flex-shrink: 0;
}
.seed {
  font-size: 9px;
  font-weight: 700;
  color: #666;
  width: 14px;
  text-align: center;
  flex-shrink: 0;
}
.tname {
  font-size: 11px;
  font-weight: 700;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #ddd;
}
.row.winner .tname { color: #fff; }
.pct {
  font-size: 11px;
  font-weight: 700;
  color: #c8a96e;
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}
.row.loser .pct { color: #555; }

/* ── Center column (FF left + right of championship) ── */
.center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 660px;
  flex-shrink: 0;
  gap: 10px;
}
.center-label {
  font-size: 9px;
  letter-spacing: 3px;
  color: #c8a96e;
  text-transform: uppercase;
  text-align: center;
  padding: 4px 0;
}
.ff-row {
  display: flex;
  align-items: center;
  gap: 0;
}
.ff-left, .ff-right {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.ff-conn {
  width: 28px;
  height: 1px;
  background: #3a3a4a;
  flex-shrink: 0;
}
.champ-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.champ-game { width: 210px; }
.champ-game .game-card { width: 208px; }
.champ-winner-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 4px;
}
.champ-logo {
  width: 22px;
  height: 22px;
  object-fit: contain;
  border-radius: 50%;
  flex-shrink: 0;
}
.champ-winner-text {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #c8a96e;
  text-transform: uppercase;
}
"""

# ── Full HTML ──────────────────────────────────────────────────────────────────

def build_html(games: dict, seeds: dict) -> str:
    logo_cache: dict = {}

    # Left: East + South (S16 → E8, normal direction)
    east  = region_block('East',  [[13, 14], [15]], games, seeds, logo_cache, mirror=False)
    south = region_block('South', [[43, 44], [45]], games, seeds, logo_cache, mirror=False)

    # Right: Midwest + West (S16 → E8, mirrored so E8 is closest to center)
    midwest = region_block('Midwest', [[58, 59], [60]], games, seeds, logo_cache, mirror=True)
    west    = region_block('West',    [[28, 29], [30]], games, seeds, logo_cache, mirror=True)

    # Final Four + Championship
    ff61 = game_card(61, games, seeds, logo_cache)
    ff62 = game_card(62, games, seeds, logo_cache)
    ff63 = game_card(63, games, seeds, logo_cache)

    # Champion name + logo
    champ_name = ''
    champ_logo_html = ''
    if 63 in games:
        champ_name = games[63]['winner']
        b64 = logo_cache.get(champ_name) or load_logo_b64(champ_name)
        logo_cache[champ_name] = b64
        if b64:
            champ_logo_html = f'<img class="champ-logo" src="data:image/png;base64,{b64}">'

    center = f'''
    <div class="center">
      <div class="ff-row">
        <div class="ff-left">
          <div class="center-label">Final Four</div>
          {ff61}
        </div>
        <div class="ff-conn"></div>
        <div class="champ-col">
          <div class="champ-game">{ff63}</div>
          <div class="champ-winner-badge">{champ_logo_html}<span class="champ-winner-text">Champion: {champ_name}</span></div>
        </div>
        <div class="ff-conn"></div>
        <div class="ff-right">
          <div class="center-label">Final Four</div>
          {ff62}
        </div>
      </div>
    </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>2026 NCAA Tournament — Sweet 16 Simulation</title>
<style>{CSS}</style>
</head>
<body>
<h1>2026 NCAA Tournament — Sweet 16</h1>
<div class="subtitle">Monte Carlo Simulation · 5,000 runs per matchup · Sweet 16 field locked from actual results</div>
<div class="bracket">
  <div class="side left">{east}{south}</div>
  {center}
  <div class="side right">{midwest}{west}</div>
</div>
</body>
</html>'''

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate Sweet 16 bracket HTML')
    parser.add_argument('--out', type=str,
                        default=str(OUTPUT_DIR / 'bracket_sweet16_2026.html'),
                        help='Output file path')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print('Loading data...')
    games = load_games()
    seeds = load_seeds()

    print('Building HTML...')
    html = build_html(games, seeds)

    out = Path(args.out)
    out.write_text(html, encoding='utf-8')
    print(f'Done -> {out}')
    print('Open in a browser and screenshot.')


if __name__ == '__main__':
    main()
