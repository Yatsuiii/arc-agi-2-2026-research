# RUN-001 — validation report

Produced by `python -m src.run001.validate_outputs artifacts/run001/run001
--kernel-status COMPLETE`. Full JSON in that command's output; the substantive
results are below.

## Classification: `TIMED_OUT`

`ok = true`, zero hard problems after the provenance manifest was reconstructed
(§Manifest below). `TIMED_OUT` rather than `PARTIAL` because the shortfall is
explained by the per-task guard binding, not by a crash: 41 of 77 processed
tasks hit the 1200 s guard.

## Checks

| Check | Result |
| --- | --- |
| Kernel terminal status | `COMPLETE` (Kaggle) |
| Tracebacks in kernel log | **0** |
| CUDA OOM events | **0** |
| Submission task ids vs contract | 120/120 present, 0 missing, 0 unexpected |
| Submission entry counts | every task matches its test-input count |
| Attempt structure | every entry is exactly `{attempt_1, attempt_2}` |
| Grid validity (non-placeholder) | 0 malformed grids |
| Archive records malformed | **0 / 1129** |
| Selection records malformed | **0 / 595** |
| Submitted grids absent from archive | **0** |
| Selected-grid identity vs archive | **0 mismatches / 179 checked** |
| Task-summary reconciliation | 77 / 77 rows reconciled |
| Corrupted or truncated task records | **0** |
| Archive records carrying an answer field | **0** (no leakage) |
| Gzip archives readable | yes, both, clean to EOF |

## Coverage (the run is partial by budget, as predicted)

| Quantity | Value |
| --- | --- |
| Tasks in split | 120 |
| Tasks reached (summary rows) | 77 |
| Tasks with >= 1 candidate | 72 |
| Tasks reached but 0 candidates (timed out empty) | 5 |
| Tasks never reached (budget drained) | 43 |
| Test-inputs total | 172 |
| Test-inputs with candidates | 94 |
| Tasks that hit the 1200 s per-task guard | 41 / 77 |
| Candidate records archived | 1129 |
| Selection/ranking records | 595 |
| Non-placeholder submitted attempts | 179 / 344 |
| Placeholder `[[0]]` attempts | 165 / 344 (47.97%) |

## Resource envelope

From `task_summary.csv`, over 77 processed tasks:

| Metric | min | median | max |
| --- | --- | --- | --- |
| solve seconds | 388 | 1206 | 1721 |
| peak inference MiB | 5903 | 9916 | **13148** |

Peak inference memory reached 13.1 GiB of the T4's 15.0 GiB — tight but within
budget, no OOM. Confirms the `ACCESS_REPORT.md` R2 concern was real and survived.

## Leakage

No archive record carries a `solution`/`ground_truth`/`answer`/`label`/`correct`
field. Predicted grids that happen to equal a ground-truth grid are solver
output, not leakage. The validator holds ground truth only to *count* correct
predictions, never writes it.

## Manifest

The notebook did not pass `manifest=` to the `CandidateArchive` constructor, so
no `run_manifest.*.json` was emitted during the run. This is a real
instrumentation gap and the fix for any future run is one keyword argument.

`run_manifest.json` was reconstructed post-hoc from verifiable provenance only:
the commit stamped into the executed kernel's cell 0
(`131eba8144f99d561efe8624a5156d428935312e`, recovered by `kaggle kernels
pull`), the kernel's terminal status, the environment measured by the probe
kernels, and SHA256 of every downloaded artifact. No runtime measurement is
invented in it; the file states this in its own header.
