# EXP002-C3 — RESULTS

Kaggle 2xT4 kernel `redlotusthepotus/exp002c3-b1b2-vcpu-throughput`, v1,
status COMPLETE. Raw output: `artifacts/EXP002C3/pilot_kernel_output/
exp002c3_pilot/{b1b2_report.json,config_B1.json,config_B2.json,
config_B2_wave2.json,per_task/*.json,telemetry_monitor.log}`.

## 0. Headline result

**Neither B1 (thread caps) nor B2 (vCPU-derived concurrency) materially
improves candidate or iteration throughput over frozen C3.** The Phase 1
probe's finding (`HOST_TOPOLOGY.md`: 4 effective vCPUs, PyTorch already
self-limiting to 2 threads/process) predicted this outcome would be
plausible, and the measured data confirms it directly: B1's per-task
`steps_per_s` (mean 0.212) is statistically indistinguishable from plain
C3's (mean 0.213, `experiments/EXP002C2/RESULTS.md`), despite B1 running at
the same 5-processes-on-4-cores oversubscription. **The bottleneck is
GPU-level compute sharing between concurrent CUDA contexts on the same T4,
not CPU thread-pool contention** — see §4 for the direct evidence.

## 1. B0 baseline (reused, not rerun)

C3 from `experiments/EXP002C2/RESULTS.md`: 2425.2s wall-clock, 7.42
tasks/hour, 39.31 candidates/min, 36.94 unique-candidates/min, 94.0%
unique-candidate fraction, 50.0% (3/6) oracle coverage, mean steps/s 0.213,
2576 total steps.

## 2. B1 — C3 thread-capped

| Metric | Value |
| --- | --- |
| Wall-clock | 2421.19s (40.35 min) |
| Task throughput | 7.43 tasks/hour (matches B0, expected — same concurrency) |
| Candidates | 1727 total, 1630 unique (94.4%) |
| Candidates/min | 42.80 (+8.9% vs B0) |
| Unique-candidates/min | 40.40 (+9.4% vs B0) |
| Oracle coverage | 33.3% (2/6) — down from B0's 3/6, a single-answer difference on n=6, within the documented noise band |
| Mean steps/s (5 tasks) | 0.2122 (B0: 0.2125 — within 0.1%, no depth gain) |
| Total steps | 2569 (B0: 2576 — within 0.3%) |
| Depth-adjusted throughput | 3819.4 steps/wall-clock-hour (B0: 3823.6 — within 0.1%) |
| Failures / OOM / archive corruption | 0 / 0 / 0 |
| Aborted | No |

Every process ran with `num_threads=1` confirmed in its own telemetry
snapshot (§4), so the thread cap was genuinely applied. It produced a
small (+8.9%) candidate-count uptick with essentially zero change in
training depth or aggregate iteration throughput — most plausibly ordinary
run-to-run stochasticity in candidate generation (a single run each, no
repeats; `paper/REPRODUCIBILITY.md`'s determinism policy already documents
that CompressARC's per-step trajectory is not guaranteed identical across
runs) rather than a causal effect of the thread cap.

**Affinity note:** the deterministic core-assignment rule
(`BASELINE_SPEC.md` §4) assigns consecutive core IDs 0-4 to B1's 5
processes without a wrap-around when `effective_cpus < 5` — the code did
not implement the wrap the spec described. Task `8abad3cf` was assigned
core ID 4, which does not exist on this 4-core host;
`os.sched_setaffinity` failed (`[Errno 22] Invalid argument`) and that one
process ran with default (unrestricted) affinity instead of a pin. Logged,
not hidden — see `ERROR_ANALYSIS.md` §1. The other 4/5 processes were
pinned successfully.

## 3. B2 — balanced vCPU-aware

Rule evaluated against the measured host (`HOST_TOPOLOGY.md`): `Q=4, U=3,
W=1` — 1 worker/GPU, 2 total slots. With only 5 tasks and 2 slots, the run
required **two sequential waves**:

- **Wave 1** (2 tasks, fully uncontended, 1/GPU): `00576224`@GPU0,
  `009d5c81`@GPU1.
- **Wave 2** (3 tasks, queued): `0520fde7`@GPU0, `8abad3cf`@GPU0 (2
  concurrent on GPU0), `42f83767`@GPU1 (uncontended on GPU1).

