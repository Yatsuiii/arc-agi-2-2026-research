"""EXP002-D Phase 5-6: verifier model families and class-imbalance handling.

All models are pointwise or linear-pairwise classifiers over a fixed
feature set, fit per outer fold on that fold's 4-fold training partition
only. No neural network, no GPU, no broad hyperparameter search (a single
fixed `LogisticRegression` and a single fixed `HistGradientBoostingClassifier`
configuration are the only two model types used anywhere).
"""

from __future__ import annotations

import random

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

F0F1 = ["beam_score_best", "beam_score_mean", "beam_score_min", "beam_score_percentile", "native_rank_or_zero"]
STRUCTURAL = [
    "output_size_matches_expected", "n_colours_introduced_by_candidate", "n_colours_removed_by_candidate",
    "introduced_colours_seen_in_demos", "removed_colours_seen_in_demos", "symmetry_agreement_with_demo_outputs",
    "object_count", "object_count_consistent_with_demo_pattern", "tiling_pattern_consistent_with_demos",
    "is_degenerate_input_copy", "is_degenerate_constant_fill", "is_valid_grid", "grid_complexity",
    "contradiction_count",
]
F5_PROVENANCE = ["task_steps_run", "task_elapsed_s", "task_hit_time_guard"]
F4_RELATIONAL = ["consensus_frequency", "distance_from_modal", "mean_distance_from_set", "discovery_order_frac"]

FEATURE_SETS = {
    "F0F1": F0F1,
    "STRUCTURAL": STRUCTURAL,
    "V2": STRUCTURAL + F5_PROVENANCE,
    "V4": F0F1 + STRUCTURAL + F5_PROVENANCE + F4_RELATIONAL,
}


def make_logreg(seed: int) -> LogisticRegression:
    return LogisticRegression(C=1.0, max_iter=5000, class_weight="balanced", random_state=seed)


def make_hgb(seed: int) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(max_iter=100, max_depth=4, random_state=seed)


def negative_sample(
    train_df: pd.DataFrame, seed: int, max_hard: int = 20, max_easy: int = 5,
    hard_by: str = "beam_score_percentile",
) -> pd.DataFrame:
    """Preserve all positives; per test-index, keep up to `max_hard`
    negatives ranked highest by `hard_by` (near the native top / most
    consensus-heavy wrong candidates) plus up to `max_easy` random
    negatives. Deterministic given `seed`."""
    rng = random.Random(seed)
    kept_frames = []
    for _, grp in train_df.groupby(["task_id", "test_index"]):
        pos = grp[grp["is_correct"]]
        neg = grp[~grp["is_correct"]]
        kept_frames.append(pos)
        if len(neg) == 0:
            continue
        hard = neg.sort_values(hard_by, ascending=False).head(max_hard)
        remaining = neg.drop(hard.index)
        n_easy = min(max_easy, len(remaining))
        easy_idx = rng.sample(list(remaining.index), n_easy) if n_easy else []
        kept_frames.append(hard)
        if easy_idx:
            kept_frames.append(remaining.loc[easy_idx])
    return pd.concat(kept_frames, ignore_index=True) if kept_frames else train_df.iloc[0:0]


def fit_pointwise(train_df: pd.DataFrame, feature_cols: list[str], model_type: str, seed: int):
    sampled = negative_sample(train_df, seed)
    X = sampled[feature_cols].to_numpy(dtype=float)
    y = sampled["is_correct"].to_numpy(dtype=int)
    model = make_logreg(seed) if model_type == "logreg" else make_hgb(seed)
    model.fit(X, y)
    return model


def score_pointwise(model, df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    X = df[feature_cols].to_numpy(dtype=float)
    return model.predict_proba(X)[:, 1]


def fit_pairwise_linear(
    train_df: pd.DataFrame, feature_cols: list[str], seed: int, max_hard: int = 20, max_easy: int = 5,
) -> tuple[np.ndarray, LogisticRegression]:
    """RankNet-style linear pairwise ranker: fit logistic regression on
    (winner - loser) feature-difference vectors (and the mirrored, negated
    pair) so the fitted weight vector is a valid linear scoring function --
    ranking candidates by `weights . features(candidate)` reproduces the
    pairwise comparisons the model was trained on."""
    rng = random.Random(seed)
    diffs, labels = [], []
    for _, grp in train_df.groupby(["task_id", "test_index"]):
        pos = grp[grp["is_correct"]]
        neg = grp[~grp["is_correct"]]
        if len(pos) == 0 or len(neg) == 0:
            continue
        hard = neg.sort_values("beam_score_percentile", ascending=False).head(max_hard)
        remaining = neg.drop(hard.index)
        n_easy = min(max_easy, len(remaining))
        easy_idx = rng.sample(list(remaining.index), n_easy) if n_easy else []
        neg_sample = pd.concat([hard, remaining.loc[easy_idx]]) if easy_idx else hard
        pos_X = pos[feature_cols].to_numpy(dtype=float)
        neg_X = neg_sample[feature_cols].to_numpy(dtype=float)
        for p in pos_X:
            for n in neg_X:
                diffs.append(p - n)
                labels.append(1)
                diffs.append(n - p)
                labels.append(0)
    if not diffs:
        return np.zeros(len(feature_cols)), None
    X = np.array(diffs)
    y = np.array(labels)
    clf = LogisticRegression(C=1.0, max_iter=5000, fit_intercept=False, random_state=seed)
    clf.fit(X, y)
    return clf.coef_[0], clf


def score_pairwise(weights: np.ndarray, df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    X = df[feature_cols].to_numpy(dtype=float)
    return X @ weights


def fit_ensemble_weights(
    inner_calib_scores: pd.DataFrame, score_cols: list[str], grid: list[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> dict[str, float]:
    """Grid search over normalised combination weights, maximising top-2
    test-index accuracy on the inner-calibration split only (never the
    outer test fold)."""
    import itertools

    best_weights, best_acc = None, -1.0
    for combo in itertools.product(grid, repeat=len(score_cols)):
        if sum(combo) == 0:
            continue
        weights = {c: w / sum(combo) for c, w in zip(score_cols, combo)}
        combined = sum(inner_calib_scores[c] * w for c, w in weights.items())
        scored = inner_calib_scores.assign(_score=combined)
        acc = _top2_accuracy_naive(scored)
        if acc > best_acc:
            best_acc, best_weights = acc, weights
    return best_weights


def _top2_accuracy_naive(scored: pd.DataFrame) -> float:
    hits = 0
    n = 0
    for _, grp in scored.groupby(["task_id", "test_index"]):
        n += 1
        top2 = grp.sort_values("_score", ascending=False).head(2)
        hits += int(top2["is_correct"].any())
    return hits / n if n else 0.0
