# GEN001-A — PILOT_SAMPLE

The frozen 24-test-index pilot sample, drawn by
`src/gen001/build_pilot_manifest.py` before any NVARC prediction exists.
Manifest: `artifacts/GEN001A/pilot_manifest.json`.

## Selection rule (deterministic, no randomness)

Three pools, each already fixed by EXP002-D's frozen, ground-truth-derived
outcome labels (`artifacts/EXP002D/error_taxonomy.csv`) — not by anything
this phase computes fresh:

- Group A pool = test-indices with `oracle_hit=False` (129 candidates).
- Group B pool = test-indices with `oracle_hit=True, native_top2_hit=False`
  (19 candidates).
- Group C pool = test-indices with `native_top2_hit=True` (23 candidates).

Within each pool, rows are sorted by `(size_relation, large_grid,
n_input_colours, task_id, test_index)` — structural descriptors from
`artifacts/data_audit/task_statistics.csv`, joined in — then an evenly
strided sample of the group's target size is taken. Striding a sorted list
spans the distribution of structural properties (grid-size relation, large
vs. normal grid, colour count) without reference to any NVARC-specific
property, satisfying the "not chosen based on expected NVARC success"
requirement mechanically rather than by intent alone.

All 24 selected test-indices happen to come from 24 distinct tasks (no task
in this corpus has more than one test-index landing in the sample), so the
"keep all test-indices from one task together" rule is satisfied trivially.

## Group A — 12 CompressARC generation failures

| task_id | test_index | size_relation | large_grid | n_input_colours |
| --- | --- | --- | --- | --- |
| d631b094 | 0 | inconsistent | False | see manifest |
| 310f3251 | 0 | larger | False | see manifest |
| ce039d91 | 0 | same | False | see manifest |
| 41ace6b5 | 0 | same | False | see manifest |
| 1b59e163 | 0 | same | False | see manifest |
| 94be5b80 | 0 | same | False | see manifest |
| 3490cc26 | 0 | same | True | see manifest |
| db615bd4 | 0 | same | True | see manifest |
| 72322fa7 | 0 | same | True | see manifest |
| 25c199f5 | 1 | smaller | False | see manifest |
| 12997ef3 | 1 | smaller | False | see manifest |
| 2c0b0aff | 0 | smaller | True | see manifest |

Spans all five `size_relation` families present in the pool (`inconsistent`,
`larger`, `same`, `smaller`) and both `large_grid` values — the group this
pilot's central question is actually about.

## Group B — 6 CompressARC oracle successes, selection failures

| task_id | test_index | size_relation |
| --- | --- | --- |
| c9e6f938 | 0 | larger |
| 4a1cacc2 | 0 | same |
| 36fdfd69 | 0 | same |
| 0d3d703e | 0 | same |
| e133d23d | 0 | smaller |
| a68b268e | 0 | smaller |

Used to check whether NVARC's candidates land in the same selection blind
spot CompressARC's own selector already misses, which would indicate a
shared, not independent, weakness.

## Group C — 6 CompressARC native successes

| task_id | test_index | size_relation |
| --- | --- | --- |
| 53b68214 | 1 | larger |
| 6f8cd79b | 0 | same |
| e0fb7511 | 0 | same |
| 05269061 | 0 | same |
| 29700607 | 0 | same |
| d9fac9be | 0 | smaller |

Used to measure regression risk, redundancy, and candidate overlap on
test-indices that already work.

## Full per-row detail

`compressarc_oracle_hit`, `compressarc_native_top2_hit`, `n_input_colours`,
`objects_input_mean` for every row are in
`artifacts/GEN001A/pilot_manifest.json`, not duplicated here to avoid a
second source of truth that could drift from the generating script's
output.
