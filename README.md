# NCAA Bracket Model

A machine learning model for predicting NCAA tournament outcomes, trained on 23 seasons of data (2002–2025, excluding 2020). Achieves **71.4% accuracy** on leave-year-out cross-validation across 1,444 historical games — compared to a seed-alone baseline of ~58% and AdjEM-alone of ~65%.

---

## How It Works

The model is a `HistGradientBoostingClassifier` trained on per-matchup feature differentials. For each game, both teams' pre-tournament stats are differenced (Team A minus Team B), producing a single feature vector that the model uses to predict the win probability.

**Training strategy:** Leave-Year-Out cross-validation — for each held-out year, the model trains on all other years. This mirrors real prediction conditions where you never have data from the year you're predicting.

**Data augmentation:** Every game is duplicated with team positions swapped and all differential features negated. This removes positional bias and balances classes to exactly 50/50.

### Validated Performance

| Metric | Value |
|--------|-------|
| Accuracy | 71.4% |
| Brier Score | 0.193 |
| Log Loss | 0.581 |
| Games evaluated | 1,444 (23 seasons) |
| Seed-alone baseline | ~58% |
| AdjEM-alone baseline | ~65% |

### Top Predictive Features

| Rank | Feature | Correlation | Description |
|------|---------|-------------|-------------|
| 1 | AdjEM | +0.392 | KenPom efficiency margin |
| 2 | AdjOE | +0.325 | Adjusted offensive efficiency |
| 3 | two_way_depth | +0.301 | Roster two-way player depth |
| 4 | AdjDE | -0.288 | Adjusted defensive efficiency |
| 5 | program_tourney_rate_l5 | +0.256 | 5-year tournament appearance rate |

---

## Pipeline

```
Raw data (data/{year}/)
    ↓
Feature Engineering
  src/kenpom.py            KenPom pre-tournament ratings
  src/scouting.py          Four Factors + advanced team stats
  src/player_features.py   Roster composition features
  src/gameplan_features.py Last-10-game rolling momentum
  src/program_features.py  Program pedigree (tourney/F4 rates)
  src/features.py          Assembles matchup differential matrix
    ↓
Training  (src/model.py)
  HistGradientBoostingClassifier, Leave-Year-Out CV
    ↓
Evaluation  (scripts/)
  precompute_brackets.py   Simulated bracket per year
  precompute_feature_importance.py  Permutation importance
  profile_outcomes.py      Round-by-round accuracy
    ↓
2026 Inference  (scripts/predict_2026.py)
  Win probabilities for all possible 2026 matchups
```

---

## Project Structure

```
src/                    Core feature engineering + model
scripts/                Pipeline scripts (scraping, training, evaluation, prediction)
app/
  backend/              FastAPI server
  frontend/             Vite + vanilla JS similarity UI
config/                 Reference JSON files (name map, coaches, tournament dates)
analysis/               Feature importance findings, outcome profiles
data/                   Raw data — NOT included, see data/README.md
```

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- KenPom subscription (required for scraping — data not included)

### Install

```bash
# Python dependencies
pip install -r app/requirements.txt

# Frontend dependencies
cd app/frontend && npm install
```

### Data

Raw data (KenPom CSVs, scouting parquets, player parquets) is not included in this repository due to licensing. See [`data/README.md`](data/README.md) for the full directory structure and scraping instructions.

---

## Running

### Backend API

```bash
# From project root
uvicorn app.backend.main:app --reload --app-dir .
# → http://localhost:8000
```

### Frontend

```bash
cd app/frontend
npm run dev
# → http://localhost:5173
```

### Pipeline Scripts

```bash
# Rebuild feature importance JSON (~5-10 min)
python scripts/precompute_feature_importance.py

# Precompute leave-year-out bracket predictions
python scripts/precompute_brackets.py

# Generate 2026 predictions
python scripts/predict_2026.py

# Audit team name normalization across years
python scripts/audit_names.py
```

To force a full data cache rebuild, delete `data/datacache.pkl` and restart the backend.

---

## Team Similarity UI

The app includes a team similarity explorer — a dual-space Euclidean search across team stat vectors and player roster vectors. Given any historical tournament team, it finds the most similar teams across all other years. This is a scouting tool separate from the bracket predictor; similarity scores are for exploration, not win probabilities.

---

## Key Design Decisions

- **No data leakage:** All features use only information available before Selection Sunday. KenPom ratings are pre-tournament snapshots; rolling stats use only regular season and conference tournament games.
- **Within-year normalization:** Z-scores are computed per year using only that year's tournament teams. 2026 inference normalizes using only 2026 teams.
- **2020 excluded everywhere:** No tournament was held; excluded from all year ranges, loops, and aggregations.
- **Name normalization is critical:** Every team name passes through `config/name_map.json` before any join. Silent mismatches drop teams.
