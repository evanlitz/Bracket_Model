# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role of Claude in This Project

Claude is the **architect and reasoning layer** for this project. Codex handles implementation; Obsidian holds documentation and notes. Claude's job is to:
- Understand the full pipeline before proposing changes
- Identify leakage, alignment gaps, and design tradeoffs
- Write precise, unambiguous specs that Codex can implement without guesswork
- Catch problems before they become bugs in production predictions

**Do not write code speculatively.** Explain the approach and tradeoffs first, confirm with the user, then spec it out for Codex.

---

## Project Mission

Train on rich historical NCAA tournament data (2002–2025, no 2020) and apply the resulting model to predict the **2026 bracket**. The ultimate output is a ranked set of matchup win probabilities for every possible 2026 game, grounded in features that are provably available before Selection Sunday.

---

## Self-Check: Ask Before Every Change

Before proposing or speccing any change, answer these questions explicitly:

1. **Leakage:** Does this feature or data join use any information that would not exist at 2026 prediction time (e.g., in-tournament game results, post-Selection Sunday stats)?
2. **Alignment:** Is this feature computable for 2026 teams in exactly the same way as for 2002–2025 teams? Are column names, units, and data sources consistent?
3. **Pipeline stage:** Which stage does this change belong to — raw data, feature engineering, model training, evaluation, or inference? Am I keeping those stages cleanly separated?
4. **Reproducibility:** Can this be re-run from scratch by a script with no manual steps? If not, what is blocking that?
5. **Scope:** Is this the minimum change needed, or am I adding complexity that isn't required yet?

---

## Commands

### Backend
```bash
# Install Python dependencies
cd app && pip install -r requirements.txt

# Run backend server (from project root)
uvicorn app.backend.main:app --reload --app-dir .
# → http://localhost:8000
```

### Frontend
```bash
cd app/frontend
npm install
npm run dev      # → http://localhost:5173
npm run build    # outputs to app/frontend/dist/
```

### Data / Scripts
```bash
# Rebuild feature importance JSON
python scripts/feature_importance.py

# Precompute leave-year-out bracket predictions
python scripts/precompute_brackets.py

# Audit team name normalization
python scripts/audit_names.py

# Profile historical tournament outcomes
python scripts/profile_outcomes.py
```

**Cache:** `data/datacache.pkl` is the precomputed DataCache. Delete it to force a full rebuild on the next backend startup.

---

## Pipeline Architecture

The project has four distinct pipelines. Keep them separated — shared utilities are fine, but outputs of one stage should be explicit artifacts (files) consumed by the next.

### 1. Feature Engineering Pipeline
```
Raw CSVs/Parquets (data/{year}/)
    → src/kenpom.py          # KenPom pre-tournament stats
    → src/scouting.py        # Four Factors + advanced team stats
    → src/player_features.py # Roster composition features
    → src/gameplan_features.py # Last-10-game rolling momentum
    → src/program_features.py  # Program pedigree (tourney/F4 rates)
    → src/features.py        # Assembles matchup-level differential matrix
```
Output: per-team feature vectors, per-game feature rows with labels.

### 2. Training Pipeline
```
src/features.py (matchup feature matrix, 2002–2025)
    → src/model.py           # HistGradientBoostingClassifier
                             # Leave-Year-Out CV + data augmentation
```
Output: trained model artifact, LYO-CV predictions per game.

### 3. Evaluation Pipeline
```
LYO-CV predictions
    → scripts/feature_importance.py   # Permutation importance + correlation
    → scripts/profile_outcomes.py     # Round-by-round accuracy patterns
    → scripts/precompute_brackets.py  # Full simulated bracket per year
```
Output: `config/feature_importance.json`, accuracy metrics, bracket CSVs.

### 4. 2026 Inference Pipeline
```
data/2026/ (raw 2026 data, populated before Selection Sunday)
    → same feature engineering as above (must produce identical columns)
    → trained model (fit on 2002–2025)
    → predicted win probabilities for all 2026 matchups
```
Output: 2026 bracket predictions.

---

## Leakage Rules (Non-Negotiable)

All features must satisfy: **"Would I have known this before the 2026 tournament began?"**

| Feature category | Safe? | Notes |
|-----------------|-------|-------|
| KenPom pre-tournament ratings | Yes | Published before Selection Sunday |
| Regular season scouting stats | Yes | Use pre-tournament cutoff only |
| Last-10-game rolling stats | Yes | Pre-tournament games only |
| Player roster stats | Yes | Based on season stats, not tournament games |
| Program pedigree (tourney rate) | Yes | Computed from prior years only |
| In-tournament game results | **NO** | Leaks future outcomes into features |
| Post-tournament KenPom updates | **NO** | Not available at prediction time |
| Any stat from `bracket.csv` used as a feature | **NO** | Labels only, never features |

When `bracket.csv` is loaded, it is **labels only**. Never join bracket results back into feature rows for the same year.

---

## Feature Alignment: Training vs. 2026

Before adding any feature, verify it can be computed for 2026 with the same code path:

- **Column names** in raw data files must match across years (check with `scripts/audit_names.py`)
- **Player parquet schema** must be identical for 2026 vs. prior years
- **KenPom CSV column names** sometimes change year-to-year — audit before assuming
- **Missing data:** If a feature is missing for some teams in some years, document the imputation strategy and apply it identically in 2026
- **Normalization:** Z-score is computed within-year. The 2026 normalization must use only 2026 tournament teams, not 2026 + historical combined

---

## Feature Predictiveness

Known feature importance ranking (from `config/feature_importance.json` + `analysis/feature_importance.md`):

