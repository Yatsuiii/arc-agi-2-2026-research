# EXP002-C smoke pilot — RESULTS

Scope actually executed: **exactly the 5 preregistered ARC-AGI-2 training
tasks** in `experiments/EXP002C/pilot_sample.json`, on Kaggle 2xT4, per the
user's explicit approval of "the bounded EXP002-C smoke pilot only." No
further acquisition was launched. This document is the full analysis and the
one required verdict; nothing after it runs automatically.

## 0. Two kernel versions

**v1** (`redlotusthepotus/exp002c-compressarc-pilot`, version 1) errored 17s
in, before any task started: the competition mounts at
`/kaggle/input/competitions/arc-prize-2026-arc-agi-2/`, not
`/kaggle/input/arc-prize-2026-arc-agi-2/` as the first build assumed. Zero
GPU-hours spent on the tasks themselves; confirmed 2xT4 available before the
crash (`torch.cuda.device_count() == 2`, both `Tesla T4`). Log preserved at
`artifacts/EXP002C/pilot_kernel_output_v1_failed/exp002c-compressarc-pilot.log`.
Fixed with a runtime path resolver (tries both forms, same pattern RUN-001
used for its own mount-path drift) and re-pushed as **v2**, which completed
successfully. Everything below is v2.

## 1. Runtime per task and per test example

**Every task hit the pilot's 2400s (40-minute) per-task safety cap before
reaching 2000 iterations.** This is itself the headline finding: nothing in
this pilot ran to completion at the paper's own 2000-step setting.

| task | steps completed in 2400s | steps/s | extrapolated time for 2000 steps |
| --- | --- | --- | --- |
| `00576224` | 1506 | 0.627 | 53.2 min |
| `009d5c81` | 1389 | 0.578 | 57.6 min |
| `0520fde7` | 1613 | 0.672 | 49.6 min |
| `42f83767` (n_test=2) | 428 | 0.178 | 187.0 min |
| `8abad3cf` | 1388 | 0.578 | 57.6 min |

`42f83767` is the outlier: it has 2 test examples (vs. 1 for the other four)
and by far the largest peak memory (1.86 GB vs. 47-438 MB), consistent with
meaningfully larger/more complex grids driving a much heavier per-step cost,
not a concurrency artifact — it ran in phase 3 alongside `8abad3cf`, which
posted a normal 0.578 steps/s in the same window.

Extrapolated full-2000-step time per task: **mean 81.0 min (1.35h) including
the outlier, 54.5 min (0.91h) excluding it, median 57.6 min (0.96h).** All
three are well above the reference RTX 4070 figure of ~20 min/task
(`paper/COMPUTE_LEDGER.md`) — this hardware (or this run's per-task
overhead) is roughly **2.5-4x slower than the reference card**, not the
1.3-1.8x guessed in `experiments/EXP002C/PLAN.md` §12 before any measurement
existed.

Per-test-example time is not meaningfully different from per-task time for
the four `n_test=1` tasks; `42f83767`'s 2 test examples share one training
run, so its per-example cost is roughly half its per-task cost.

## 2. Peak VRAM and GPU utilisation

Peak VRAM (`torch.cuda.max_memory_allocated`, confirmed independently by the
`nvidia-smi` monitor log): **47 MB to 1.86 GB across all 5 tasks** — a small
fraction of a T4's 16 GB. VRAM is not remotely a constraint at 1
task/GPU.

GPU utilisation, sliced from the continuous `nvidia-smi` monitor log
(`artifacts/EXP002C/pilot_kernel_output/exp002c_pilot/gpu_monitor.log`) by
phase window:

| phase | GPU0 mean util | GPU0 peak util | GPU1 mean util | GPU1 peak util |
| --- | --- | --- | --- | --- |
| 1 (solo, GPU0 only) | 27.8% | 42% | 0.0% | 0% |
| 2 (concurrent) | 25.1% | 59% | 25.8% | 39% |
| 3 (concurrent) | 26.0% | 74% | 27.3% | 41% |

**Mean utilisation never exceeds ~28% on either card, solo or concurrent.**
CompressARC's 76K-parameter model and small per-step batch are not
compute-saturating a T4 at 1 task/GPU. Combined with the VRAM figures above,
this is direct, measured evidence that a single T4 has substantial headroom
for more than one concurrent task — untested by this pilot (see §3, §6).

