# ACQ-001 — VALIDATION_GATE

Phase 3: bounded production-path validation, exactly the exact production
driver (`src/run002c/acquire_shard.py`, embedded verbatim into the Kaggle
notebook by `build_acq001_notebook.py`), 5 test-indices (`00576224`,
`045e512c`, `09c534e7`, `0e206a2e`, `12422b43` — one task reused from every
prior EXP002-C/C2/C3 pilot plus four new-to-this-project training tasks,
all n_test=1). Full production `time_limit_s=2400`/`n_iterations=2000`
(unshortened, per the lesson `experiments/EXP002C2/ERROR_ANALYSIS.md`
recorded: a shortened smoke test cannot exercise real-timing orchestration
paths like the stall-abort check).

## Local validation (before any GPU spend)

`tests/test_acquire_shard.py`, 8 cases against a stubbed process launcher
— no subprocess, no GPU:

| Check | Result |
| --- | --- |
| Wave construction (`build_waves`, slots-per-GPU split) | PASS |
| All-success shard run | PASS |
| Crash retry (1 retry, then success, `attempts=2` recorded) | PASS |
| Permanent failure after max attempts | PASS |
| Checkpoint resume skips already-complete tasks | PASS |
| Forced-interruption (stall-abort) leaves a readable, correct checkpoint | **FAIL on first attempt, fixed** — see §3 |
| Archive ingestion produces a valid candidate archive | PASS |
| Archive ingestion handles a missing output file without crashing | PASS |

## Real Kaggle validation

**Kernel v1** (`redlotusthepotus/acq001-shard-validation`, version 1):
solve phase succeeded — all 5 tasks completed in one wave, 2420-2425s
each (matching every prior EXP002-C/C2/C3 measurement on `00576224`
specifically: 2420.1s here vs. 2410-2425s across three earlier pilots).
**Archive ingestion crashed**: `ModuleNotFoundError: No module named 'src'`
— `acquire_shard.py` imported `from src.run001.archive import ...`, which
does not exist on Kaggle's flat `/kaggle/working` layout. Preserved
(not discarded) at `artifacts/ACQ001/validation_output_v1_import_error/`.

Fixed with a try/except import fallback (repo layout first, flat layout
second — matching `solve_task_cli.py`'s own existing `sys.path`-fallback
precedent). Verified the fix against the **real v1 downloaded data**
locally before spending more GPU time: re-running `ingest_archive` on the
actual `checkpoint_state.json` and `per_task/*.json` from the failed v1
kernel produced a valid 2739-record archive across all 5 tasks.

**Kernel v2** (same kernel, version 2, with the fix): **COMPLETE**, full
pipeline succeeded end-to-end — solve + archive ingestion in one run. Raw
output: `artifacts/ACQ001/validation_output/`.

## Validation checklist

| Item | Result |
| --- | --- |
| C3 worker count | 3 tasks -> cuda:0, 2 tasks -> cuda:1 (confirmed via `checkpoint_state.json`'s `device` field) — the frozen split, correct for a 5-task/one-wave shard |
| GPU assignment | Correct, matches `build_waves`'s deterministic rule |
| Task scheduling | One wave (5 tasks < 6 slots), no queuing needed, confirmed via kernel log |
| Candidate archive | `candidates.VALIDATION.jsonl.gz`, 3216 records, all 5 task_ids present |
| Task summary | `task_summary.VALIDATION.csv`, 5 rows, `hit_time_guard=1` for all (matching every prior pilot — no task has ever converged early) |
| Runtime summary | `runtime_summary.VALIDATION.json`: `n_completed=5, n_failed=0` |
| Errors archive | Not created (0 errors) — `CandidateArchive` only creates `errors.*.jsonl` lazily on the first `record_error` call, confirmed as correct behaviour, not a missing-file bug |
| Checkpoint/restart | Verified locally (stubbed) — a checkpoint marking a task complete is correctly skipped on the next `run_shard` call, never re-launched |
| Shard resume | Same mechanism as checkpoint/restart — no separate code path, verified by the same test |
| Checksums | Computed for every artifact, `experiments/ACQ001/ARTIFACT_MANIFEST.tsv` will carry these forward for Shard A |
| Merge logic | Not separately exercised at Kaggle scale (only one shard/session in this validation) — the merge procedure (`experiments/ACQ001/SHARDING_PLAN.md`'s "what Shard B contains" note, generalised: union per-task output files by filename, no collision possible since each task runs exactly once) is unchanged from `experiments/EXP002C3/CORPUS_ACQUISITION_DECISION.md`'s existing description and does not depend on anything this validation could have contradicted |
| No ground truth entering generation | Confirmed by code inspection: `solve_task_cli.py` reads only `--challenges` (never a solutions file); `CandidateArchive`'s manifest and every recorded field derive from the solver's own output, never from `arc-agi_training_solutions.json` |
| No duplicate completion records | Confirmed: `checkpoint_state.json` has exactly one entry per task_id; `completed_tasks.json` has exactly 5 unique entries |
| Archive integrity after forced interruption | Verified locally (stubbed stall-abort test) — not re-verified on real Kaggle infrastructure (killing a live Kaggle kernel mid-run from the CLI is not a safe or repeatable action to script; the local test exercises the identical code path `run_wave`/`_score_wave` that would run in that scenario) |

## Bugs found and fixed by this validation

1. **Forced-interruption checkpoint bug** (caught locally, before any GPU
   spend): a wave-abort left a killed task in `"pending_retry"` status even
   though `run_shard` stops the whole shard on abort and never launches the
   retry — permanent limbo, not a terminal state. Fixed by threading the
   `aborted` flag into `_score_wave`.
2. **Kaggle flat-layout import bug** (caught on real Kaggle infrastructure,
   costing one ~40-minute validation run): `ingest_archive`'s `from
   src.run001.archive import ...` does not resolve under `/kaggle/working`.
   Fixed with a try/except fallback; re-verified against the real v1 output
   before spending further GPU time, then re-confirmed end-to-end on a v2
   kernel run.

## Gate result

**PASS.** Every item in the validation checklist above is satisfied. Shard
A may proceed.
