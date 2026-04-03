"""Seed-pick baseline accuracy.

Always picks the lower seed number (more favored team) in every historical
tournament game. For Final Four (round 5) and Championship (round 6) games
where both teams share the same seed, the game is excluded from the count.

Run from project root:
    python scripts/seed_baseline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.kenpom import load_kenpom
from src.names import normalize_name

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
YEARS    = [y for y in range(2002, 2026) if y != 2020]

LATE_ROUNDS = {5, 6}  # Final Four + Championship


def load_seeds(year: int) -> dict:
    kp = load_kenpom(year)
    out = {}
    for _, row in kp.iterrows():
        s = row.get('seed', '')
        if pd.notna(s) and str(s).strip() not in ('', 'nan'):
            out[normalize_name(str(row['TeamName']).strip())] = int(float(s))
    return out


def main():
    total   = 0
    correct = 0
    skipped = 0

    by_round: dict[int, dict] = {}

    for year in YEARS:
        bracket_path = DATA_DIR / str(year) / 'bracket.csv'
        if not bracket_path.exists():
            print(f'  [SKIP] {year} — bracket.csv not found')
            continue

        seeds = load_seeds(year)
        df    = pd.read_csv(bracket_path)

        for _, row in df.iterrows():
            t1     = normalize_name(str(row['Team1']).strip()) if isinstance(row['Team1'], str) else None
            t2     = normalize_name(str(row['Team2']).strip()) if isinstance(row['Team2'], str) else None
            winner = normalize_name(str(row['Winner']).strip()) if isinstance(row['Winner'], str) else None
            rnd    = int(row['Round'])

            if not t1 or not t2 or not winner:
                continue

            s1 = seeds.get(t1)
            s2 = seeds.get(t2)

            # Skip if either seed is missing
            if s1 is None or s2 is None:
                skipped += 1
                continue

            # Skip same-seed matchups in late rounds (F4 / NCG)
            if s1 == s2 and rnd in LATE_ROUNDS:
                skipped += 1
                continue

            # Pick lower seed number (more favored); coin-flip to t1 on tie
            pick = t1 if s1 <= s2 else t2

            hit = int(pick == winner)
            total   += 1
            correct += hit

            r = by_round.setdefault(rnd, {'correct': 0, 'total': 0})
            r['correct'] += hit
            r['total']   += 1

    print(f'Seed-pick baseline  ({len(YEARS)} seasons, 2002-2025 excl. 2020)')
    print('=' * 55)
    print(f'  Overall : {correct}/{total}  ({correct/total*100:.1f}%)')
    print()

    round_names = {1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG'}
    print(f'  {"Round":<6}  {"Correct":>7}  {"Total":>5}  {"Acc":>6}')
    print('  ' + '-' * 30)
    for rnd in sorted(by_round):
        r   = by_round[rnd]
        acc = r['correct'] / r['total'] * 100
        print(f'  {round_names.get(rnd, str(rnd)):<6}  {r["correct"]:>7}  {r["total"]:>5}  {acc:>5.1f}%')

    if skipped:
        print(f'\n  Skipped (same seed in F4/NCG or missing seed): {skipped}')


if __name__ == '__main__':
    main()
