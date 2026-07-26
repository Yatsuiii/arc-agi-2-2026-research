"""ACQ-001 Phase 5 offline oracle analysis for Shard A.

Standalone, read-only: computes candidate-oracle coverage against legal
ARC-AGI-2 training-split ground truth (`arc-agi_training_solutions.json`,
never the public evaluation split, never a Kaggle placeholder). This script
is deliberately kept separate from the acquisition/generation pipeline
(`src/run002c/acquire_shard.py`) -- it must run only after generation is
complete, and its output must never feed back into task selection, solver
behaviour, or verifier training.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

SOLUTIONS_PATH = Path(
    "/home/Yatsuiii/arc-agi-2-2026/competition_2026/extracted/arc-agi_training_solutions.json"
)


def load_candidates_by_key(archive_path: Path) -> dict[tuple[str, int], list[list[list[int]]]]:
    by_key: dict[tuple[str, int], list] = defaultdict(list)
    with gzip.open(archive_path, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r.get("kind") != "candidate":
                continue
            by_key[(r["task_id"], r["test_index"])].append(r["grid"])
    return by_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    solutions = json.loads(SOLUTIONS_PATH.read_text())
    by_key = load_candidates_by_key(args.archive)

    per_task: dict[str, dict] = {}
    n_keys = 0
    n_hit = 0
    for (task_id, test_index), grids in by_key.items():
        n_keys += 1
        truth = solutions[task_id][test_index]
        hit = any(g == truth for g in grids)
        n_hit += hit
        entry = per_task.setdefault(task_id, {"n_test": 0, "n_hit": 0, "per_index": []})
        entry["n_test"] += 1
        entry["n_hit"] += int(hit)
        entry["per_index"].append({"test_index": test_index, "oracle_hit": hit, "n_candidates": len(grids)})

    summary = {
        "archive": str(args.archive),
        "n_test_indices": n_keys,
        "n_oracle_hit": n_hit,
        "oracle_coverage": n_hit / n_keys if n_keys else 0.0,
        "per_task": per_task,
    }
    args.out.write_text(json.dumps(summary, indent=2))
    print(f"n_test_indices={n_keys} n_oracle_hit={n_hit} coverage={summary['oracle_coverage']:.4f}")


if __name__ == "__main__":
    main()
