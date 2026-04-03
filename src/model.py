"""Train and evaluate the tournament game prediction model.

Uses HistGradientBoostingClassifier (sklearn's LightGBM-inspired implementation)
with leave-year-out cross-validation.

Main entry points:
    leave_year_out_cv(df)  -> pd.DataFrame  (predictions for every game)
    report(cv_df)          -> None          (print summary metrics)
    train(df)              -> fitted model
    save(model, path) / load(path)
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import brier_score_loss, log_loss

from src.features import DIFF_FEATURES

MODEL_PATH = Path(__file__).parent.parent / 'model.joblib'


# ── Model factory ─────────────────────────────────────────────────────────────

def _make_model() -> HistGradientBoostingClassifier:
    # Conservative hyperparameters for ~1000-sample folds.
    # Small trees + high min_samples_leaf prevent overfitting on this dataset size.
    return HistGradientBoostingClassifier(
        max_iter=500,
        max_leaf_nodes=15,
        min_samples_leaf=20,
        learning_rate=0.05,
        l2_regularization=1.0,
        random_state=42,
    )


# ── Data augmentation ─────────────────────────────────────────────────────────

def augment(df: pd.DataFrame) -> pd.DataFrame:
    """Double the dataset by adding a position-flipped copy of each game.

    For each row (team1 vs team2), adds a mirror row (team2 vs team1) with
    all diffs negated and label flipped. Applied to training data only.

    This removes position bias and balances labels to exactly 50/50, so the
    model learns from stat differentials rather than team ordering.
    """
    diff_cols = [c for c in DIFF_FEATURES if c in df.columns]
    flipped = df.copy()
    flipped[diff_cols] = -flipped[diff_cols].values
    flipped['label'] = 1 - flipped['label']
    flipped[['team1', 'team2']] = flipped[['team2', 'team1']].values
    return pd.concat([df, flipped], ignore_index=True)


# ── Cross-validation ──────────────────────────────────────────────────────────

def leave_year_out_cv(df: pd.DataFrame) -> pd.DataFrame:
    """Leave-year-out cross-validation.

    For each year, trains on all other years (augmented) and predicts on that
    year (not augmented — real game direction preserved for metric calculation).

    Returns:
        DataFrame with all original columns plus:
            prob  — predicted P(team1 wins)
            pred  — predicted winner (1 = team1, 0 = team2)
    """
    years = sorted(df['year'].unique())
    preds = []

    for test_year in years:
        train = augment(df[df['year'] != test_year])
        test = df[df['year'] == test_year].copy()

        feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
        model = _make_model()
        model.fit(train[feat_cols], train['label'])

        proba = model.predict_proba(test[feat_cols])[:, 1]
        test['prob'] = proba
        test['pred'] = (proba >= 0.5).astype(int)
        preds.append(test)

    return pd.concat(preds, ignore_index=True)


# ── Reporting ─────────────────────────────────────────────────────────────────

def _seed_baseline_acc(df: pd.DataFrame) -> float:
    """Accuracy of naively picking the better-seeded team (seed_diff < 0 → team1 wins)."""
    sub = df[df['seed_diff'].notna()]
    return ((sub['seed_diff'] < 0) == sub['label'].astype(bool)).mean()


def report(cv_df: pd.DataFrame) -> None:
    """Print a human-readable summary of leave-year-out CV results."""
    feat_cols = [c for c in DIFF_FEATURES if c in cv_df.columns]
    acc      = (cv_df['pred'] == cv_df['label']).mean()
    brier    = brier_score_loss(cv_df['label'], cv_df['prob'])
    ll       = log_loss(cv_df['label'], cv_df['prob'])
    baseline = _seed_baseline_acc(cv_df)

    print('=' * 52)
    print('Leave-Year-Out CV Results')
    print('=' * 52)
    print(f'  Games evaluated : {len(cv_df)}')
    print(f'  Features used   : {len(feat_cols)}')
    print(f'  Accuracy        : {acc:.3f}')
    print(f'  Seed baseline   : {baseline:.3f}')
    print(f'  Brier score     : {brier:.4f}  (lower = better, 0.25 = random)')
    print(f'  Log loss        : {ll:.4f}  (lower = better, 0.693 = random)')

    print()
    print('Accuracy by round:')
    for rnd, grp in cv_df.groupby('round'):
        racc = (grp['pred'] == grp['label']).mean()
        bar = '#' * int(racc * 30)
        print(f'  R{rnd}  ({len(grp):3d} games)  {racc:.3f}  {bar}')

    print()
    print('Accuracy by year:')
    for year, grp in cv_df.groupby('year'):
        yacc = (grp['pred'] == grp['label']).mean()
        bar = '#' * int(yacc * 30)
        print(f'  {int(year)}  ({len(grp):2d} games)  {yacc:.3f}  {bar}')


# ── Training ──────────────────────────────────────────────────────────────────

def train(df: pd.DataFrame) -> HistGradientBoostingClassifier:
    """Train on the full dataset (augmented). Use for bracket simulation."""
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
    aug = augment(df)
    model = _make_model()
    model.fit(aug[feat_cols], aug['label'])
    return model


def feature_importances(
    model: HistGradientBoostingClassifier,
    df: pd.DataFrame,
    n_repeats: int = 20,
) -> pd.Series:
    """Return permutation importances (mean accuracy drop) sorted descending.

    Uses the supplied df as evaluation data. Pass the full matchup df
    (unaugmented) for a representative picture.
    """
    feat_cols = [c for c in DIFF_FEATURES if c in df.columns]
    result = permutation_importance(
        model, df[feat_cols], df['label'],
        n_repeats=n_repeats, random_state=42, scoring='accuracy',
    )
    return (
        pd.Series(result.importances_mean, index=feat_cols)
        .sort_values(ascending=False)
    )


# ── Persistence ───────────────────────────────────────────────────────────────

def save(model: HistGradientBoostingClassifier, path: Path | str = MODEL_PATH) -> None:
    joblib.dump(model, path)
    print(f'Model saved -> {path}')


def load(path: Path | str = MODEL_PATH) -> HistGradientBoostingClassifier:
    return joblib.load(path)
