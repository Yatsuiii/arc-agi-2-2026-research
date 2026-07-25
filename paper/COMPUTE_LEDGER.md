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
| Local GPU | **verified 2026-07-25**: NVIDIA RTX 4050 Laptop, 6 GB VRAM | Weaker than CompressARC's reference RTX 4070; `torch`/CUDA not yet installed (`experiments/EXP002C/FEASIBILITY.md`) |

## Ledger

| Date | Experiment | Hardware | Wall-clock | GPU-hours | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-07-24 | Phases 0-12 audit | local CPU | ~1 h | 0 | Static analysis, JSON parsing, PDF reading. No training, no downloads. |
| 2026-07-24 | EXP001 Stage A | local CPU | 20 s | 0 | Headroom analysis of CompressARC recorded traces. |
| 2026-07-25 | Kaggle metadata sweep | local CPU | ~2 min | 0 | Licence and file-listing queries for 6 datasets, 1 model instance, 2 kernels. Metadata only; **nothing downloaded**. |
| 2026-07-25 | RUN-001 access probes | Kaggle CPU + 2xT4 | ~15 min | ~0.2 | 5 probe kernel versions establishing Persona, accelerator, mounts and the import chain. |
| 2026-07-25 | RUN-001 baseline | Kaggle 2x T4 | 11 h 43 m (actual) | ~23 | COMPLETE/TIMED_OUT. 77/120 tasks, 1129 candidates archived. One version, one run. |
| 2026-07-25 | Harness build (Phase 1/2: schemas, ingestion, features, verifiers B0-B7, allocator interfaces) | local CPU | ~10 min incl. tests | 0 | 184 tests, no GPU, no network. Frozen-baseline mode verified to reproduce all 179 non-placeholder RUN-001 submitted attempts exactly. |
| 2026-07-25 | EXP002 execution (verifier evaluation + figures) | local CPU | 2.05 s (eval) + ~1 s (figures) | 0 | 8 baselines (B0-B7) + oracle over the 94-test-index RUN-001 archive; per-feature AUC over 487 grid-level rows. ~20,000x faster than the 11h43m GPU run that produced its input. |
| 2026-07-25 | EXP002-B (confidence fix, independence enforcement, V0-V3, bounded mechanism test) | local CPU | ~5 min incl. 228-test suite | 0 | No new GPU candidates generated, per this pass's explicit scope. `CORPUS_REQUIREMENTS.md`'s acquisition recommendation (CompressARC on ARC-AGI-2 training folds, ~20 min/task on 1x RTX 4070 per the reference-system table above) is **not launched** — local GPU availability is itself unverified and this is a plan pending separate approval, not executed compute. |
| 2026-07-25 | EXP002-C (preregistration, vendoring, instrumentation, driver code, feasibility check) | local CPU | minutes | 0 | Vendored CompressARC into `third_party/compressarc/`, instrumented for grid persistence, wrote `src/run002c/`. Verified local GPU exists (RTX 4050 Laptop, 6 GB) but `torch` is not installed and no GPU call was made. Preregistered estimate (pre-measurement): ~210-290 GPU-hours serially for the 500-test-index target — **not launched**, gated on explicit approval per `experiments/EXP002C/PLAN.md` §16. |
| 2026-07-25 | EXP002-C smoke pilot (5 preregistered ARC-AGI-2 training tasks, Kaggle 2xT4) | Kaggle 2x Tesla T4 | v1: 22s (errored on a mount-path bug, no task ran); v2: ~2.0h wall-clock (3 phases x ~40 min, 2 phases running 2 GPUs concurrently) | ~3.35 (v2 only; ~0.67 phase 1 + ~1.34 phase 2 + ~1.34 phase 3, both-GPU-hours) | `experiments/EXP002C/PILOT_RESULTS.md`. Measured per-task cost is 2.5-4x the reference RTX 4070 figure (revises the 210-290h estimate up to 454-675h serial for 500 tasks), but measured GPU utilisation (~26-28% mean) shows real oversubscription headroom untested by this pilot. Verdict: PARALLELISE AND SCALE. Stopped at exactly 5 tasks per explicit instruction; no further acquisition launched. |
| 2026-07-25 | EXP002-C2 oversubscription pilot (same 5 tasks, C1 reused + new C3/C4, Kaggle 2xT4) | Kaggle 2x Tesla T4 | v1: 20.0 min (both configs false-aborted by an orchestration bug at exactly 1200s, no throughput data); v2: C3 40.4 min + C4 40.3 min = ~1.34h wall-clock | v1: ~3.33 (wasted, 10 processes x 1200s); v2: C3 ~3.37 + C4 ~3.35 = ~6.72 (process-hours; Kaggle-quota GPU-hours = wall-clock x 2 = ~2.68) | `experiments/EXP002C2/RESULTS.md`. Task-count/test-index throughput scales ~linearly with concurrency (C3 2.98x, C4 2.99x over C1, both clearing the 1.75x threshold); a compute-bound candidate-rate metric scales only ~1.4x, explained by measured host CPU saturation (~99.6-99.8%) rather than GPU limits. No quality loss (diversity, oracle coverage held steady). Verdict: PARALLELISE AND SCALE, adopt C3. `SCALING_PROJECTION.md` revises the 500-test-index acquisition cost to 112-334 Kaggle quota GPU-hours (from 454-675 serial GPU-hours pre-oversubscription); the 170-test-index power floor is ~38 GPU-hours. No further acquisition launched. |
| 2026-07-25 | EXP002-C3 vCPU-aware throughput pilot (host-topology probe + B1/B2 vs. frozen C3, Kaggle 2xT4) | Kaggle 2x Tesla T4 | Host probe: ~2 min, metadata only. B1/B2 kernel: B1 40.4 min + B2 (2 sequential waves) 80.3 min = ~2.01h wall-clock | Host probe: ~0.03 (2 GPUs allocated briefly, no compute). B1/B2: B1 ~3.36 + B2 ~3.35 = ~6.71 (process-hours; Kaggle-quota GPU-hours = wall-clock x 2 = ~4.02) | `experiments/EXP002C3/RESULTS.md`. Host probe measured 4 effective vCPUs total (confirmed 3 independent ways + cgroup v2 quota), shared across both T4s with no CPU-core partition, and PyTorch already self-limiting to 2 threads/process by default. Neither B1 (thread caps + affinity, same C3 concurrency) nor B2 (vCPU-derived concurrency, evaluated to 1 process/GPU) improved on plain C3: B1's per-task training rate was statistically identical to C3's (0.212 vs 0.213 steps/s); B2's depth gain when uncontended (+91% steps/s) was lost to running in two sequential waves. Direct telemetry showed GPU-level sharing among concurrent CUDA contexts, not CPU contention, gates per-task rate. Verdict: KEEP FROZEN C3 — no further CPU-orchestration tuning pursued; EXP002-C2's acquisition-cost figures (112-334 GPU-hours/500 test-indices, ~38 GPU-hours/170-test-index floor) stand unrevised as the stable planning basis. No further acquisition launched. |

## Budgeting principle

A Kaggle GPU week is roughly 30 hours. One full 12-hour baseline run is ~40% of
that. This buys about **two full baseline runs per week**, which is the real
constraint on the research plan.

Consequence, and it drives Phase 12: the first experiment must be CPU-only or
must reuse a single stored artifact from one GPU run. Any thesis whose decisive
experiment needs more than ~4 baseline runs to test is not testable before the
deadline and should be rejected in Phase 11 on those grounds alone.
