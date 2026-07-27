# ACQ-001 — SHARD_A_RESULTS

Kaggle kernel `redlotusthepotus/acq001-shard-a`, version 1. Launched under
the frozen C3 configuration (`BASELINE_SPEC.md`), Shard A only (80 tasks,
85 test-indices, per `artifacts/ACQ001/shard_a.json`).

## Run outcome

**COMPLETE.** 14 waves (13 of 6 tasks + 1 of 2 tasks, matching
`SHARDING_PLAN.md`'s prediction exactly), wall-clock **33,899.85s (9.417h)**
against a prediction of 34,300s (9.53h) — 98.8% of predicted, no abort, no
stall, no RAM exhaustion.

| Metric | Value |
| --- | --- |
| Tasks attempted | 80 / 80 |
| Tasks completed | 80 / 80 |
| Tasks failed | 0 |
| Tasks timed out (expected outcome, not a failure) | 80 / 80 (`hit_time_guard=1`, matches every prior pilot — CompressARC never converges early under this timeout) |
| Retry attempts used | 0 (all `attempts=1`) |
| Device split | cuda:0: 41 tasks, cuda:1: 39 tasks |
| Per-task wall-clock | 2410.1-2425.1s (matches the 2410-2425s range measured on task `00576224` across every prior EXP002-C/C2/C3 pilot) |

## Archive integrity

- `candidates.A.jsonl.gz`: gzip fully readable, **36,378 records** — exactly
  matches `runtime_summary.A.json`'s `records_total`.
- Record composition: 36,208 `candidate` records + 170 `selection` records
  (2 per test-index x 85 test-indices, exact).
- `checkpoint_state.json`: 80 entries, all `status=complete`, no duplicates.
- `completed_tasks.json`: 80 entries, all unique.
- `errors.A.jsonl`: absent — correct (lazy-created only on first
  `record_error` call; 0 failures recorded, matching `n_failed=0`).
- Test-index coverage reconciled against the real `arc-agi_training_
  challenges.json` structure (task/test-count fields only, no answers
  read): every one of the 80 tasks' expected test-index set is present
  exactly once in the archive. **Zero missing, zero duplicated records.**
- Checksums: `artifacts/ACQ001/shard_a_checksums.sha256` (also see
  `ARTIFACT_MANIFEST.tsv`).

## Provenance

`run_manifest.A.json` confirms: `concurrency="C3 frozen: 3 processes/T4"`,
`n_iterations=2000`, `time_limit_s=2400`, `solver="CompressARC (vendored +
grid-persistence instrumentation)"`, and the exact 80-task-ID list matching
`artifacts/ACQ001/shard_a.json`. No parameter drift from the frozen
baseline.

## Candidate volume and diversity

Keyed by `(task_id, test_index)`, 85 keys total:

| Metric | Value |
| --- | --- |
| Total candidates | 36,208 |
| Total unique grids (by `grid_sha1`, summed per key) | 35,270 |
| Unique-candidate fraction | 97.41% |
| Candidates per test-index | mean 426.0 (min 7, max 1434) |
| Unique grids per test-index | mean 414.9 |

97.41% uniqueness clears the 90% diversity floor used as a quality gate in
EXP002-C2.

## Candidate-oracle coverage (separate offline analysis)

Computed by `src/analysis/acq001_oracle.py`, a standalone script
run only after generation completed, using legal ground truth
(`arc-agi_training_solutions.json` — training split, never the public
evaluation split, never a Kaggle placeholder). This script was not run
during, and does not feed back into, generation.

| Metric | Value |
| --- | --- |
| Oracle coverage (any candidate in the full archive matches ground truth) | 23 / 85 = **27.06%** |
| Top-2 selection accuracy (CompressARC's own `attempt_1`/`attempt_2`, the `selection` records) | 13 / 85 = **15.29%** |

The 27.06% vs. 15.29% gap (11.8pp, 10 test-indices where a correct grid
exists somewhere in the beam but was not chosen by CompressARC's built-in
top-2 selection) is the kind of recoverable-selection headroom claim C2
(`paper/CLAIM_LEDGER.md`) needs evidence for — this run alone is far too
small a sample to resolve that claim, but it is consistent with the RUN-001
preview finding (30 generated vs. 23 selected, 7.4pp) in the same
direction. No verifier tuning or further analysis was performed on this
result, per the explicit prohibition on tuning after viewing held-out
correctness.

## Compute

Wall-clock 9.417h on a 2xT4 kernel = **18.83 Kaggle-quota GPU-hours**
(wall-clock x 2 GPUs), for 85 test-indices. Revised full-corpus cost: the
170-test-index target needs Shard A + Shard B combined; Shard B's own
predicted wall-clock (9.53h, `SHARDING_PLAN.md`) was built with the same
balancing procedure and is expected to land within a few percent of Shard
A's actual. Projected total: **~19h wall-clock / ~38 GPU-hours** for the
full 170-test-index corpus — matching the pre-registered ~38 GPU-hour
estimate (`experiments/EXP002C3/CORPUS_ACQUISITION_DECISION.md`) almost
exactly; Shard A's actual cost does not revise that figure materially.

## Shard B success gate (evaluation only — not a launch decision)

| Criterion | Result |
| --- | --- |
| Zero archive corruption | **PASS** — gzip fully readable, record count reconciles exactly |
| No systematic orchestration failures | **PASS** — 0 failed tasks, 0 retries needed, all 14 waves completed cleanly |
| >=90% expected unique-candidate production | **PASS** — 97.41% |
| Acceptable timeout and retry rate | **PASS** — 100% time-guard hits is the expected, designed-for outcome under this baseline (`BASELINE_SPEC.md`), not an anomaly; 0 retries were needed |
| Valid provenance | **PASS** — `run_manifest.A.json` matches the frozen configuration and the exact frozen task list |
| Projected total cost compatible with recorded budget | **PASS** — ~38 GPU-hours projected for the full corpus, matching the pre-registered estimate |
| Enough multi-candidate examples for verifier research | **PASS** — mean 426 candidates/test-index, 97.4% unique, with a measured oracle/top-2 gap |

**All seven criteria pass. Shard B is recommended for launch** under the
same frozen configuration, in a separate task, per the explicit instruction
that this task stops after Shard A validation.