## 3. Can two T4s process separate tasks concurrently?

**Yes, cleanly.** Two lines of direct evidence, not inference:

1. **Utilisation is unaffected by concurrency.** GPU0's mean utilisation in
   the concurrent phases (25.1%, 26.0%) matches its solo-phase utilisation
   (27.8%) within noise. If the two processes were contending for the same
   physical GPU, GPU0's phase-2/3 utilisation would be depressed relative to
   solo, or GPU1 would show near-zero throughput; neither happened.
2. **Per-step throughput is unaffected.** `009d5c81` (concurrent, GPU0,
   phase 2) ran at 0.578 steps/s and `8abad3cf` (concurrent, GPU1, phase 3)
   also ran at 0.578 steps/s — the same rate as the solo-phase task's 0.627
   steps/s (a different task, so not identical, but the same order of
   magnitude, not roughly halved as GPU contention would produce).

Caveat: the pilot used a different task in each phase (task heterogeneity is
real, per §1's outlier), so this is not a perfectly matched A/B test of one
task run solo vs. concurrent. The utilisation-based evidence in point 1 does
not have this confound and is the stronger of the two.

## 4. Candidate, integrity, and failure statistics

| Metric | Value |
| --- | --- |
| Total candidates | 3,399 |
| Total unique candidates | 3,194 (94.0%) |
| Total test-indices | 6 (5 tasks, one with `n_test=2`) |
| Singleton test-indices | **0 (0.0%)** |
| Candidate oracle coverage | **3/6 = 50.0%** |
| Native score (accumulated log-sum-exp) | min -33.81, max 6.42, mean -4.72, stdev 6.46, n=2,729 |
| Archive integrity | 5/5 expected tasks recovered, all per-task JSON files present and readable |
| Failures | **0 hard failures.** All 5 tasks hit the 2400s time cap (`timed_out: true`) — an expected, recorded outcome given §1, not a crash or data-loss event; every task still produced a valid, non-empty candidate set and the incremental per-task JSON survived regardless. |

Two results worth flagging on their own:

- **Zero singletons**, versus RUN-001/NVARC's 9.6% singleton rate
  (`experiments/EXP002B/CONFIDENCE_SEMANTICS.md`). CompressARC's
  per-step-logged candidate accumulation structurally produces many distinct
  candidates even under time pressure — the confidence-collapse bug EXP002-B
  fixed may simply not arise on this corpus's shape, though n=6 is far too
  small to generalise that claim.
- **50% oracle coverage after 21-71% of the paper's own training budget**
  (steps completed / 2000) is a genuinely encouraging signal for headroom:
  even truncated runs are finding the correct answer among their candidates
  on half of this tiny sample. Also far too small a sample to report as a
  rate with any confidence — stated here as a directional observation only.

## 5. Comparison against the preregistered 210-290 GPU-hour estimate

**The pilot revises this estimate upward, not downward.** §1's per-task
extrapolation, scaled to 500 tasks:

| basis | 100 tasks | 250 tasks | 500 tasks |
| --- | --- | --- | --- |
| mean (incl. outlier) | 135.0 h | 337.5 h | 675.1 h |
| median | 96.1 h | 240.2 h | 480.3 h |
| mean (excl. outlier) | 90.9 h | 227.1 h | 454.3 h |

All three bases exceed `PLAN.md`'s preregistered 210-290 GPU-hour range at
500 tasks; the median basis alone is roughly 1.7-2.3x that range. The
original estimate scaled the reference card's ~20 min/task figure by an
assumed 1.3-1.8x slowdown; the measured slowdown is closer to 2.5-4x.

## 6. Extrapolated corpus cost (objective 6, restated as the table above)

500 tasks ≈ **454-675 serial GPU-hours** at 1 task/GPU on this hardware. With
2-GPU parallelism (§3) at face value, halve those figures: **227-338
wall-clock hours**, still 9-14 days of continuous dual-T4 running — far
beyond a Kaggle session (12h cap) and a large fraction of a ~30
GPU-hour/week quota (`paper/COMPUTE_LEDGER.md`), meaning many weeks of
scheduled sessions even before considering §2's untested oversubscription
headroom.

## 7. Can a smaller corpus still meet the preregistered power requirement?

**Yes, at the low end of the range `CORPUS_REQUIREMENTS.md` already
pre-registered.** That document's McNemar-based minimum was **170-500
test-indices**, with 500 chosen as the conservative top of the range; 170
was always an acceptable, if less conservative, floor. This pilot's 6
test-indices from 5 tasks is not enough to fix a firm tasks-per-test-index
ratio (`n_test` varied 1-2 here), but at a rough ~1.2 test-indices/task, 170
test-indices needs roughly ~140 tasks total, materially cheaper than the
500-task target:

- 140 tasks at the median per-task rate: **~134 serial GPU-hours**, or ~67
  wall-clock hours with 2-GPU parallelism — payable within a few weeks at the
  ~30 GPU-hour/week Kaggle quota, unlike the full 500-task target.

This trades statistical power at the margin (per `CORPUS_REQUIREMENTS.md`'s
own McNemar planning table, 170 pairs sits at the low end of 80%-power
detection for a 10-15% discordance rate) but remains inside the
pre-registered, justified range — not an ad hoc downward revision invented
after seeing results.

## 8-9. What was not touched

Per the user's explicit constraints: CompressARC's solver behaviour was not
modified beyond the grid-persistence instrumentation already committed and
verified accuracy-neutral before this pilot
(`third_party/compressarc/NOTICE.md`); no tuning or continuation decision was
made by inspecting held-out results — the 50% oracle-coverage figure in §4 is
reported, not acted on, and the corpus these 6 test-indices belong to (one is
Fold C by `pilot_sample.json`'s own fold assignment) plays no role in this
verdict. Execution stopped at exactly 5 tasks; nothing beyond this document
was launched.

## Verdict: PARALLELISE AND SCALE

Not "scale to a smaller corpus," not "redesign," not "reject." Reasoning:

1. **The naive 1:1-task-per-GPU economics do not work.** §5/§6 show the full
   500-task target costs more than originally estimated, not less — proceeding
   at the parallelism level this pilot tested would not be a responsible use
   of the project's remaining compute budget.
2. **But §2's utilisation data is direct, measured evidence of a specific,
   large, untapped efficiency gain**, not a hopeful guess: ~26-28% mean GPU
   utilisation and sub-2GB VRAM at 1 task/GPU, on hardware with 16GB per
   card. CompressARC's own upstream `parallel_train.py`
   (`third_party/compressarc/NOTICE.md`, not vendored this pass) exists
   specifically to schedule many puzzles per GPU for exactly this reason —
   this project chose the simpler 1-process-per-task design for this pilot's
   isolation guarantees, not because oversubscription was believed
   infeasible.
3. **§3 already confirms the more basic claim (2 separate GPUs, 2 separate
   processes, no cross-GPU interference)** that any oversubscription scheme
   would need to hold as a precondition. The next, still-bounded step is a
   second pilot — not the full run — that tests 3-4 concurrent processes per
   GPU on a small task sample and re-measures §1's per-task wall-clock under
   contention, which is the direct test this pilot did not run.
4. If that follow-on shows real throughput gains (which §2's utilisation
   numbers suggest is likely, though not guaranteed — CPU-side overhead in
   the training loop's per-step logging could dominate instead of GPU
   compute), the full 500-task corpus becomes payable and §7's
   power-reducing smaller-corpus fallback is unnecessary. If it does not,
   §7's 170-test-index/~140-task target remains the pre-registered, still
   fully justified fallback — not a new decision, already on the record.

## Exact next experiment (not started)

A second bounded pilot, same discipline as this one: preregister a small
task sample (5-10 tasks), run each at 3-4 concurrent CompressARC processes
per T4 (8-16 total concurrent processes across 2 GPUs) instead of 1
process/GPU, and measure per-task wall-clock and per-GPU utilisation under
that contention. Compares directly against this pilot's §1/§2 baseline
numbers. Requires separate approval before running, per the user's explicit
"do not continue beyond 5 tasks without my explicit approval" and "stop
after the pilot" instructions — not launched by this pass.
