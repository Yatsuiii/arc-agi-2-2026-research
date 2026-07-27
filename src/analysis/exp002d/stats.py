"""EXP002-D Phase 9: statistical tests, paired at the test-index level.

Never at the raw candidate-row level -- candidates within a test-index are
dependent, so the statistical unit here is (task_id, test_index), and
McNemar/bootstrap resampling always keeps a task's test-indices intact
within a resample (grouped, not i.i.d. resampling of rows).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = REPO_ROOT / "artifacts/EXP002D"
CANDIDATE_ORACLE = 0.2456140350877193  # restated, recomputed in corpus.py
NATIVE_TOP2 = 0.13450292397660818


def oracle_gap_recovery(verifier_top2: float, native_top2: float = NATIVE_TOP2, oracle: float = CANDIDATE_ORACLE) -> float | None:
    denom = oracle - native_top2
    if denom == 0:
        return None
    return (verifier_top2 - native_top2) / denom


def mcnemar(track_hits: pd.Series, v0_hits: pd.Series) -> dict:
    """Exact McNemar (binomial test on the discordant pairs)."""
    both = pd.DataFrame({"track": track_hits.values, "v0": v0_hits.values})
    b = int(((both["track"]) & (~both["v0"])).sum())  # track right, V0 wrong (rescue)
    c = int(((~both["track"]) & (both["v0"])).sum())  # track wrong, V0 right (regression)
    n_discordant = b + c
    if n_discordant == 0:
        return {"n_rescues": b, "n_regressions": c, "n_discordant": 0, "p_value": 1.0}
    result = binomtest(min(b, c), n_discordant, 0.5)
    return {"n_rescues": b, "n_regressions": c, "n_discordant": n_discordant, "p_value": float(result.pvalue)}


def stratified_bootstrap_ci(
    df: pd.DataFrame, hit_col: str, fold_col: str = "outer_fold", n_resamples: int = 2000, seed: int = 20260727,
) -> dict:
    """Resample task-groups within each fold stratum, recompute the mean
    hit rate, and report the 2.5/97.5 percentiles."""
    rng = np.random.RandomState(seed)
    folds = df[fold_col].unique()
    task_groups = {
        fold: [g["task_id"].values for _, g in df[df[fold_col] == fold].groupby("task_id")]
        for fold in folds
    }
    means = []
    for _ in range(n_resamples):
        resampled_rows = []
        for fold in folds:
            groups = task_groups[fold]
            n = len(groups)
            picks = rng.randint(0, n, size=n)
            for p in picks:
                resampled_rows.append(groups[p])
        resampled_task_ids = np.concatenate(resampled_rows) if resampled_rows else np.array([])
        # Weight by occurrence: build a value array directly instead of re-merging for speed.
        hits = df.set_index("task_id").loc[resampled_task_ids][hit_col]
        means.append(hits.mean())
    means = np.array(means)
    return {
        "mean": float(df[hit_col].mean()),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
        "n_resamples": n_resamples,
    }


def per_fold_breakdown(df: pd.DataFrame, hit_col: str, fold_col: str = "outer_fold") -> dict:
    return {int(k): float(v) for k, v in df.groupby(fold_col)[hit_col].mean().items()}


def main() -> None:
    track_results = pd.read_parquet(ARTIFACT_DIR / "test_index_track_results.parquet")
    predictions = pd.read_parquet(ARTIFACT_DIR / "model_predictions.parquet")
    fold_lookup = predictions[["task_id", "test_index", "outer_fold"]].drop_duplicates()

    v0 = pd.read_parquet(ARTIFACT_DIR / "test_index_summary.parquet")[
        ["task_id", "test_index", "native_top1_hit", "native_top2_hit"]
    ]

    tracks = [t for t in track_results["track"].unique()]
    metrics = {}
    for track in tracks:
        sub = track_results[track_results["track"] == track].merge(
            v0, on=["task_id", "test_index"]
        ).merge(fold_lookup, on=["task_id", "test_index"])

        top2_acc = float(sub["top2_hit"].mean())
        top1_acc = float(sub["top1_hit"].mean())
        mrr = float(sub["mrr"].mean())
        gap_recovery = oracle_gap_recovery(top2_acc)
        mcn = mcnemar(sub["top2_hit"], sub["native_top2_hit"])
        boot = stratified_bootstrap_ci(sub, "top2_hit")
        per_fold = per_fold_breakdown(sub, "top2_hit")

        metrics[track] = {
            "top1_accuracy": top1_acc,
            "top2_accuracy": top2_acc,
            "mrr": mrr,
            "oracle_gap_recovery": gap_recovery,
            "mcnemar_vs_v0": mcn,
            "bootstrap_ci": boot,
            "per_fold_top2_accuracy": per_fold,
            "absolute_gain_vs_native": top2_acc - NATIVE_TOP2,
            "relative_gain_vs_native": (top2_acc - NATIVE_TOP2) / NATIVE_TOP2,
        }

    out_path = ARTIFACT_DIR / "metrics.json"
    out_path.write_text(json.dumps(metrics, indent=2))
    print(f"wrote {out_path}")
    for track, m in metrics.items():
        print(f"{track}: top2={m['top2_accuracy']:.4f} gap_recovery={m['oracle_gap_recovery']} "
              f"rescues={m['mcnemar_vs_v0']['n_rescues']} regressions={m['mcnemar_vs_v0']['n_regressions']} "
              f"p={m['mcnemar_vs_v0']['p_value']:.3f}")


if __name__ == "__main__":
    main()
