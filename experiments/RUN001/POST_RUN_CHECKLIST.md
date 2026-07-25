# RUN-001 — post-run checklist

Run this once the Kaggle kernel `redlotusthepotus/run001-nvarc-t4x2-baseline`
has reached a terminal state. Every step is local and CPU-only; none of them
touch the kernel itself except the read-only status query in step 1.

## 0. Preconditions

- [ ] Do not repush, cancel, or version the kernel at any point below.
- [ ] Do not launch EXP002 (or any other GPU/verifier experiment) before step
      6 passes.

## 1. Confirm the kernel is actually finished

```
kaggle kernels status redlotusthepotus/run001-nvarc-t4x2-baseline
```

or, equivalently and reused by the next step:

```python
from src.run001.download_outputs import kernel_status
kernel_status("redlotusthepotus/run001-nvarc-t4x2-baseline")
```

- [ ] Status is `COMPLETE`, `ERROR`, or `CANCELLED` (a terminal state). If it
      is still `RUNNING` or `QUEUED`, stop here — do not download.

## 2. Download outputs, checksum, validate, classify

```
python -m src.run001.download_outputs
```

This queries status once more (refuses to proceed if non-terminal, unless
`--force`), downloads every kernel output file unmodified into
`artifacts/run001/`, writes `checksums.json` (sha256 of every downloaded
file), runs `src.run001.validate_outputs.validate`, and writes
`artifacts/run001/ingestion_manifest.json` recording the kernel status,
classification, file count and validation result.

- [ ] `checksums.json` exists and lists every file under `artifacts/run001/`.
- [ ] `ingestion_manifest.json` exists and records a `classification`.

## 3. Read the classification

`ingestion_manifest.json["classification"]` is one of:

| Classification | Meaning | Next step |
| --- | --- | --- |
| `COMPLETE` | All 120 tasks produced candidates, no hard problems | proceed to step 4 |
| `PARTIAL` | Some tasks missing candidates, no per-task time-guard hits recorded | proceed to step 4, note the shortfall in `RESULT.md` |
| `TIMED_OUT` | Some tasks missing candidates and the per-task/per-batch time guards fired (`BASELINE_SPEC.md` "Runtime guards") | expected outcome per `PLAN.md` §10 (the T4x2 port has looser compute than the reference); proceed to step 4 |
| `FAILED` | Kernel errored/cancelled, or a hard validation problem (bad submission, corrupted archive, leaked ground truth) | **stop.** Read `validate_outputs` output's `problems` list before doing anything else. Do not proceed to EXP002 preparation. |

- [ ] Classification recorded above.
- [ ] If `FAILED`, the specific `problems` entries are copied into
      `experiments/RUN001/RESULT.md` before any further action.

## 4. Inspect the validation report in full

```
python -m src.run001.validate_outputs artifacts/run001 --kernel-status <status from step 1>
```

Check in particular:

- [ ] `n_tasks_with_candidates` vs `n_tasks_expected` (120) — the coverage
      number for `RESULT.md` §15 "deviations from plan".
- [ ] `n_tasks_corrupted_or_truncated == 0` (task_summary.csv reconciliation).
- [ ] `n_selected_mismatches` — expected 0; a nonzero count on a `COMPLETE`
      run would indicate the selection-record join is wrong and must be
      understood before trusting anything downstream.
- [ ] `archive_has_answer_fields == 0` (leakage check — this must never be
      nonzero; it is a hard stop if it is).
- [ ] `n_placeholder_attempts` and `pct_placeholder` — expected close to 0 on
      a `COMPLETE` run; nonzero is consistent with `PARTIAL`/`TIMED_OUT`.

## 5. Record the run

- [ ] Fill `experiments/RUN001/RESULT.md` from the template in
      `paper/EXPERIMENT_REGISTRY.md` ("Result template"), using the validation
      report's stats and the ingestion manifest's checksums as the artifact
      record.
- [ ] Update `paper/EXPERIMENT_REGISTRY.md`'s RUN-001 row: status from
      `RUNNING` to the classification from step 3 (mapping `PARTIAL` /
      `TIMED_OUT` to `COMPLETE` in the registry's own status vocabulary if the
      run is usable, or `KILLED` if it is not — see
      `paper/EXPERIMENT_REGISTRY.md` "Status values").
- [ ] Log actual GPU-hours in `paper/COMPUTE_LEDGER.md`'s Ledger table (the
      row currently reads "up to 11 h 40, up to ~23 GPU-hours" as an estimate;
      replace with the measured wall-clock from `run_manifest*.json` /
      `runtime_summary*.json`).

## 6. Run the CPU-only headroom analysis (Stage B of EXP001, precondition for EXP002)

```
python -m src.analysis.candidate_headroom artifacts/run001 --split evaluation
```

Writes `artifacts/exp002/candidate_headroom.json`. This is
`docs/CANDIDATE_RESEARCH_THESES.md` §T2's "cheapest decisive experiment"
groundwork and EXP001-B's ARC-AGI-2 replication in one pass — both were
blocked on RUN-001 landing.

- [ ] `oracle_candidate_accuracy` and `selected_accuracy` populate (ground
      truth is available for the evaluation split, `README.md` "Data
      policy").
- [ ] Compare against EXP001-A's ARC-AGI-1 headroom
      (`experiments/EXP001/RESULT.md` §7) — is the gap similar in kind, given
      that this run's accuracy numbers are themselves labelled CONTAMINATED
      (`RUN001/PLAN.md` §5)?
- [ ] Update `experiments/EXP001/PLAN.md`/`RESULT.md` cross-references or add
      a `RESULT.md` "Stage B" section, per the plan's own note that Stage B
      "is not executed and must not be until RUN-001 is approved and run."

## 7. Only then: EXP002

`experiments/EXP002/PLAN.md` is preregistered but **not executed**. Its own
preconditions (restated from that file) are exactly steps 1-6 above. Do not
begin EXP002's Stage 1 code until this checklist is complete and
`experiments/RUN001/RESULT.md` is committed.
