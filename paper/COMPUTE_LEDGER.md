# COMPUTE_LEDGER

Compute spent, compute available, and compute the reference systems needed. The
last column is the reason this project must pick a thesis that is cheap to test.

## Reference-system compute (from published sources)

| System | Stage | Hardware | Time | Source |
| --- | --- | --- | --- | --- |
| NVARC Qwen3-4B | SFT pretraining | 4 nodes x 8xH100 | 27 h | `nvarc_2025.pdf` §3.1 |
| NVARC SDG | synthetic generation | 8xH100 node, gpt-oss-120b at 15k tok/s | not stated; 126,901 input programs + 103,253 puzzles | §2, §2.3, §2.4 |
| NVARC TRM | pretraining | 8xH100 | 24 h | §4.1 |
| NVARC TRM | test-time fine-tuning | Kaggle 4xL4 | ~2 h for 240 tasks | §4.2 |
| NVARC ARChitects branch | inference + TTT | Kaggle 4xL4 | 12 h for 240 tasks | §3, Table 2 |
| ARChitects LLaDA | pretraining | 8xH100 | 39 h, 175k steps | `page.md` |
| ARChitects | dev budget | 1-3x GH200 for the season, plus 2 weeks of 16xH100, plus ~3 weeks of 8xA100 | months | `page.md` §Compute Budget |
| TRM (original) | pretraining | 4xH100 | 3 days, 100k epochs | TRM README |
| CompressARC | per task | 1x RTX 4070 | ~20 min | `papers/03_compressarc.pdf` |
| SOAR | per iteration | not locally recorded | 3k samples + 6k refinements per task | `papers/02_soar.pdf` |

Read the ARChitects row again: a season of 1-3 GH200 machines plus two weeks of
16xH100. That is the compute behind 21.67%. **We are not going to out-scale
anyone.**

## Calendar

| Milestone | Date | Days from 2026-07-25 |
| --- | --- | --- |
| ARC Prize 2026 ARC-AGI-2 deadline | **2026-11-02 23:59** | **100** |
| ARC Prize 2026 paper-track deadline | **2026-11-09 23:59** | **107** |

Retrieved from the Kaggle API. At ~2 full baseline runs per week (see
Budgeting principle below), 100 days is roughly **28 usable 12-hour runs** for
the whole project, including calibration, ablations and the final submission.

## Our available compute

| Resource | Quota | Notes |
| --- | --- | --- |
| Kaggle API access | working (OAuth, CLI 2.2.4) | verified 2026-07-25 |
| Kaggle notebook GPU | 2xT4 (16 GB each) or 4xL4 depending on allocation; competition runtime cap 12 h | The 2026 baseline targets `NvidiaTeslaT4` explicitly |
| Kaggle GPU quota | ~30 h/week, subject to change | Hard constraint on iteration speed |
| Kaggle submissions | 1/day historically | The binding constraint on leaderboard feedback, and the reason `paper/CLAIM_LEDGER.md` A4 exists |
| Local CPU | this machine | Sufficient for all Phase 3 analysis and for the whole selection-ablation family |
| Local GPU | **not verified** | To be recorded before any local training is planned |

## Ledger

| Date | Experiment | Hardware | Wall-clock | GPU-hours | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-07-24 | Phases 0-12 audit | local CPU | ~1 h | 0 | Static analysis, JSON parsing, PDF reading. No training, no downloads. |
| 2026-07-24 | EXP001 Stage A | local CPU | 20 s | 0 | Headroom analysis of CompressARC recorded traces. |
| 2026-07-25 | Kaggle metadata sweep | local CPU | ~2 min | 0 | Licence and file-listing queries for 6 datasets, 1 model instance, 2 kernels. Metadata only; **nothing downloaded**. |
| 2026-07-25 | RUN-001 access probes | Kaggle CPU + 2xT4 | ~15 min | ~0.2 | 5 probe kernel versions establishing Persona, accelerator, mounts and the import chain. |
| 2026-07-25 | RUN-001 baseline | Kaggle 2x T4 | up to 11 h 40 | up to ~23 | Baseline execution and candidate archive. One version, one run. |

## Budgeting principle

A Kaggle GPU week is roughly 30 hours. One full 12-hour baseline run is ~40% of
that. This buys about **two full baseline runs per week**, which is the real
constraint on the research plan.

Consequence, and it drives Phase 12: the first experiment must be CPU-only or
must reuse a single stored artifact from one GPU run. Any thesis whose decisive
experiment needs more than ~4 baseline runs to test is not testable before the
deadline and should be rejected in Phase 11 on those grounds alone.
