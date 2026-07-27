"""EXP002-D Phase 8: correctness calibration (rank-1/rank-2 selections) and
candidate-set sufficiency, kept as two separate evaluations per EXP002-B's
three-way confidence split (ranking / correctness / sufficiency).

Platt scaling is fit per outer fold on that fold's own training scores only
(the other four folds' pooled rows), never on the held-out fold's labels.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from src.harness.metrics import brier_score, expected_calibration_error, false_confidence_rate, negative_log_likelihood, reliability_bins

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = REPO_ROOT / "artifacts/EXP002D"
SCORE_COLS = ["score_V1", "score_V2", "score_V3", "score_V4", "score_V5", "score_V6"]


def platt_calibrate_per_fold(pooled: pd.DataFrame, score_col: str) -> np.ndarray:
    """Returns calibrated P(correct) for every row, fit per outer fold on
    the other four folds' rows."""
    calibrated = np.zeros(len(pooled))
    for k in pooled["outer_fold"].unique():
        train_mask = pooled["outer_fold"] != k
        test_mask = pooled["outer_fold"] == k
        X_train = pooled.loc[train_mask, score_col].to_numpy().reshape(-1, 1)
        y_train = pooled.loc[train_mask, "is_correct"].to_numpy(dtype=int)
        if y_train.sum() == 0:
            calibrated[test_mask.to_numpy()] = y_train.mean() if len(y_train) else 0.0
            continue
        clf = LogisticRegression(max_iter=2000)
        clf.fit(X_train, y_train)
        X_test = pooled.loc[test_mask, score_col].to_numpy().reshape(-1, 1)
        calibrated[test_mask.to_numpy()] = clf.predict_proba(X_test)[:, 1]
    return calibrated


def rank1_calibration_report(pooled: pd.DataFrame, score_col: str, calibrated_col: str) -> dict:
    """Per test-index, take the rank-1 (highest-score) candidate only."""
    rank1 = (
        pooled.sort_values(score_col, ascending=False)
        .groupby(["task_id", "test_index"])
        .head(1)
    )
    probs_raw = rank1[score_col].clip(0, 1).tolist()
    probs_calibrated = rank1[calibrated_col].tolist()
    outcomes = rank1["is_correct"].tolist()
    y = np.array(outcomes, dtype=int)

    def _auc_pair(scores):
        if y.sum() == 0 or y.sum() == len(y):
            return None
        return float(roc_auc_score(y, scores))

    return {
        "n_test_indices": len(rank1),
        "n_correct": int(sum(outcomes)),
        "raw_score": {
            "brier_score": brier_score(probs_raw, outcomes),
            "log_loss": negative_log_likelihood(probs_raw, outcomes),
            "ece": expected_calibration_error(probs_raw, outcomes),
            "auroc": _auc_pair(rank1[score_col]),
            "auprc": float(average_precision_score(y, rank1[score_col])) if y.sum() else None,
            "false_confidence_rate_at_0.8": false_confidence_rate(probs_raw, outcomes),
        },
        "platt_calibrated": {
            "brier_score": brier_score(probs_calibrated, outcomes),
            "log_loss": negative_log_likelihood(probs_calibrated, outcomes),
            "ece": expected_calibration_error(probs_calibrated, outcomes),
            "auroc": _auc_pair(probs_calibrated),
            "auprc": float(average_precision_score(y, probs_calibrated)) if y.sum() else None,
            "false_confidence_rate_at_0.8": false_confidence_rate(probs_calibrated, outcomes),
            "reliability_bins": reliability_bins(probs_calibrated, outcomes),
        },
    }


def sufficiency_report(pooled: pd.DataFrame, score_col: str) -> dict:
    """Candidate-set sufficiency: does at least one correct candidate exist
    for this test-index (the oracle indicator), predicted from the
    entropy-based effective-candidate-count of the track's own score
    distribution within the set (same construction as EXP002-B's
    `verifier/base.py::_sufficiency`)."""
    rows = []
    for (task_id, test_index), grp in pooled.groupby(["task_id", "test_index"]):
        scores = grp[score_col].to_numpy(dtype=float)
        scores = scores - scores.max()
        exp_scores = np.exp(scores)
        probs = exp_scores / exp_scores.sum()
        entropy = -np.sum(probs * np.log(probs + 1e-12))
        effective_count = np.exp(entropy)
        sufficiency = 0.0 if len(grp) <= 1 else min(1.0, (effective_count - 1) / 2)
        rows.append({"task_id": task_id, "test_index": test_index, "sufficiency": sufficiency,
                      "oracle_hit": bool(grp["is_correct"].any())})
    df = pd.DataFrame(rows)
    y = df["oracle_hit"].to_numpy(dtype=int)
    return {
        "n_test_indices": len(df),
        "n_oracle_hit": int(y.sum()),
        "brier_score": brier_score(df["sufficiency"].tolist(), df["oracle_hit"].tolist()),
        "auroc": float(roc_auc_score(y, df["sufficiency"])) if 0 < y.sum() < len(y) else None,
        "auprc": float(average_precision_score(y, df["sufficiency"])) if y.sum() else None,
        "ece": expected_calibration_error(df["sufficiency"].tolist(), df["oracle_hit"].tolist()),
        "mean_sufficiency_when_hit": float(df.loc[df["oracle_hit"], "sufficiency"].mean()) if y.sum() else None,
        "mean_sufficiency_when_miss": float(df.loc[~df["oracle_hit"], "sufficiency"].mean()),
    }


def main() -> None:
    pooled = pd.read_parquet(ARTIFACT_DIR / "model_predictions.parquet")
    result = {"rank1_calibration": {}, "sufficiency": {}}
    for col in SCORE_COLS:
        calibrated_col = col + "_calibrated"
        pooled[calibrated_col] = platt_calibrate_per_fold(pooled, col)
        result["rank1_calibration"][col] = rank1_calibration_report(pooled, col, calibrated_col)
        result["sufficiency"][col] = sufficiency_report(pooled, col)

    out_path = ARTIFACT_DIR / "calibration.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"wrote {out_path}")
    for col, r in result["rank1_calibration"].items():
        print(f"{col}: brier(raw)={r['raw_score']['brier_score']:.4f} "
              f"brier(calibrated)={r['platt_calibrated']['brier_score']:.4f} "
              f"auroc={r['raw_score']['auroc']}")


if __name__ == "__main__":
    main()
