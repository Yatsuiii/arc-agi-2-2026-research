# ACQ-001 — SHARD_B_RESULTS

Kaggle kernel `redlotusthepotus/acq001-shard-b`, version 1. Launched under
the exact frozen C3 configuration used for Shard A (`BASELINE_SPEC.md`),
Shard B only (80 tasks, 86 test-indices, per
`artifacts/ACQ001/shard_b.json`). Before launch, every embedded module in
the Shard B notebook was diffed byte-for-byte against the code that
actually executed in Shard A (`artifacts/ACQ001/shard_a_output/*.py`) —
all matched, including the archive-ingest import fix. No further
validation kernel was run before this launch, per the explicit quota
constraint (~12 GPU-quota hours remaining, Shard A having used ~9.42h).

## Run outcome

**COMPLETE.** 14 waves (13 of 6 tasks + 1 of 2 tasks, matching
`SHARDING_PLAN.md`'s prediction exactly), wall-clock **33,901.05s
(9.417h)** — within 2s of Shard A's own wall-clock, no abort, no stall, no
RAM exhaustion.

| Metric | Value |
| --- | --- |
| Tasks attempted | 80 / 80 |
| Tasks completed | 80 / 80 |
| Tasks failed | 0 |
| Tasks timed out (expected outcome, not a failure) | 80 / 80 (`hit_time_guard=1`) |
| Retry attempts used | 0 (all `attempts=1`) |
| Device split | cuda:0: 41 tasks, cuda:1: 39 tasks |
| Per-task wall-clock | 2410.1-2425.2s |

## Archive integrity

- `candidates.B.jsonl.gz`: gzip fully readable, **37,111 records** —
  exactly matches `runtime_summary.B.json`'s `records_total`.
- Record composition: 36,939 `candidate` records + 172 `selection`
  records (2 per test-index x 86 test-indices, exact).
- `checkpoint_state.json`: 80 entries, all `status=complete`, no
  duplicates. `completed_tasks.json`: 80 unique entries.
- `errors.B.jsonl`: absent — correct (0 failures recorded).
- Test-index coverage reconciled against the real `arc-agi_training_
  challenges.json` structure (task/test-count fields only, no answers
  read): all 80 tasks' expected test-index sets present exactly once.
  **Zero missing, zero duplicated records.**
- `run_manifest.B.json`'s `task_ids` list matches
  `artifacts/ACQ001/shard_b.json` exactly — no parameter or membership
  drift from the frozen shard.
- Checksums: `artifacts/ACQ001/shard_b_checksums.sha256`.

## Provenance

`run_manifest.B.json` confirms: `concurrency="C3 frozen: 3 processes/T4"`,
`n_iterations=2000`, `time_limit_s=2400`, same vendored CompressARC
solver as Shard A.

## Candidate volume and diversity

Keyed by `(task_id, test_index)`, 86 keys total:

| Metric | Value |
| --- | --- |
| Total candidates | 36,939 |
| Total unique grids (by `grid_sha1`, summed per key) | 35,410 |
| Unique-candidate fraction | 95.86% |
| Candidates per test-index | mean 429.5 |
| Unique grids per test-index | mean 411.7 |

95.86% clears the 90% diversity floor (Shard A: 97.41%).

## Candidate-oracle coverage (separate offline analysis)

Computed by `src/analysis/acq001_oracle.py` (renamed from
`acq001_oracle_shard_a.py` now that it is used for both shards — the
script itself was already archive-path-parameterized and needed no logic
change), run only after generation completed, using the same legal
training-split ground truth as Shard A.

| Metric | Value |
| --- | --- |
| Oracle coverage (any candidate matches ground truth) | 19 / 86 = **22.09%** |
| Top-2 selection accuracy (CompressARC's own `attempt_1`/`attempt_2`) | 10 / 86 = **11.63%** |

Shard A measured 27.06%; Shard B measures 22.09% — both in the same
range, consistent with sampling variance across a family-stratified but
otherwise task-diverse shard split, not a systematic difference in
generation quality between shards (both ran the identical frozen
configuration).

## Compute

Wall-clock 9.417h on a 2xT4 kernel = **18.83 Kaggle-quota GPU-hours**, for
86 test-indices — matching Shard A's cost almost exactly.

See `experiments/ACQ001/FINAL_CORPUS_REPORT.md` for the combined
170(171)-index corpus totals.
