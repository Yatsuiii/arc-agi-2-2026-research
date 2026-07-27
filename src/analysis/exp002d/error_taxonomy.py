"""EXP002-D Phase 11: per-test-index error taxonomy, V0 (native) vs V4
(the best-performing non-trivial alternative track measured in Phase 5-9)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = REPO_ROOT / "artifacts/EXP002D"


def classify(row) -> str:
    oracle = row["oracle_hit"]
    native = row["native_top2_hit"]
    verifier = row["v4_top2_hit"]
    sufficiency = row.get("sufficiency", None)

    if not oracle:
        return "1_generation_failure"
    if not native and not verifier:
        if sufficiency is not None and sufficiency < 0.1:
            return "8_candidate_set_insufficiency_correctly_identified"
        return "7_both_fail_correct_candidate_present"
    if native and verifier:
        return "6_both_succeed"
    if native and not verifier:
        return "4_native_only_success"
    if verifier and not native:
        return "5_verifier_rescue"
    return "2_ranking_failure"


def main() -> None:
    v0 = pd.read_parquet(ARTIFACT_DIR / "test_index_summary.parquet")
    track_results = pd.read_parquet(ARTIFACT_DIR / "test_index_track_results.parquet")
    v4 = track_results[track_results["track"] == "V4"][["task_id", "test_index", "top2_hit", "correct_rank"]]
    v4 = v4.rename(columns={"top2_hit": "v4_top2_hit", "correct_rank": "v4_correct_rank"})

    import numpy as np

    predictions = pd.read_parquet(ARTIFACT_DIR / "model_predictions.parquet")
    suff_rows = []
    for (task_id, test_index), grp in predictions.groupby(["task_id", "test_index"]):
        scores = grp["score_V4"].to_numpy(dtype=float)
        scores = scores - scores.max()
        exp_scores = np.exp(scores)
        probs = exp_scores / exp_scores.sum()
        entropy = -np.sum(probs * np.log(probs + 1e-12))
        effective_count = np.exp(entropy)
        sufficiency = 0.0 if len(grp) <= 1 else min(1.0, (effective_count - 1) / 2)
        suff_rows.append({"task_id": task_id, "test_index": test_index, "sufficiency": sufficiency})
    suff_df = pd.DataFrame(suff_rows)

    merged = v0.merge(v4, on=["task_id", "test_index"]).merge(suff_df, on=["task_id", "test_index"])
    merged["category"] = merged.apply(classify, axis=1)

    out_path = ARTIFACT_DIR / "error_taxonomy.csv"
    merged[["task_id", "test_index", "family", "oracle_hit", "native_top2_hit", "v4_top2_hit",
            "sufficiency", "category"]].to_csv(out_path, index=False)

    counts = merged["category"].value_counts().sort_index()
    print(counts)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