| Rank | Feature | Correlation | Notes |
|------|---------|-------------|-------|
| 1 | AdjEM (Efficiency Margin) | +0.392 | Strongest single signal |
| 2 | AdjOE (Offensive Efficiency) | +0.325 | |
| 3 | two_way_depth (roster) | +0.301 | Engineered player feature |
| 4 | AdjDE (Defensive Efficiency) | -0.288 | Inverse: lower = better defense |
| 5 | program_tourney_rate_l5 | +0.256 | Coaching/culture proxy |

Round-specific patterns:
- **R1:** AdjEM dominates; defensive stats matter
- **R2–R4:** Offensive capability increases; program pedigree stays critical
- **R5–R6:** Playmaking / TO rate become critical

When evaluating a new feature, report its correlation with outcome and permutation importance drop before deciding to include it.

---

## Model Details

- **Algorithm:** `HistGradientBoostingClassifier` (sklearn) — LightGBM-inspired, handles ~1000-sample yearly folds without overfitting
- **Hyperparams:** max_iter=500, max_leaf_nodes=15, min_samples_leaf=20, learning_rate=0.05, l2_regularization=1.0 — conservative by design
- **Training:** Leave-Year-Out CV: for each held-out year, train on all other years
- **Data augmentation:** Each game is duplicated with team positions swapped + all differential features negated + label flipped → removes KenPom position bias, balances classes to exactly 50/50
- **Validated performance:** 71.4% accuracy (1,444 games, 23 seasons), Brier 0.193, Log Loss 0.581
- **Baseline:** Seed-alone ≈ 58%; AdjEM-alone ≈ 65%; full model ≈ 71%

Before changing the model algorithm or hyperparameters, document the expected change in LYO-CV accuracy and why the tradeoff is worth it.

---

## Data Layout

```
data/
  {year}/                      # 2001–2025 (2020 excluded everywhere)
    summary{YY}_pt.csv         # KenPom pre-tournament stats (FEATURES)
    bracket.csv                # Tournament results (LABELS ONLY)
    scouting/                  # Team advanced stats (parquet)
    players/                   # Player roster stats (parquet)
    gameplan/                  # Game-by-game logs for rolling features
  2026/                        # Populated before Selection Sunday 2026
    summary26_pt.csv
    scouting/
    players/
    gameplan/
  conferences.parquet          # Team → conference mapping
  name_map.json                # Canonical team name lookup
  datacache.pkl                # Pickled DataCache (delete to rebuild)
  feature_importance.json      # Precomputed permutation importance
```

**Stage separation principle:**
- `data/{year}/` = raw data, never modified by scripts
- `datacache.pkl` = processed/featurized intermediate artifact
- Model artifacts and bracket outputs should live in clearly named output directories (e.g., `outputs/models/`, `outputs/brackets/`), not alongside raw data

---

## Source Library (`src/`)

| File | Stage | Role |
|------|-------|------|
| `src/kenpom.py` | Feature Eng. | KenPom CSV loader + column normalization |
| `src/scouting.py` | Feature Eng. | Scouting parquet loader (Four Factors + advanced) |
| `src/player_features.py` | Feature Eng. | Roster composition (star_eup, interior_dom, etc.) |
| `src/gameplan_features.py` | Feature Eng. | Rolling last-10-game momentum (pre-tournament only) |
| `src/program_features.py` | Feature Eng. | Program pedigree from prior years' bracket CSVs |
| `src/features.py` | Feature Eng. | Assembles matchup differential feature matrix |
| `src/model.py` | Training | HistGradientBoostingClassifier, LYO-CV, augmentation |
| `src/names.py` | Utility | Team name normalization via `config/name_map.json` |
| `src/bracket.py` | Utility | Bracket CSV reading/writing |

---

## Backend / App Layer

| File | Role |
|------|------|
| `app/backend/data_loader.py` | `DataCache` — precomputes + caches feature vectors for the similarity UI |
| `app/backend/similarity.py` | Dual-space Euclidean similarity; Gaussian 0–100 scoring |
| `app/backend/bracket_path.py` | Game-by-game path extraction for UI display |
| `app/backend/main.py` | FastAPI routes + static file serving |

The similarity engine is a **UI exploration tool**, separate from the prediction model. The dual-space search (team vectors + player vectors, user-adjustable weights) is for human scouting, not the bracket predictor's win probabilities.

---

## Key Development Rules

- **Name normalization is critical.** Every team name must pass through `src/names.py` / `config/name_map.json` before any join. Silent mismatches drop teams without errors.
- **2020 is always excluded.** No tournament was held. Exclude it in every year loop, every range, every aggregation.
- **Z-score normalization is within-year only.** Never normalize across years. The 2026 inference pass must normalize using only 2026 teams.
- **Scripts over notebooks.** All pipelines must be runnable as `python scripts/foo.py` with no manual intervention. Notebooks may be used for exploration but must not be the authoritative pipeline.
- **Reproducibility.** Deleting `datacache.pkl` and re-running must produce bit-identical results. Random seeds must be set explicitly anywhere randomness is used.
- **Propose before implementing.** For any non-trivial change, describe the approach, identify leakage/alignment risks, and state the expected effect on LYO-CV accuracy before writing code.

---

## Tooling Context

- **Claude Code:** Architecture, reasoning, leakage audits, feature design, pipeline specs
- **Codex:** Implementation of specs produced by Claude
- **Obsidian:** Notes, data dictionary, findings (see `OBSIDIAN_VAULT_PLAN.md`)

When writing specs for Codex, be explicit about: function signatures, column names, expected dtypes, output file paths, and any edge cases (missing data, 2020 exclusion, name normalization). Ambiguity in specs becomes bugs in predictions.
