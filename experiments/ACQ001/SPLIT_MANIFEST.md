# ACQ-001 — SPLIT_MANIFEST

Phase 1: freezes the TRAIN/DEV/TEST folds and the ~170-test-index TEST
corpus before any generation. Produced by
`src/run002c/build_acq001_corpus.py` (deterministic, CPU-only, no network).
Raw output: `artifacts/ACQ001/{corpus_manifest,folds,duplicate_report}.json`.

## Referenced-but-missing files (same discipline as prior EXP002-C passes)

The acceptance message referenced `experiments/EXP002C/SPLIT_PROTOCOL.md`
and `experiments/EXP002C/CORPUS_REQUIREMENTS.md`. Neither exists —
confirmed by directory listing before writing this document.
`CORPUS_REQUIREMENTS.md` exists under `experiments/EXP002B/`, not
`EXP002C/`, and supplies the 170-500 test-index McNemar-based target this
document implements the 170 floor of. No split protocol document existed
anywhere in the repository before this one; §1-4 below **is** the split
protocol, written for the first time here rather than assumed to exist.

## 1. Source and eligibility

Source: `competition_2026/extracted/arc-agi_training_challenges.json`
(1000 tasks total — the full ARC-AGI-2 training pool, structurally disjoint
from the 120-task evaluation split RUN-001/EXP002/EXP002-B already used,
per `src/run002c/sample_tasks.py`'s own docstring). Every training task is
eligible; no task is excluded before fold assignment (unlike RUN-001's
evaluation-split corpus, the training split carries no known contamination
concern for this project's own solvers, since CompressARC has no
pretraining phase to contaminate).

## 2. Fold assignment (TRAIN / DEV / TEST)

Reused unchanged: `src.analysis.exp002_verifier_eval.assign_folds` with
`FOLD_SEED = 20260725` — the same seeded, family-stratified (by
`size_relation`) 60/20/20 round-robin split already used for EXP002's own
fold assignment and `sample_tasks.py`'s pilot sampling. No new fold logic
was written; this is the single existing implementation, reused for
consistency with the rest of the project's fold-seed discipline.

| Fold | Role | Task count | Total test-indices |
| --- | --- | --- | --- |
| A | TRAIN | 602 | 654 |
| B | DEV | 199 | 210 |
| C | (source pool for TEST, see §3) | 199 | 212 |

## 3. The ~170-index TEST corpus

Fold C (199 tasks, 212 test-indices) is larger than the 170-test-index
target `experiments/EXP002C2/SCALING_PROJECTION.md` and
`experiments/EXP002C3/SCALING_PROJECTION.md` establish as the pre-registered
McNemar floor. Per this document's own new split protocol: **TEST is a
deterministic, family-stratified subset of Fold C**, drawn by iterating
each family (`size_relation` stratum) in a fixed, seeded shuffle order,
round-robin across families, accumulating test-indices until the 170
target is reached (never splitting a task's test-indices across the
drawn/reserved boundary — "keep complete tasks together," per the
acceptance message).

**Result: 160 tasks, 171 test-indices** (one task over target since whole
tasks are kept intact; unavoidable without ever undershooting).

| Family (`size_relation`) | TEST task count |
| --- | --- |
| same | 97 |
| smaller | 45 |
| larger | 16 |
| inconsistent | 2 |

The remaining 39 Fold-C tasks (41 test-indices) are **reserved, not
discarded** — recorded in `folds.json`'s `test_reserved_task_ids`, the
exact pool a future corpus expansion toward the 500-test-index conservative
target should draw from next, using the same seeded procedure, rather than
re-randomising.

## 4. Leakage controls

`duplicates.report` (`src/data_audit/duplicates.py`, the same tool
`src/data_audit/__main__.py` already runs across Kaggle/GitHub splits) run
across three named corpora built from this split (TRAIN=Fold A, DEV=Fold
B, TEST=the 160-task subset above):

| Check | Cross-split hits |
| --- | --- |
| Exact duplicate tasks (identical demonstration pairs) | **0** |
| Canonical duplicate tasks (identical under the D4 dihedral group + colour relabelling — the augmentation group every reference solver trains on) | **0** |
| Shared individual demonstration pairs across splits | **0** |

No leakage detected by any of the three notions this tool checks. Full
raw report: `artifacts/ACQ001/duplicate_report.json`.

## 5. What was not inspected

Per the acceptance message's explicit instruction ("do not inspect held-out
correctness before generation completes"), **no test-index's ground-truth
output was read or compared during fold construction** — `assign_folds`
stratifies on `size_relation` (a property of grid *shapes*, computed from
`docs/DATASET_AUDIT.md`'s existing `task_statistics.csv`, itself derived
from input/output shapes, not correctness), and the TEST-subset draw uses
only task IDs and test-index counts, never solution grids. No public
ARC-AGI-2 evaluation-split answers were used (this corpus is drawn entirely
from the training split). No Kaggle placeholder test tasks were used
(source is `arc-agi_training_challenges.json`, not the competition's
`arc-agi_test_challenges.json`).

## 6. Frozen record

`artifacts/ACQ001/folds.json` records `fold_seed`, every task ID in every
fold (TRAIN/DEV/TEST/reserved), and the family stratification —
sufficient to reconstruct this exact split from the same source file and
seed, byte-for-byte, without rerunning any nondeterministic step (there is
none; `build_acq001_corpus.py` is fully deterministic).
