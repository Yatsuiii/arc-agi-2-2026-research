# GEN002-B — VALIDATION_PROTOCOL

## Validation objective

Run one frozen GEN002-B configuration exactly once on a new 24-index
ACQ-001 pilot and measure whether it emits complementary candidates over
CompressARC.

## Pilot composition

- Group A2: 12 CompressARC generation failures.
- Group B2: 6 CompressARC oracle-only successes missed by native top-2.
- Group C2: 6 CompressARC native top-2 successes.

The manifest must not overlap the original GEN001-A / GEN002-A pilot at
the `(task_id, test_index)` level, and task-level disjointness is
preferred where feasible.

## Generation rules

- CPU only.
- Deterministic seeds.
- Incremental persistence and resume support.
- Initial budget target: up to 20 CPU-minutes per task with strict memory
  guards.
- Candidate emission requires exact fit on all visible demonstrations.
- Hidden outputs are unavailable to the generator.

## Required artifacts

- `artifacts/GEN002B/candidates.jsonl.gz`
- `artifacts/GEN002B/task_summary.csv`
- `artifacts/GEN002B/runtime_summary.json`
- `artifacts/GEN002B/errors.jsonl`
- `artifacts/GEN002B/run_manifest.json`
- `artifacts/GEN002B/completed_indices.json`

## Offline analysis rules

Correctness is checked only after generation completes for the whole
manifest. The offline pass reports:

- emitted-candidate coverage;
- exact demonstration-consistent program count;
- Group-A2 / B2 / C2 outcomes;
- GEN002-B oracle and CompressARC union oracle;
- incremental solved indices;
- missing-language, search-failure, generalization-failure, and
  representation-failure counts;
- runtime and peak RAM.

## Decision rule

Exactly one verdict is allowed:

- `ADOPT SYMBOLIC GENERATOR`
- `SCALE SYMBOLIC GENERATOR`
- `EXPAND LANGUAGE ONCE MORE`
- `IMPROVE SEARCH`
- `FREEZE SYMBOLIC RESEARCH`
