"""ACQ-001 Phase 1/2 (sharding half): freeze the TRAIN/DEV/TEST folds, draw the
~170-test-index TEST corpus, run the leakage check, and split TEST into two
shards balanced by predicted runtime.

Reuses, rather than re-derives, this project's existing fold machinery:
`src.analysis.exp002_verifier_eval.{FOLD_SEED, assign_folds, load_family_flags}`
(the same stratified-by-family, seeded A/B/C split already used by EXP002/
EXP002-B/EXP002-C's own `sample_tasks.py`) and `src.data_audit.duplicates`
(the same exact/canonical-duplicate detector `src/data_audit/__main__.py`
already runs across Kaggle/GitHub splits).

Deterministic, CPU only, no network. Run once, before any GPU work:

    python -m src.run002c.build_acq001_corpus
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from src.analysis.exp002_verifier_eval import FOLD_SEED, assign_folds, load_family_flags
from src.data_audit import duplicates
from src.data_audit.corpus import Corpus, Pair, Task

ROOT = Path(__file__).resolve().parents[2]
TRAINING_CHALLENGES = ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_challenges.json"
OUTPUT_DIR = ROOT / "artifacts" / "ACQ001"

TEST_TARGET_INDICES = 170
# CompressARC's own per-task wall-clock is empirically constant at the
# 2400s cap (every task in EXP002-C/C2/C3 timed out, none converged early),
# so "predicted runtime" per task is uniform, not a per-task variable --
# see `experiments/ACQ001/SHARDING_PLAN.md` for the full argument. What
# does vary, and what this script balances across shards, is n_test (the
# measured memory/compute-weight outlier axis from every prior pilot:
# `42f83767`, n_test=2, was consistently the slowest task by steps/s).
SLOTS_PER_WAVE = 6  # frozen C3: 3 processes/T4 x 2 T4s


def _load_problems() -> dict:
    return json.loads(TRAINING_CHALLENGES.read_text())


def build_folds() -> dict:
    problems = _load_problems()
    all_ids = sorted(problems)
    flags = load_family_flags(set(all_ids))
    folds = assign_folds(all_ids, flags, seed=FOLD_SEED)
    return {"problems": problems, "all_ids": all_ids, "flags": flags, "folds": folds}


def draw_test_subset(problems: dict, all_ids: list[str], flags: dict, folds: dict[str, str]) -> tuple[list[str], list[str]]:
    """From Fold C (the untouched final-eval 20%), deterministically draw the
    smallest family-stratified task set whose total test-index count reaches
    `TEST_TARGET_INDICES`, keeping whole tasks together (never splitting a
    task's test indices across the drawn/reserved boundary). Returns
    (chosen, reserved)."""
    fold_c = [t for t in all_ids if folds[t] == "C"]
    by_family: dict[str, list[str]] = defaultdict(list)
    for task_id in fold_c:
        family = flags.get(task_id, {}).get("size_relation", "unknown")
        by_family[family].append(task_id)

    rng = random.Random(FOLD_SEED)
    for family in by_family:
        by_family[family] = sorted(by_family[family])
        rng.shuffle(by_family[family])

    families = sorted(by_family)
    cursor = {family: 0 for family in families}
    chosen: list[str] = []
    total_test = 0
    while total_test < TEST_TARGET_INDICES:
        progressed = False
        for family in families:
            if cursor[family] < len(by_family[family]):
                task_id = by_family[family][cursor[family]]
                cursor[family] += 1
                chosen.append(task_id)
                total_test += len(problems[task_id]["test"])
                progressed = True
                if total_test >= TEST_TARGET_INDICES:
                    break
        if not progressed:
            break

    reserved = [t for t in fold_c if t not in set(chosen)]
    return sorted(chosen), sorted(reserved)


def leakage_check(problems: dict, folds: dict[str, str], train_ids: list[str], dev_ids: list[str], test_ids: list[str]) -> dict:
    def to_corpus(name: str, ids: list[str]) -> Corpus:
        tasks = {}
        for task_id in ids:
            problem = problems[task_id]
            tasks[task_id] = Task(
                task_id=task_id,
                train=[Pair(p["input"], p.get("output")) for p in problem["train"]],
                test=[Pair(p["input"], p.get("output")) for p in problem["test"]],
            )
        return Corpus(name=name, source="arc-agi_training_challenges.json", tasks=tasks)

    corpora = [
        to_corpus("TRAIN", train_ids),
        to_corpus("DEV", dev_ids),
        to_corpus("TEST", test_ids),
    ]
    return duplicates.report(corpora)


def build_shards(problems: dict, flags: dict, test_ids: list[str]) -> tuple[list[str], list[str]]:
    """Split TEST into two shards, balanced by task count (the real driver
    of wall-clock at fixed per-task runtime, see module docstring) AND by
    n_test-weighted family mix (the real driver of per-task compute
    variance), via deterministic round-robin: sort tasks by (family,
    n_test, task_id) so the alternation naturally interleaves both axes,
    then alternate assignment to A/B."""
    ordered = sorted(
        test_ids,
        key=lambda t: (flags.get(t, {}).get("size_relation", "unknown"), len(problems[t]["test"]), t),
    )
    shard_a, shard_b = [], []
    for i, task_id in enumerate(ordered):
        (shard_a if i % 2 == 0 else shard_b).append(task_id)
    return sorted(shard_a), sorted(shard_b)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state = build_folds()
    problems, all_ids, flags, folds = state["problems"], state["all_ids"], state["flags"], state["folds"]

    test_ids, reserved_ids = draw_test_subset(problems, all_ids, flags, folds)
    train_ids = [t for t in all_ids if folds[t] == "A"]
    dev_ids = [t for t in all_ids if folds[t] == "B"]
    # Reserved Fold-C tasks are neither TEST (not drawn into the 170-index
    # target) nor TRAIN/DEV (they are Fold C, held out by the family split)
    # -- recorded separately so a future corpus expansion toward 500 draws
    # from this exact reserved pool, not a re-randomised one.

    test_index_count = sum(len(problems[t]["test"]) for t in test_ids)

    folds_payload = {
        "fold_seed": FOLD_SEED,
        "n_total_training_tasks": len(all_ids),
        "train_task_ids": train_ids,
        "dev_task_ids": dev_ids,
        "test_task_ids": test_ids,
        "test_reserved_task_ids": reserved_ids,
        "test_target_indices": TEST_TARGET_INDICES,
        "test_actual_indices": test_index_count,
        "family_stratification": dict(Counter(flags.get(t, {}).get("size_relation", "unknown") for t in test_ids)),
    }
    (OUTPUT_DIR / "folds.json").write_text(json.dumps(folds_payload, indent=2, sort_keys=True) + "\n")

    leak_report = leakage_check(problems, folds, train_ids, dev_ids, test_ids)
    exact_cross = [c for c in leak_report["exact_duplicate_tasks"] if len({m.split(":")[0] for m in c["members"]}) > 1]
    canon_cross = [c for c in leak_report["canonical_duplicate_tasks"] if len({m.split(":")[0] for m in c["members"]}) > 1]
    pair_cross = leak_report["shared_demonstration_pairs_across_splits"]

    shard_a_ids, shard_b_ids = build_shards(problems, flags, test_ids)
    shard_a_indices = sum(len(problems[t]["test"]) for t in shard_a_ids)
    shard_b_indices = sum(len(problems[t]["test"]) for t in shard_b_ids)

    def shard_payload(name: str, ids: list[str]) -> dict:
        n_test_total = sum(len(problems[t]["test"]) for t in ids)
        n_waves = -(-len(ids) // SLOTS_PER_WAVE)  # ceil
        return {
            "shard": name,
            "task_ids": ids,
            "n_tasks": len(ids),
            "n_test_indices": n_test_total,
            "slots_per_wave": SLOTS_PER_WAVE,
            "n_waves": n_waves,
            "predicted_wall_clock_s": n_waves * 2450,  # 2400s task cap + ~50s observed per-wave overhead
        }

    (OUTPUT_DIR / "shard_a.json").write_text(json.dumps(shard_payload("A", shard_a_ids), indent=2, sort_keys=True) + "\n")
    (OUTPUT_DIR / "shard_b.json").write_text(json.dumps(shard_payload("B", shard_b_ids), indent=2, sort_keys=True) + "\n")

    manifest = {
        "acquisition": "ACQ-001",
        "fold_seed": FOLD_SEED,
        "source": str(TRAINING_CHALLENGES),
        "n_train_tasks": len(train_ids),
        "n_dev_tasks": len(dev_ids),
        "n_test_tasks": len(test_ids),
        "n_test_reserved_tasks": len(reserved_ids),
        "n_test_indices": test_index_count,
        "test_target_indices": TEST_TARGET_INDICES,
        "leakage_check": {
            "exact_duplicate_tasks_within_split": len(leak_report["exact_duplicate_tasks"]) - len(exact_cross),
            "exact_duplicate_tasks_cross_split": len(exact_cross),
            "canonical_duplicate_tasks_within_split": len(leak_report["canonical_duplicate_tasks"]) - len(canon_cross),
            "canonical_duplicate_tasks_cross_split": len(canon_cross),
            "shared_demonstration_pairs_cross_split": len(pair_cross),
        },
        "shards": {
            "A": {"n_tasks": len(shard_a_ids), "n_test_indices": shard_a_indices},
            "B": {"n_tasks": len(shard_b_ids), "n_test_indices": shard_b_indices},
        },
    }
    (OUTPUT_DIR / "corpus_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (OUTPUT_DIR / "duplicate_report.json").write_text(json.dumps(leak_report, indent=2, sort_keys=True) + "\n")

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
