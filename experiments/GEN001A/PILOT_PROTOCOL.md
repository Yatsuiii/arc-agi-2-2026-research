# GEN001-A — PILOT_PROTOCOL

The procedure the eventual (not-yet-launched) 24-index Kaggle pilot follows,
frozen before the pilot manifest or kernel package exists.

## Sample construction (Phase 5)

A deterministic 24-test-index sample drawn from ACQ-001's 171-index corpus,
three groups:

- **Group A (12): CompressARC generation failures.** No correct CompressARC
  candidate exists (`experiments/EXP002D/error_taxonomy.csv`, category
  `generation_failure`). Selected by a deterministic stratified rule over
  task structural descriptors (grid size, colour count, object count,
  `size_relation` family — `artifacts/data_audit/task_statistics.csv`), not
  by any expectation of NVARC success. This is the group the central
  question (`PLAN.md`) is actually about.
- **Group B (6): CompressARC oracle successes, selection failures.** A
  correct CompressARC candidate exists but native top-2 missed it. Used to
  check whether NVARC's candidates land in the same place selection already
  fails on, which would be diagnostic of a shared blind spot rather than
  independent value.
- **Group C (6): CompressARC native successes.** Native top-2 already
  succeeds. Used to measure regression risk, redundancy, and candidate-grid
  overlap — a generator that is complementary on failures but corrupts
  successes is not a net win.

All test-indices from the same task stay together in the sample where a
task has more than one selected test-index, so the pilot never needs to run
a task partially.

## Generation (Phase 6)

Exactly one frozen NVARC configuration, restored from the RUN-001 lineage
unless it cannot operate on ACQ-001's clean corpus (documented deviation if
so). No checkpoint comparison, no base-model bake-off, no tuning on the 24
pilot indices, no restoring multiple NVARC branches. Candidate export uses
`src/run001/archive.py::CandidateArchive` directly — the same class ACQ-001
used — so every candidate record carries `task_id`, `test_index`, `grid`,
`grid_sha1`, `beam_score`, augmentation scores, generation order, plus
GEN001-A-specific provenance fields (`checkpoint_id`, `config_hash`,
`contamination_status`) that CompressARC's records did not need.

## Validation before launch (Phase 7-8)

Every stage that does not require GPU inference is exercised with real code
against real data (task loading, serialization, augmentation construction,
output parsing, archive writing/resume, union-metric computation). GPU
inference itself is exercised with a mocked generator whose output is
schema-valid but explicitly and unmistakably labelled as synthetic
(`checkpoint_id="MOCK"`), so a CI run or a local dry run can never be
mistaken for a real pilot result.

## Launch gate (Phase 8-9)

The pilot is built and packaged but **not launched** by this phase. Launch
requires a separate, explicit, human-confirmed action after manually
checking remaining Kaggle GPU quota against the condition in
`experiments/GEN001A/QUOTA_PROJECTION.md`. No code in this phase calls
`kaggle kernels push` or otherwise starts a Kaggle job.

## Analysis (Phase 11, run only after a future launch)

`src/gen001/analyse_union.py` is written now, against synthetic fixtures,
so the analysis a real pilot's output would receive is fixed before that
output exists — the same discipline `EXP002D`'s preregistration applied to
its verifier evaluation. It computes the oracle-union metrics defined in
`PLAN.md` Phase 4 and nothing else; no verifier is fit in this pass.
