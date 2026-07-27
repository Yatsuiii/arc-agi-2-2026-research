# GEN001-A — BASELINE_SPEC

Frozen inputs and reference numbers this phase measures against. Nothing
here is computed by this phase; every number is restated from an existing,
already-validated artifact.

## Corpus (immutable, read-only in this phase)

| Field | Value | Source |
| --- | --- | --- |
| Tasks | 160 | `artifacts/ACQ001/merged_corpus_manifest.json` |
| Test-indices | 171 | same |
| Candidate records (raw archive rows, `kind=candidate`) | 73,147 | same |
| Unique candidates (by `grid_sha1` within `(task_id, test_index)`) | 70,680 (96.63%) | same |
| CompressARC candidate oracle | 24.56% (42/171) | same |
| CompressARC native top-1 | 11.70% | `experiments/EXP002D/RESULTS.md` |
| CompressARC native top-2 | 13.45% | same |
| Generation-failure test-indices (no correct candidate at all) | 129/171 (75.44%) | `experiments/EXP002D/ERROR_ANALYSIS.md` |
| Selection-failure test-indices (correct candidate present, not selected) | 17/171 | same |
| Archive files | `artifacts/ACQ001/shard_a_output/acq001_a/archive/candidates.A.jsonl.gz`, `artifacts/ACQ001/shard_b_output/acq001_b/archive/candidates.B.jsonl.gz` | — |
| Archive checksums | `sha256:580c764f...`, `sha256:499e8428...` | `artifacts/ACQ001/merged_corpus_manifest.json` |

## Archive schema (what a new generator must match)

`src/run001/archive.py::CandidateArchive` is the schema ACQ-001's own
acquisition (`src/run002c/acquire_shard.py`) reuses without modification.
GEN001-A's adapter (Phase 6) reuses this exact class, not a reimplementation,
so join keys (`task_id, test_index, grid_sha1`) and record kinds
(`candidate`, `selection`) are identical across CompressARC and NVARC output
by construction.

## What "beating the baseline" means in this phase

This phase does not evaluate NVARC's selection accuracy against
CompressARC's. The comparison that matters (Phase 4 of `PLAN.md`) is set
complementarity: does NVARC's candidate set contain a correct grid on any of
the 129 test-indices where CompressARC's candidate set contains none. The
129-test-index generation-failure set, frozen above, is the denominator for
that question and is not recomputed in this phase — it is inherited
verbatim from EXP002-D's already-validated error taxonomy
(`artifacts/EXP002D/error_taxonomy.csv`).

## RUN-001 reference numbers (contaminated, restated for pilot projection only)

| Field | Value | Source |
| --- | --- | --- |
| Tasks reached (120-task eval split, 11h43m budget, 2xT4) | 77/120 | `experiments/RUN001/RESULTS.md` |
| Candidate-bearing tasks | 72/120 | same |
| Accuracy on candidate-bearing tasks | 23.4% | same |
| Per-task time guard | 1200s | `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §10-11 |
| Per-DFS-batch time guard | 540s | same |
| Global session budget | 11h40m (12h - 1200s) | same |

These numbers describe RUN-001's run over the ARC-AGI-2 **evaluation** split
(120 tasks), which is a different, and separately contaminated, split from
ACQ-001's 160-task **training**-split corpus (`experiments/GEN001A/CONTAMINATION_AUDIT.md`).
They are used here only as a runtime/throughput reference for Phase 8's
quota projection, never as an accuracy claim transferable to ACQ-001's
corpus.
