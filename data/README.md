# data/

This directory holds all raw and intermediate data for the bracket model. It is **not tracked by git** — you must populate it yourself using the scraping scripts in `scripts/`. Note that a Kenpom Premium subscription is required to attain this data, which can be found on kenpom.com

---

## Data Sources

| Source | What it provides | Auth |
|--------|-----------------|------|
| [KenPom](https://kenpom.com) (premium subscription) | Pre-tournament efficiency ratings (`summary{YY}_pt.csv`), scouting reports (Four Factors + advanced stats), player roster stats, game-by-game logs | Cookie export from Chrome — see Quick Start |
| [Sports Reference CBB](https://www.sports-reference.com/cbb/) | Conference standings | None |
| NCAA (manual) | `bracket.csv` tournament results — used as labels only, never as features | None |

Reproducibility requires a KenPom premium account. The Sports Reference and bracket data are freely available.

---

## Directory Structure

```
data/
  {year}/                        # One directory per season (2001–2026, no 2020)
    summary{YY}_pt.csv           # KenPom pre-tournament ratings (FEATURES)
    bracket.csv                  # NCAA tournament results (LABELS ONLY — never use as features)
    bracket_loo.json             # Leave-year-out model predictions for this year (generated)
    scouting/                    # Per-team Four Factors + advanced stats (parquet)
      {slug}_scouting.parquet
      average_scouting.parquet   # D-I averages for the year
    players/                     # Per-team roster stats (parquet)
      {slug}_players.parquet
    gameplan/                    # Per-team game-by-game logs (parquet)
      {slug}_gameplan.parquet
  conferences.parquet            # Team → conference mapping, all years
  analytics.json                 # Precomputed calibration + accuracy metrics (generated)
```

Reference files (tracked in `config/`, not here):
- `config/name_map.json` — canonical team name lookup
- `config/team_coaches.json` — team → coach by year
- `config/sr_school_map.json` — Sports Reference school ID → normalized name
- `config/tournament_dates.json` — NCAA tournament start date per year
- `config/feature_importance.json` — precomputed permutation importance (generated)

---

## How to Populate

Run these scripts from the project root in order. Each requires a valid KenPom session cookie (`cookies.json`) except `scrape_conferences.py` which uses Sports Reference.

```bash
# 1. Game-by-game logs (used for rolling momentum features)
python scripts/scrape_all_years.py          # 2001–2026

# 2. Scouting reports + Four Factors (KenPom)
python scripts/scrape_scouting.py           # 2001–2026

# 3. Player roster stats (KenPom)
python scripts/scrape_players_all_years.py  # 2002–2026

# 4. Conference standings (Sports Reference)
python scripts/scrape_conferences.py        # 2002–2026

# 5. Rebuild coach map (reads coaches_raw/, writes config/team_coaches.json)
python scripts/build_coach_map.py
```

After scraping, rebuild the feature cache:
```bash
# Delete stale cache so it rebuilds on next backend start
rm data/datacache.pkl

# Recompute feature importance (optional, ~5-10 min)
python scripts/precompute_feature_importance.py

# Precompute leave-year-out bracket predictions
python scripts/precompute_brackets.py
```

---

## Key Rules

- **2020 is always excluded.** No tournament was held. All year loops skip it.
- **`bracket.csv` is labels only.** Never join bracket results back into feature rows for the same year.
- **KenPom CSVs (`summary{YY}_pt.csv`) must be pre-tournament snapshots.** Post-tournament updates are not valid features.
- **Z-score normalization is within-year.** Never normalize across years or mix 2026 teams with historical data.
- **Team names must be normalized** through `config/name_map.json` before any join. Silent mismatches drop teams without errors.
