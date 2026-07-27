"""The analysis a future NVARC pilot's output is fed into (Phase 11).

Written now, against synthetic fixtures, so the metric a real pilot is
judged by is fixed before that pilot's output exists — the same discipline
`experiments/EXP002D/PLAN.md` applied to its own verifier evaluation.

Computes set-complementarity metrics only (`experiments/GEN001A/GENERATOR_COMPARISON.md`):
oracle coverage per generator, union oracle, incremental coverage, overlap,
Jaccard. No model is fit here — this is oracle-union set arithmetic, per the
acceptance message's explicit "a simple oracle-union analysis is sufficient,
do not fit another learned verifier" instruction.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.run001.archive import read_records


@dataclass(frozen=True)
class UnionMetrics:
    n_indices: int
    compressarc_oracle: float
    nvarc_oracle: float
    union_oracle: float
    incremental_nvarc_coverage: int
    overlap: int
    compressarc_only: int
    jaccard: float


def _oracle_hit_set(
    candidate_records: list[dict], solutions: dict[str, list[list[list[int]]]]
) -> set[tuple[str, int]]:
    """(task_id, test_index) pairs where some candidate grid matches the
    ground-truth output. `solutions` is supplied by the caller and is never
    read by generation code — only by this post-hoc analysis step."""
    hits: set[tuple[str, int]] = set()
    by_key: dict[tuple[str, int], list[list]] = {}
    for record in candidate_records:
        if record.get("kind") != "candidate":
            continue
        key = (record["task_id"], record["test_index"])
        by_key.setdefault(key, []).append(record["grid"])

    for (task_id, test_index), grids in by_key.items():
        target = solutions.get(task_id)
        if target is None or test_index >= len(target):
            continue
        if any(grid == target[test_index] for grid in grids):
            hits.add((task_id, test_index))
    return hits


def compute_union_metrics(
    compressarc_records: list[dict],
    nvarc_records: list[dict],
    solutions: dict[str, list[list[list[int]]]],
    pilot_indices: set[tuple[str, int]],
) -> UnionMetrics:
    c_hits = _oracle_hit_set(compressarc_records, solutions) & pilot_indices
    n_hits = _oracle_hit_set(nvarc_records, solutions) & pilot_indices

    n = len(pilot_indices)
    union = c_hits | n_hits
    overlap = c_hits & n_hits
    incremental = n_hits - c_hits
    c_only = c_hits - n_hits
    jaccard = len(overlap) / len(union) if union else 0.0

    return UnionMetrics(
        n_indices=n,
        compressarc_oracle=len(c_hits) / n if n else 0.0,
        nvarc_oracle=len(n_hits) / n if n else 0.0,
        union_oracle=len(union) / n if n else 0.0,
        incremental_nvarc_coverage=len(incremental),
        overlap=len(overlap),
        compressarc_only=len(c_only),
        jaccard=jaccard,
    )


def load_archive_records(path) -> list[dict]:
    return list(read_records(path))
