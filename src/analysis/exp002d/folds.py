"""EXP002-D Phase 2: task-grouped, family-stratified fold assignment.

Frozen before any model touches labels. A task never crosses an outer-fold
boundary; within each outer fold's training partition, a further
task-grouped 80/20 split produces an inner calibration set.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import pandas as pd

FOLD_SEED = 20260727
N_OUTER_FOLDS = 5
INNER_CALIBRATION_FRACTION = 0.2

REPO_ROOT = Path(__file__).resolve().parents[3]


def assign_outer_folds(task_families: dict[str, str], seed: int = FOLD_SEED) -> dict[str, int]:
    """Stratified round-robin: shuffle each family's task list, then deal
    into N_OUTER_FOLDS folds in order, so every family is spread as evenly
    as possible across folds."""
    by_family: dict[str, list[str]] = defaultdict(list)
    for task_id, family in sorted(task_families.items()):
        by_family[family].append(task_id)

    rng = random.Random(seed)
    fold_of: dict[str, int] = {}
    for family, tasks in sorted(by_family.items()):
        tasks = sorted(tasks)
        rng.shuffle(tasks)
        for i, task_id in enumerate(tasks):
            fold_of[task_id] = i % N_OUTER_FOLDS
    return fold_of


def assign_inner_calibration(
    outer_fold_of: dict[str, int], task_families: dict[str, str], seed: int = FOLD_SEED
) -> dict[int, set[str]]:
    """For each outer fold k, choose an inner-calibration task subset drawn
    only from the other four folds' tasks (never from fold k itself, and
    never touching fold k's labels)."""
    inner_calibration: dict[int, set[str]] = {}
    for k in range(N_OUTER_FOLDS):
        train_tasks = [t for t, f in outer_fold_of.items() if f != k]
        by_family: dict[str, list[str]] = defaultdict(list)
        for task_id in sorted(train_tasks):
            by_family[task_families[task_id]].append(task_id)

        rng = random.Random(seed + 1000 + k)
        calibration_tasks: set[str] = set()
        for family, tasks in sorted(by_family.items()):
            tasks = sorted(tasks)
            rng.shuffle(tasks)
            n_calib = max(1, round(len(tasks) * INNER_CALIBRATION_FRACTION)) if len(tasks) >= 3 else 0
            calibration_tasks.update(tasks[:n_calib])
        inner_calibration[k] = calibration_tasks
    return inner_calibration


def build_and_verify(test_index_summary: pd.DataFrame) -> dict:
    task_families = (
        test_index_summary[["task_id", "family"]].drop_duplicates().set_index("task_id")["family"].to_dict()
    )
    outer_fold_of = assign_outer_folds(task_families)
    inner_calibration = assign_inner_calibration(outer_fold_of, task_families)

    # Verify disjointness: every outer fold's task set is disjoint from every other.
    fold_task_sets = {k: {t for t, f in outer_fold_of.items() if f == k} for k in range(N_OUTER_FOLDS)}
    for k1 in range(N_OUTER_FOLDS):
        for k2 in range(k1 + 1, N_OUTER_FOLDS):
            assert fold_task_sets[k1].isdisjoint(fold_task_sets[k2]), f"fold {k1}/{k2} overlap"
    all_tasks = set(task_families)
    assert set.union(*fold_task_sets.values()) == all_tasks, "fold union != full task set"

    for k in range(N_OUTER_FOLDS):
        assert inner_calibration[k].isdisjoint(fold_task_sets[k]), f"inner calibration leaks into outer fold {k}"

    return {
        "fold_seed": FOLD_SEED,
        "n_outer_folds": N_OUTER_FOLDS,
        "inner_calibration_fraction": INNER_CALIBRATION_FRACTION,
        "outer_fold_of_task": outer_fold_of,
        "outer_fold_sizes": {k: len(v) for k, v in fold_task_sets.items()},
        "inner_calibration_tasks_by_fold": {k: sorted(v) for k, v in inner_calibration.items()},
    }


def main() -> None:
    out_dir = REPO_ROOT / "artifacts/EXP002D"
    test_index_summary = pd.read_parquet(out_dir / "test_index_summary.parquet")
    result = build_and_verify(test_index_summary)

    path = out_dir / "fold_assignments.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"outer_fold_sizes={result['outer_fold_sizes']}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
