"""Schema validation and cross-source consistency checks.

Answers two questions an audit must answer before any modelling: does every file
obey the format the submission pipeline assumes, and do the Kaggle files and the
GitHub benchmark actually agree.
"""

from __future__ import annotations

import json
from pathlib import Path

from .corpus import Corpus, Grid

MAX_DIMENSION = 30
VALID_COLOURS = set(range(10))


def _grid_violations(grid: Grid, where: str) -> list[str]:
    problems = []
    if not grid or not grid[0]:
        problems.append(f"{where}: empty grid")
        return problems
    widths = {len(row) for row in grid}
    if len(widths) > 1:
        problems.append(f"{where}: ragged rows {sorted(widths)}")
    if len(grid) > MAX_DIMENSION or max(widths) > MAX_DIMENSION:
        problems.append(f"{where}: exceeds {MAX_DIMENSION}x{MAX_DIMENSION}")
    bad = {c for row in grid for c in row} - VALID_COLOURS
    if bad:
        problems.append(f"{where}: colours outside 0..9 {sorted(bad)}")
    return problems


def validate(corpus: Corpus) -> dict:
    problems = []
    for task in corpus:
        if not task.train:
            problems.append(f"{task.task_id}: no demonstration pairs")
        if not task.test:
            problems.append(f"{task.task_id}: no test pairs")
        for index, pair in enumerate(task.train):
            problems += _grid_violations(pair.input, f"{task.task_id}.train[{index}].input")
            problems += _grid_violations(pair.output, f"{task.task_id}.train[{index}].output")
        for index, pair in enumerate(task.test):
            problems += _grid_violations(pair.input, f"{task.task_id}.test[{index}].input")
            if pair.output is not None:
                problems += _grid_violations(
                    pair.output, f"{task.task_id}.test[{index}].output"
                )
    return {"name": corpus.name, "n_tasks": len(corpus), "violations": problems}


def compare(left: Corpus, right: Corpus) -> dict:
    """Task-level agreement between two corpora that claim to be the same split."""
    left_ids, right_ids = set(left.tasks), set(right.tasks)
    shared = left_ids & right_ids

    def pairs_of(task, attr):
        return [[p.input, p.output] for p in getattr(task, attr)]

    train_differs, test_differs = [], []
    for task_id in sorted(shared):
        a, b = left.tasks[task_id], right.tasks[task_id]
        if pairs_of(a, "train") != pairs_of(b, "train"):
            train_differs.append(
                {
                    "task_id": task_id,
                    f"{left.name}_n_train": len(a.train),
                    f"{right.name}_n_train": len(b.train),
                }
            )
        if pairs_of(a, "test") != pairs_of(b, "test"):
            test_differs.append(
                {
                    "task_id": task_id,
                    f"{left.name}_n_test": len(a.test),
                    f"{right.name}_n_test": len(b.test),
                }
            )
    return {
        "left": left.name,
        "right": right.name,
        "n_shared_ids": len(shared),
        f"only_in_{left.name}": sorted(left_ids - right_ids),
        f"only_in_{right.name}": sorted(right_ids - left_ids),
        "demonstration_pairs_differ": train_differs,
        "test_pairs_differ": test_differs,
    }


def submission_contract(sample_path: Path, test_corpus: Corpus) -> dict:
    """Check the sample submission against the test challenges it must cover."""
    sample = json.loads(sample_path.read_text())
    missing = sorted(set(test_corpus.tasks) - set(sample))
    extra = sorted(set(sample) - set(test_corpus.tasks))
    wrong_length = [
        task_id
        for task_id in set(sample) & set(test_corpus.tasks)
        if len(sample[task_id]) != len(test_corpus.tasks[task_id].test)
    ]
    attempt_keys = sorted(
        {key for entries in sample.values() for entry in entries for key in entry}
    )
    return {
        "source": str(sample_path),
        "n_tasks": len(sample),
        "attempt_keys": attempt_keys,
        "missing_task_ids": missing,
        "unexpected_task_ids": extra,
        "entry_count_mismatches": wrong_length,
    }