| Metric | Value |
| --- | --- |
| Wall-clock (both waves) | 4820.90s (80.35 min) |
| Task throughput | 3.73 tasks/hour (-49.7% vs B0 — expected, half the nominal concurrency) |
| Candidates | 2836 total, 2603 unique (91.8%) |
| Candidates/min | 35.30 (-10.2% vs B0) |
| Unique-candidates/min | 32.39 (-12.3% vs B0) |
| Oracle coverage | 50.0% (3/6), matching B0 |
| Mean steps/s (5 tasks) | 0.4062 (+90.9% vs B0 — real per-task depth gain) |
| Total steps | 4892 |
| Depth-adjusted throughput | 3653.6 steps/wall-clock-hour (-4.4% vs B0) |
| Failures / OOM / archive corruption | 0 / 0 / 0 |
| Aborted | No (either wave) |

**The per-task depth gain (+91% steps/s) does not translate into higher
aggregate throughput** because B2 spreads that gain over roughly twice the
wall-clock time (two sequential waves instead of one 5-way wave) — see §4.

## 4. Direct evidence: GPU-level sharing, not CPU threading, is the bottleneck

Per-core/per-process telemetry, not inferred:

| Window | Concurrent processes | Measured host CPU (mean/max) | GPU0 util (mean/max) | GPU1 util (mean/max) |
| --- | --- | --- | --- | --- |
| B1 (5-way, 4 cores) | 5 | 99.6% / 100% | 91.6% / 100% | 40.8% / 64% |
| B2 wave 1 (2-way, 4 cores) | 2 (1/GPU) | 51.2% / 53.5% | 27.3% / 42% | 25.4% / 58% |
| B2 wave 2 (3-way, 4 cores) | 3 (2 on GPU0, 1 on GPU1) | 76.0% / 78.1% | 85.0% / 100% | 25.3% / 70% |

**CPU% scales almost exactly with process-count/core-count**: 2/4=50.0%
measured 51.2%; 3/4=75.0% measured 76.0%; 5/4=125% (clamped) measured
99.6%. This confirms the host is genuinely oversubscribed exactly as
`HOST_TOPOLOGY.md` predicted, and rules out any measurement artifact.

**But GPU utilization tracks concurrent-processes-per-GPU, not host CPU
load**: GPU0 jumps from 27.3% (1 process, wave 1) to 85.0% (2 processes,
wave 2) — a near-linear increase with GPU-side concurrency, independent of
the fact that wave 2's host CPU (76.0%) was far from saturated (unlike
B1's 99.6%). **Per-task training rate (`steps_per_s`) is governed by how
many processes share the same GPU, not by host CPU saturation**:
`0520fde7` ran at 0.354 steps/s in B2 wave 2 (2-way GPU0 contention, CPU at
76%) versus 0.613 steps/s for `00576224` in B2 wave 1 (1-way GPU0,
uncontended, CPU at 51%) — a real slowdown from GPU sharing alone, at a
CPU load level nowhere near saturated.

Per-process context-switch counts (`psutil.Process.num_ctx_switches()`)
corroborate real, measurable CPU contention in B1 that B2 does not have:
B1's involuntary context switches ranged 162k-260k per process over the
run; B2's ranged 26k-39k, a 5-7x reduction. **CPU contention is real and
precisely measured, but it does not gate aggregate throughput** — B1's
depth-adjusted throughput (3819.4 steps/hour) is statistically the same as
B0/C3's (3823.6) despite this large CPU-contention difference, and B2's
(3653.6, with far less CPU contention) is not higher, only slightly lower.

**Conclusion for Q1**: the ~3x task-count vs ~1.4x candidate-throughput gap
measured in EXP002-C2 is best explained by GPU-side time-sharing among
concurrent CUDA contexts on the same T4 (a hardware/driver-level
constraint on how many processes can make training progress
simultaneously on one physical GPU), not by CPU thread-pool
oversubscription. Host CPU saturation is real and directly measured here
for the first time, but it is a symptom of running many processes, not the
binding constraint on useful compute throughput.

## 5. Candidate-diversity preservation

| Config | Unique-candidate fraction |
| --- | --- |
| B0 (C3) | 94.0% |
| B1 | 94.4% |
| B2 | 91.8% |

