"""Pick a family-stratified sample of ARC-AGI-2 training tasks for EXP002-C.

Training tasks are structurally leakage-free with respect to RUN-001/EXP002's
120-task evaluation-split corpus by construction (ARC-AGI-2 ships training and
evaluation as disjoint task sets), so the only fold-assignment discipline this
needs is the same one `exp002_verifier_eval.assign_folds` already applies:
stratify by `size_relation` so no family is missing from any fold, seed the
split so it is reproducible and cannot be tuned after seeing results.

Reuses `paper/EXPERIMENT_REGISTRY.md` H0-tested code
(`src/analysis/exp002_verifier_eval.load_family_flags`,
`.assign_folds`) rather than re-deriving fold logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.exp002_verifier_eval import FOLD_SEED, assign_folds, load_family_flags

ROOT = Path(__file__).resolve().parents[2]
TRAINING_CHALLENGES = (
    ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_challenges.json"
)


def training_task_ids() -> list[str]:
    problems = json.loads(TRAINING_CHALLENGES.read_text())
    return sorted(problems)


def sample(n_tasks: int, seed: int = FOLD_SEED) -> dict:
    """Deterministic family-stratified sample plus its own train/cal/eval fold split.

    Returns `{"task_ids": [...], "folds": {task_id: "A"|"B"|"C"}}`. `n_tasks`
    should be picked to satisfy `experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s
    minimum test-index target once each task's test-index count is known
    (checked separately, not assumed 1:1 with task count).
    """
    all_ids = training_task_ids()
    flags = load_family_flags(set(all_ids))
    folds = assign_folds(all_ids, flags, seed=seed)

    by_family: dict[str, list[str]] = {}
    for task_id in all_ids:
        family = flags.get(task_id, {}).get("size_relation", "unknown")
        by_family.setdefault(family, []).append(task_id)

    target_per_family = max(1, n_tasks // max(1, len(by_family)))
    chosen: list[str] = []
    for family, ids in sorted(by_family.items()):
        chosen.extend(sorted(ids)[:target_per_family])
    chosen = sorted(chosen)[:n_tasks]

    return {
        "n_tasks": len(chosen),
        "fold_seed": seed,
        "task_ids": chosen,
        "folds": {task_id: folds[task_id] for task_id in chosen},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-tasks", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = sample(args.n_tasks)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}: {result['n_tasks']} tasks")


if __name__ == "__main__":
    main()
