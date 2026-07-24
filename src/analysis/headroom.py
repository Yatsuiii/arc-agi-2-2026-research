"""EXP001 Stage A: selection headroom and compute headroom from recorded traces.

Reads CompressARC's published per-task solution logs and answers two questions
the ARC literature has never separated: how often is the correct answer produced
and then not chosen, and how much accuracy would perfect budget allocation buy.

CompressARC is used because it is the only solver in the workspace that ships
recorded per-task traces, it is MIT licensed, and it has no pretraining at all,
so no task it was evaluated on can have leaked into it. The benchmark is
ARC-AGI-1; see experiments/EXP001/PLAN.md §10 for why that is the right stage-A
choice and what it does and does not establish.

Trace format, reverse-engineered from the reference implementation
(references/paper_winners/03_compressarc/list_solved_puzzles.py):

    solution_contribution_logs[task, step, i] = (hash, score)

for i in {0, 1}, the two solutions logged at that step. Scores for the same hash
accumulate by log-sum-exp across steps, and candidates rank by accumulated score.
Hashes are compared after `>> 16`, matching the reference.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

COMPRESSARC = (
    Path(__file__).resolve().parents[3]
    / "references"
    / "paper_winners"
    / "03_compressarc"
)
TOTAL_STEPS = 2000
HASH_SHIFT = 16


def true_hashes(split: str) -> list[int]:
    """Ground-truth solution hash per task, in the trace's task order.

    Reproduces `Task._create_solution_tensor`: the hash of a tuple of grids,
    each grid a tuple of row tuples. CPython hashes integer tuples
    deterministically, so this is stable across processes without
    PYTHONHASHSEED.
    """
    challenges = json.loads(
        (COMPRESSARC / "dataset" / f"arc-agi_{split}_challenges.json").read_text()
    )
    solutions = json.loads(
        (COMPRESSARC / "dataset" / f"arc-agi_{split}_solutions.json").read_text()
    )
    return [
        hash(tuple(tuple(map(tuple, grid)) for grid in solutions[task_id]))
        for task_id in challenges
    ]


def rank_of_truth(task_log: np.ndarray, truth: int, steps: int) -> int | None:
    """Rank of the true solution after `steps`, or None if never proposed.

    Rank 1 is the top-scored candidate. Mirrors the reference implementation's
    log-sum-exp accumulation and its descending sort.
    """
    target = truth >> HASH_SHIFT
    accumulated: dict[int, float] = defaultdict(lambda: -math.inf)
    for step in range(min(steps, len(task_log))):
        for hashed, score in task_log[step]:
            key = int(hashed) >> HASH_SHIFT
            accumulated[key] = np.logaddexp(accumulated[key], float(score))
    if target not in accumulated:
        return None
    better = sum(1 for score in accumulated.values() if score > accumulated[target])
    return better + 1


def ranks_at(logs: np.ndarray, truths: list[int], steps: int) -> list[int | None]:
    return [rank_of_truth(logs[i], truths[i], steps) for i in range(len(truths))]


def _first_budget_solving(logs, truths, budgets, k) -> list[int | None]:
    """Smallest budget in `budgets` at which each task is solved within top k."""
    minimum: list[int | None] = [None] * len(truths)
    for budget in budgets:
        for task, rank in enumerate(ranks_at(logs, truths, budget)):
            if minimum[task] is None and rank is not None and rank <= k:
                minimum[task] = budget
    return minimum


def analyse(split: str, budgets: list[int], k_values: list[int]) -> dict:
    logs = np.load(
        COMPRESSARC / "results_for_the_blog_post" / f"predictions_{split}.npz",
        allow_pickle=True,
    )["solution_contribution_logs"]
    truths = true_hashes(split)
    n = len(truths)

    full = ranks_at(logs, truths, TOTAL_STEPS)
    realised = sum(1 for r in full if r is not None and r <= 2)

    selection_headroom = {
        f"oracle@{k}": sum(1 for r in full if r is not None and r <= k)
        for k in k_values
    }
    selection_headroom["oracle@any"] = sum(1 for r in full if r is not None)
    selection_headroom["realised@2"] = realised

    # Compute headroom: uniform gives every task the same budget; the oracle
    # spends each task's minimum sufficient budget and abandons the rest. Both
    # are held to the same total, so the comparison is like for like.
    minimum_budget = _first_budget_solving(logs, truths, budgets, k=2)
    uniform_curve = {
        budget: sum(
            1 for m in minimum_budget if m is not None and m <= budget
        )
        for budget in budgets
    }
    sufficient = sorted(m for m in minimum_budget if m is not None)
    oracle_curve = {}
    for budget in budgets:
        total = budget * n
        spent = solved = 0
        for cost in sufficient:
            if spent + cost > total:
                break
            spent += cost
            solved += 1
        oracle_curve[budget] = solved

    return {
        "split": split,
        "n_tasks": n,
        "selection": selection_headroom,
        "uniform_accuracy_by_budget": uniform_curve,
        "oracle_allocation_by_budget": oracle_curve,
        "minimum_sufficient_budget_histogram": {
            str(budget): sufficient.count(budget) for budget in budgets
        },
        "never_solved": sum(1 for m in minimum_budget if m is None),
    }


def main() -> None:
    budgets = [50, 100, 200, 400, 800, 1200, 1600, 2000]
    k_values = [1, 2, 3, 5, 10, 20]
    report = {
        "experiment": "EXP001-A",
        "source": str(COMPRESSARC / "results_for_the_blog_post"),
        "benchmark": "ARC-AGI-1 (CompressARC recorded traces)",
        "splits": [analyse(split, budgets, k_values) for split in ("training", "evaluation")],
    }
    out = Path(__file__).resolve().parents[2] / "artifacts" / "exp001"
    out.mkdir(parents=True, exist_ok=True)
    (out / "headroom.json").write_text(json.dumps(report, indent=2) + "\n")

    for result in report["splits"]:
        n = result["n_tasks"]
        sel = result["selection"]
        print(f"\n=== {result['split']}  (n={n}) ===")
        print(f"  realised@2      {sel['realised@2']:4d}  {sel['realised@2']/n:6.2%}")
        for key in sorted(sel, key=lambda s: (s == "oracle@any", s)):
            if key.startswith("oracle"):
                print(f"  {key:15s} {sel[key]:4d}  {sel[key]/n:6.2%}")
        gap = sel["oracle@any"] - sel["realised@2"]
        print(f"  SELECTION HEADROOM (oracle@any - realised@2): {gap} tasks = {gap/n:.2%}")
        print("  budget   uniform   oracle-alloc")
        for budget in budgets:
            print(
                f"  {budget:6d}   {result['uniform_accuracy_by_budget'][budget]:7d}"
                f"   {result['oracle_allocation_by_budget'][budget]:12d}"
            )
    print(f"\nwrote {out / 'headroom.json'}")


if __name__ == "__main__":
    main()
