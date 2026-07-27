# EXP002-D — EVALUATION_PROTOCOL

Built by `src/analysis/exp002d/folds.py`, seed `20260727`.

## Design

Five outer, task-grouped folds, stratified by `size_relation` family
(computed within each family: shuffle, then round-robin deal into 5
folds). Every test-index belonging to one task is in exactly one outer
fold. Within each outer fold's four-fold training partition, a further
family-stratified 80/20 task-grouped split (seed `20260727 + 1000 + k`,
distinct per outer fold `k`) produces an inner-calibration task set drawn
only from that partition's own tasks.

## Verified programmatically (assertions in `folds.py::build_and_verify`)

- Every pair of outer folds' task sets is disjoint.
- The union of all five outer folds' task sets equals the full 160-task
  set.
- Every outer fold's inner-calibration set is disjoint from that same
  fold's own outer test set (a task in fold `k`'s calibration set is
  never in fold `k` itself).

## Outer fold sizes (160 tasks)

| Fold | Tasks |
| --- | --- |
| 0 | 34 |
| 1 | 33 |
| 2 | 31 |
| 3 | 31 |
| 4 | 31 |

Reasonably balanced given family-stratified round-robin dealing, not a
fixed 32/32/32/32/32 split — expected, since each family's own task count
need not divide evenly by 5.

## Repetition

A single frozen seed is used (no multi-seed repeat) — a preregistered
scope decision (`PLAN.md`), not a result-driven one, given the CPU/time
cost of repeating up to 6 model families x 7 ablations x 3 seeds against
the paired-bootstrap already covering resampling variance.

## Artifact

`artifacts/EXP002D/fold_assignments.json`: `fold_seed`, `n_outer_folds`,
`inner_calibration_fraction`, `outer_fold_of_task` (task_id -> fold
index), `outer_fold_sizes`, `inner_calibration_tasks_by_fold`.
