# DATA001-A — BASELINE_SPEC

## Frozen predecessors

The relevant predecessor state on July 27, 2026 is:

- GEN001-A: frozen NVARC pilot branch, untouched in this phase.
- GEN002-A: frozen symbolic null result on the original 24-index pilot.
- GEN002-B: frozen symbolic null result on a fresh 24-index pilot.

The completed GEN002-B result is:

- branch `gen002b-dsl-redesign`;
- commit `6eea7016de157d7426e4896bbb999df1bd8bfc1d3`;
- 0/24 validation indices emitted candidates;
- 0 exact programs;
- 0/12 Group-A2 rescues;
- 22 `missing_language` failures;
- 2 `search_failure` failures;
- TRAIN/DEV exact-program coverage `2/75 = 2.67%`;
- CompressARC union unchanged;
- verdict `FREEZE SYMBOLIC RESEARCH`.

## Why DATA001-A exists

The symbolic branch is frozen because the bottleneck is not a narrow
search-budget issue. The typed DSL and search redesign still failed to
reach useful expressivity or coverage. DATA001-A therefore shifts the
clean research program toward learned candidate generation with synthetic
provenance and without relying on contaminated competition systems for
paper evidence.

## What stays fixed

- CompressARC remains the frozen comparison baseline.
- ACQ-001 held-out tasks remain read-only evaluation references.
- No Kaggle jobs or GPU quota are consumed during DATA001-A.
- NVARC remains excluded from clean evidence, though it may later remain
  a competition-only control.

## Primary output of DATA001-A

The primary output is not a model result. It is:

- a clean synthetic corpus pilot;
- leakage controls;
- coverage analysis;
- deterministic target serialization;
- a reusable local training and evaluation harness;
- a tightly scoped later model-pilot specification.
