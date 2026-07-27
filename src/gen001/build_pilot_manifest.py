"""Freeze GEN001-A's 24-index pilot sample, before any NVARC prediction exists.

Draws deterministically from EXP002-D's already-computed error taxonomy
(`artifacts/EXP002D/error_taxonomy.csv`) and task statistics
(`artifacts/data_audit/task_statistics.csv`). No randomness, no expectation
of NVARC success informs the selection — only CompressARC's already-frozen
outcome label (which group a test-index belongs to) and task structural
descriptors (which candidates are chosen within a group, for stratification).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ERROR_TAXONOMY = ROOT / "artifacts" / "EXP002D" / "error_taxonomy.csv"
TASK_STATS = ROOT / "artifacts" / "data_audit" / "task_statistics.csv"
OUT_MANIFEST = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"

N_GROUP_A = 12
N_GROUP_B = 6
N_GROUP_C = 6


def _stratified_pick(pool: pd.DataFrame, n: int) -> list[str]:
    """Deterministic stride sample over a pool sorted by structural descriptors.

    Sorting by (size_relation, large_grid, n_input_colours, task_id,
    test_index) then striding evenly across the sorted list spans the
    distribution of structural properties without any random draw or any
    reference to which candidates NVARC might solve.
    """
    ordered = pool.sort_values(
        ["size_relation", "large_grid", "n_input_colours", "task_id", "test_index"]
    ).reset_index(drop=True)
    if len(ordered) <= n:
        return list(ordered.index)
    stride = len(ordered) / n
    picks = [int(i * stride) for i in range(n)]
    return picks


def build_pilot_sample() -> dict:
    taxonomy = pd.read_csv(ERROR_TAXONOMY)
    stats = pd.read_csv(TASK_STATS)[
        ["task_id", "size_relation", "large_grid", "n_input_colours", "objects_input_mean"]
    ]
    merged = taxonomy.merge(stats, on="task_id", how="left")

    pool_a = merged[~merged["oracle_hit"]]
    pool_b = merged[merged["oracle_hit"] & ~merged["native_top2_hit"]]
    pool_c = merged[merged["native_top2_hit"]]

    rows = []
    for group_name, pool, n in (
        ("A", pool_a, N_GROUP_A),
        ("B", pool_b, N_GROUP_B),
        ("C", pool_c, N_GROUP_C),
    ):
        ordered = pool.sort_values(
            ["size_relation", "large_grid", "n_input_colours", "task_id", "test_index"]
        ).reset_index(drop=True)
        stride = len(ordered) / n
        idx = sorted({int(i * stride) for i in range(n)})
        while len(idx) < n:
            for candidate_i in range(len(ordered)):
                if candidate_i not in idx:
                    idx.append(candidate_i)
                    break
            idx = sorted(idx)
        for i in idx[:n]:
            row = ordered.iloc[i]
            rows.append(
                {
                    "group": group_name,
                    "task_id": row["task_id"],
                    "test_index": int(row["test_index"]),
                    "compressarc_oracle_hit": bool(row["oracle_hit"]),
                    "compressarc_native_top2_hit": bool(row["native_top2_hit"]),
                    "size_relation": row["size_relation"],
                    "large_grid": bool(row["large_grid"]),
                    "n_input_colours": int(row["n_input_colours"])
                    if pd.notna(row["n_input_colours"])
                    else None,
                    "objects_input_mean": float(row["objects_input_mean"])
                    if pd.notna(row["objects_input_mean"])
                    else None,
                }
            )

    manifest = {
        "acquisition": "GEN001A",
        "pilot_n_test_indices": len(rows),
        "group_sizes": {"A": N_GROUP_A, "B": N_GROUP_B, "C": N_GROUP_C},
        "selection_rule": (
            "Deterministic: sort each group's pool by (size_relation, "
            "large_grid, n_input_colours, task_id, test_index), then take "
            "an evenly-strided sample. No randomness. No selection based "
            "on expected NVARC outcome."
        ),
        "source_taxonomy": "artifacts/EXP002D/error_taxonomy.csv",
        "source_task_stats": "artifacts/data_audit/task_statistics.csv",
        "test_indices": rows,
    }
    return manifest


def main() -> None:
    manifest = build_pilot_sample()
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {OUT_MANIFEST} ({manifest['pilot_n_test_indices']} test-indices)")
    for group in "ABC":
        n = sum(1 for r in manifest["test_indices"] if r["group"] == group)
        print(f"  Group {group}: {n}")


if __name__ == "__main__":
    main()
