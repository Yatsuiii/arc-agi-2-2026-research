# GEN002-B — VALIDATION_SAMPLE

Fresh validation manifest: `GEN002B_VALIDATION_V1_TASK_DISJOINT_STRIDE24`
(`artifacts/GEN002B/validation_manifest.json`).

## Composition

- Group A2: 12 CompressARC generation failures.
- Group B2: 6 CompressARC oracle-only successes missed by native top-2.
- Group C2: 6 CompressARC native top-2 successes.

The selected sample contains 24 test-indices from 24 unique task IDs.
Every old pilot task ID was excluded before sampling, so the fresh
validation set is both task-disjoint and index-disjoint from the original
GEN001-A / GEN002-A pilot.

## Deterministic sampling rule

Within each A2/B2/C2 pool:

1. Start from EXP002-D's frozen CompressARC outcome labels.
2. Exclude all 24 old pilot task IDs.
3. Join visible task descriptors from `task_statistics.csv` and the ARC
   training challenges.
4. Sort by:
   `dimension_descriptor`, `n_input_colours`, `component_bucket`,
   `object_structure`, `palette_descriptor`,
   `object_delta_descriptor`, `task_id`, `test_index`.
5. Take an evenly-strided sample with no randomness.

This preserves stratification over dimensions, colour count, component
load, object structure, and coarse transformation descriptors without any
reference to expected GEN002-B performance.

## Overlap checks

- Old pilot tasks: 24
- Selected unique tasks: 24
- Task overlap count: 0
- Index overlap count: 0
- Task-level disjointness: true
- Index-level disjointness: true

## Frozen sample

### Group A2

- `5587a8d0` / test 0
- `c1990cce` / test 0
- `a3f84088` / test 0
- `c62e2108` / test 0
- `5a5a2103` / test 0
- `396d80d7` / test 0
- `46c35fc7` / test 0
- `6ca952ad` / test 0
- `2c737e39` / test 0
- `5daaa586` / test 0
- `5d2a5c43` / test 1
- `a8c38be5` / test 0

### Group B2

- `60b61512` / test 0
- `6df30ad6` / test 0
- `913fb3ed` / test 0
- `642248e4` / test 0
- `88a62173` / test 0
- `c8b7cc0f` / test 0

### Group C2

- `00576224` / test 0
- `1478ab18` / test 0
- `69889d6e` / test 0
- `7ee1c6ea` / test 0
- `ea786f4a` / test 0
- `9ba4a9aa` / test 0
