# ACQ-001 — SHARDING_PLAN

Phase 2 (sharding half): splits the 160-task, 171-test-index TEST corpus
into two shards balanced by predicted runtime, per the acceptance
message's instruction. Produced by the same
`src/run002c/build_acq001_corpus.py` run that froze the corpus (§3-4
below). Raw output: `artifacts/ACQ001/shard_{a,b}.json`.

## Why "predicted runtime" reduces to "task count" for this workload

`experiments/EXP002C/PILOT_RESULTS.md`, `experiments/EXP002C2/RESULTS.md`,
and `experiments/EXP002C3/RESULTS.md` together cover 20 CompressARC
task-processes across three separate pilots. **Every single one hit its
2400s time-limit cap; none converged early.** CompressARC's per-task
wall-clock is therefore empirically constant (2400s + ~10-25s process
overhead) regardless of task content, at least across every task this
project has ever run it against. This means "predicted runtime per task"
is not a per-task variable to balance — it is a constant — and the actual
lever that determines shard wall-clock is **how many sequential waves of
`SLOTS_PER_WAVE` (= 6, frozen C3: 3 processes/T4 x 2 T4s) a shard
requires**, i.e. `ceil(n_tasks / 6)`.

What genuinely varies between tasks is **compute weight within a wave**
(steps completed, memory footprint) — `42f83767` (n_test=2) was the
slowest task by steps/s in every one of the three prior pilots, and the
largest peak-memory task in EXP002-C's own measurement. This plan balances
shards on that axis too, not just task count, per the acceptance message's
"not merely task count" instruction.

## Balancing procedure

Deterministic (no randomisation at this stage — the TEST-subset draw in
`SPLIT_MANIFEST.md` §3 already used the one seeded step): sort the 160
TEST tasks by `(size_relation family, n_test, task_id)`, then alternate
assignment to Shard A / Shard B. This interleaves both the family
stratification (so neither shard is family-skewed) and the n_test axis
(so neither shard accumulates a disproportionate share of the
higher-memory, slower-per-step n_test=2 tasks) in a single deterministic
pass.

## Result

| Shard | Tasks | Test-indices | Waves (ceil(tasks/6)) | Predicted wall-clock |
| --- | --- | --- | --- | --- |
| A | 80 | 85 | 14 | 34,300s (9.53h) |
| B | 80 | 86 | 14 | 34,300s (9.53h) |

Both shards fit inside a single 12-hour Kaggle competition-runtime session
with **~2.47 hours of margin** — enough to absorb the per-task wall-clock
variance already observed (individual tasks have occasionally run
slightly past 2400s, e.g. 2425-2450s including process teardown) without
risking the session's own hard cap. Predicted wall-clock uses 2450s/task
(the 2400s cap plus ~50s observed per-wave launch/teardown overhead, a
conservative round-up from the ~15-25s actually measured in
`experiments/EXP002C2/RESULTS.md` and `experiments/EXP002C3/RESULTS.md`).

## Complete-tasks-together guarantee

Every shard boundary falls on a task boundary by construction (`build_
acq001_corpus.py` operates on whole `task_ids`, never splits a task's
test-indices across shards). Shard membership is frozen the moment
`shard_a.json`/`shard_b.json` are written, before any candidate is
generated — per the acceptance message's "do not change shard membership
after observing correctness," this is mechanically enforced by *when* the
files are written (before Phase 3 validation even runs), not merely a
promise.

## What Shard B contains, for the record (not launched by this task)

Shard B's 80 tasks and predicted 9.53h runtime are recorded now so a
future, separately approved launch reuses this exact frozen split rather
than re-deriving it. Per the acceptance message's explicit execution
limits, **Shard B is not launched by this task** regardless of Shard A's
outcome — that decision is deferred to the Shard-B success gate
(`experiments/ACQ001/VALIDATION_GATE.md` and `SHARD_A_RESULTS.md`'s own
recommendation section).