All three clear the 90% floor (`PLAN.md` §12/success criteria). No config
shows a diversity collapse.

## 6. Candidate-oracle result (n=6, small-sample warning applies)

| Config | Oracle coverage |
| --- | --- |
| B0 (C3) | 50.0% (3/6) |
| B1 | 33.3% (2/6) |
| B2 | 50.0% (3/6) |

B1's drop is a single test-index difference on n=6 — the same
single-answer noise band `experiments/EXP002C2/BASELINE_SPEC.md` already
documented for C4 vs C3. Not interpreted as a systematic quality collapse.

## 7. Success-criteria check

Mandatory (all must pass):

| # | Criterion | B1 | B2 |
| --- | --- | --- | --- |
| 1 | No OOMs | PASS (0/5) | PASS (0/5) |
| 2 | No archive corruption | PASS (10/10 valid JSON archived) | (shared check) |
| 3 | No repeated process crashes | PASS (0 failures) | PASS (0 failures) |
| 4 | >=90% of B0's unique-candidate rate per task | PASS (aggregate 94.4%) | PASS (aggregate 91.8%) — per-task breakdown not separately persisted, see `ERROR_ANALYSIS.md` §3 |
| 5 | No material hard-failure increase | PASS | PASS |
| 6 | Stable for full task guard | PASS (no aborts, all `timed_out=True` as expected at the 2400s cap) | PASS |
| 7 | Behavior-neutrality review passes | PASS, see `BEHAVIOR_NEUTRALITY.md` | PASS |

Performance (at least one required):

| # | Criterion | B1 | B2 |
| --- | --- | --- | --- |
| A | >=20% higher unique-candidates/min than B0 | FAIL (+9.4%) | FAIL (-12.3%) |
| B | >=20% higher completed iterations/min than B0 | FAIL (-0.1%) | FAIL (-4.5%) |
| C | Similar useful throughput with materially lower CPU/context-switching | FAIL (CPU still 99.6%, unchanged from B0's known C3 level) | FAIL (CPU is much lower, 51-76%, but throughput is also much lower, -49.7% task-count, not "similar") |

**Both B1 and B2 pass every mandatory criterion but fail all three
performance criteria.** Neither configuration earns adoption under the
preregistered rule.

## 8. Best production configuration

**Plain C3 (3 processes/GPU, no thread caps, no CPU affinity) remains the
best configuration measured across EXP002-C2 and EXP002-C3.** Thread
capping (B1) does not measurably help; CPU-affinity pinning does not
measurably help (and partially failed to apply, see §2); reducing
concurrency to match the measured CPU quota (B2) trades away task-count
throughput (the metric the corpus's power requirement is denominated in)
for no compensating quality or depth gain large enough to justify it.

## 9. Quality-adjusted throughput (test-idx x oracle-coverage / hour)

| Config | Value |
| --- | --- |
| B0 (C3) | 4.45/hour |
| B1 | 2.97/hour |
| B2 | 2.24/hour |

Both new configurations are **worse** than B0 on this metric — B1 from the
oracle-coverage dip (small-sample noise), B2 from the doubled wall-clock.
Neither displaces C3.

## 10. Errors, OOMs, archive integrity

0 OOMs, 0 archive corruption, 0 hard failures across 10 task-processes (5
B1 + 2 B2-wave1 + 3 B2-wave2). One orchestration-layer bug (the
unimplemented affinity wrap, §2) — logged and does not affect solver
correctness or archive integrity, since the affected process simply ran
unpinned rather than crashing. Full detail in `ERROR_ANALYSIS.md`.

## 11. Verdict

**KEEP FROZEN C3.** CPU-side orchestration controls (thread caps, affinity,
reduced concurrency matched to the measured 4-vCPU quota) do not
materially improve useful throughput, and the measured mechanism (GPU-level
sharing among concurrent CUDA contexts, §4) is not a correctable
orchestration bottleneck within this pilot's scope — it is closer to an
inherent hardware constraint of running N processes on one T4. This also
supports **REJECT FURTHER MICRO-OPTIMIZATION on the CPU-orchestration
axis specifically**: no further CPU-thread/affinity tuning is worth
pursuing for this workload on this host. The frozen configuration for any
future clean-corpus acquisition is **C3 as originally measured in
EXP002-C2** — 3 processes/GPU, default threading, no affinity pinning.
