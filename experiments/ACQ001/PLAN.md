# ACQ-001 — PLAN

Build and validate a production clean-corpus acquisition pipeline, then
acquire the first of two shards (~half) of the pre-registered 170-test-index
clean corpus using the frozen C3 configuration
(`experiments/EXP002C3/RESULTS.md`: KEEP FROZEN C3).

This is explicitly not: a leaderboard run, a new solver experiment, a model
bake-off, verifier tuning, confidence-based allocation, or RUN-002.

## Phases

| Phase | Deliverable | Status |
| --- | --- | --- |
| 0 — Recover state | Confirmed frozen C3 config, prior test suite, branch `acq001-clean-corpus-shard-a` | Done |
| 1 — Freeze the 170-index corpus | `artifacts/ACQ001/{corpus_manifest,folds}.json`, `experiments/ACQ001/SPLIT_MANIFEST.md`, 0 leakage across 3 duplicate-detection notions | Done |
| 2 — Build the production driver | `src/run002c/acquire_shard.py` (checkpointed, retrying, tested), `artifacts/ACQ001/{shard_a,shard_b}.json`, `experiments/ACQ001/SHARDING_PLAN.md` | Done |
| 3 — Production-path validation | 5-test-index bounded run through the real production driver, `experiments/ACQ001/VALIDATION_GATE.md` — **PASS** | Done |
| 4 — Launch Shard A | Kaggle kernel `redlotusthepotus/acq001-shard-a`, v1, frozen C3, Shard A only | Done — **COMPLETE**, 80/80 tasks |
| 5 — Validate Shard A | This document's companions: `BASELINE_SPEC.md`, `SHARD_A_RESULTS.md`, `ARTIFACT_MANIFEST.tsv` | Done |

## Explicit stop point

Per the acceptance instruction: "Stop after SHARD A ingestion and
validation." Shard B is not launched by this task regardless of Shard A's
outcome — its launch readiness is documented (not executed) in
`SHARD_A_RESULTS.md`'s success-gate section.

## Documents in this experiment

- `SPLIT_MANIFEST.md` — Phase 1: fold assignment, TEST-subset draw, leakage
  controls.
- `SHARDING_PLAN.md` — Phase 2: Shard A/B balancing procedure and predicted
  cost.
- `VALIDATION_GATE.md` — Phase 3: bounded production-path validation, bugs
  found and fixed, gate result.
- `BASELINE_SPEC.md` — the frozen C3 configuration this acquisition ran
  under (restated here, decided in EXP002-C2/C3, not by this task).
- `SHARD_A_RESULTS.md` — Phase 5: Shard A's validated results, oracle
  coverage, Shard B success-gate evaluation.
- `ARTIFACT_MANIFEST.tsv` — checksums and provenance for every raw output
  file.
