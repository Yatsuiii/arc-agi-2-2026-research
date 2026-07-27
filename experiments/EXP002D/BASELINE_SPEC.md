# EXP002-D — BASELINE_SPEC

## Corpus (frozen, immutable, produced by ACQ-001)

- `artifacts/ACQ001/shard_a_output/acq001_a/archive/candidates.A.jsonl.gz`
- `artifacts/ACQ001/shard_b_output/acq001_b/archive/candidates.B.jsonl.gz`
- Per-task raw JSON (`per_task/*.json`) for the `candidates` list's
  discovery order and task-level solve telemetry not carried into the
  flushed archive (`steps_run`, `elapsed_s`, `timed_out`, `device`).
- Ground truth: `/home/Yatsuiii/arc-agi-2-2026/competition_2026/extracted/
  arc-agi_training_solutions.json` (training split only, legal, never the
  public evaluation split) — read only after the candidate table and
  feature vectors are built, exactly as ACQ-001's own offline oracle
  analysis did.
- Demonstration pairs: `arc-agi_training_challenges.json`'s `"train"`
  field per task — legal to read at any time, this is the visible
  training signal a solver is allowed to condition on, not the held-out
  answer.

**None of these files are modified by EXP002-D.** All EXP002-D artifacts
are new files under `artifacts/EXP002D/` / `experiments/EXP002D/`.

## Frozen native baseline (V0)

The archive's own `selection` records (`kind="selection"`,
`algorithm="compressarc_top2"`, `rank` 1 or 2, `selected=true`). This is
CompressARC's built-in top-2 selection, unchanged, unmodified, replayed
exactly as archived. Measured native top-2 accuracy over the full 171-index
corpus: **13.45%** (23/171), matching
`experiments/ACQ001/FINAL_CORPUS_REPORT.md`.

## What is explicitly not re-run

Candidate generation is not re-run. CompressARC is not modified or
re-invoked. No new candidate enters the table beyond what ACQ-001 already
archived. Every model in EXP002-D operates purely as a post-hoc reranker
over the fixed candidate set already on disk.
