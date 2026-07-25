# EXP002-C3 — PLAN (preregistration)

Preregistered before any orchestration code changes. Directly follows the
accepted EXP002-C2 verdict (PARALLELISE AND SCALE, adopt C3,
`experiments/EXP002C2/RESULTS.md`) and the user's explicit approval of one
bounded follow-up: the vCPU-aware CompressARC throughput pilot.

## 1. Experiment identifier

`EXP002-C3` — vCPU-aware CompressARC throughput pilot.

## 2. Research questions

- **Q1.** Is the candidate-throughput gap (task-count throughput ~3x, but
  compute-bound candidate throughput only ~1.4x, `experiments/EXP002C2/
  RESOURCE_ANALYSIS.md`) caused primarily by CPU oversubscription, nested
  thread-pool contention, context switching, process scheduling, Python
  overhead, or GPU contention?
- **Q2.** Can CPU-thread caps and vCPU-aware worker assignment increase
  unique candidates per minute while preserving C3's task throughput and
  candidate quality?
- **Q3.** Is the correct production architecture many independent
  processes/GPU, fewer processes with greater per-task training depth, or a
  mixed policy?
- **Q4.** What configuration should be frozen for the 170-test-index clean-
  corpus acquisition?
- **Q5.** What constraints do these measurements impose on later neural
  base-model selection (MODEL-001)?

This is an orchestration and resource-efficiency experiment. It is **not** a
solver-improvement experiment: no change to CompressARC's training,
candidate generation, or selection logic is in scope.

## 3. Falsifiable hypotheses

**H1 (CPU thread-pool contention is a real, correctable cost).** B1
(same C3 concurrency, single-thread numerical-library caps) shows measurably
lower CPU utilisation and/or higher unique-candidates/minute than B0 (C3
default), holding task throughput within measurement noise.

**H2 (a vCPU-derived concurrency exists that beats naive C3 on quality-
adjusted throughput).** B2 (concurrency derived from the measured effective
CPU quota, frozen before execution per the deterministic rule in
`BASELINE_SPEC.md` §4) meets or exceeds C3's task-count throughput while
using less CPU per candidate.

**H3 (no orchestration change damages quality or stability).** Neither B1
nor B2 drops unique-candidate generation below 90% of B0/C3's rate, and
neither introduces OOM, archive corruption, or a material hard-failure-rate
increase.

## 4. Theoretical motivation

`experiments/EXP002C2/RESOURCE_ANALYSIS.md` measured host CPU at 99.6-99.8%
utilisation in both C3 and C4, while GPU0 utilisation was only 88.0%
(C3)/97.7% (C4) — direct evidence that CPU, not GPU, was the binding
constraint on per-task training depth under oversubscription. Two
CPU-side hypotheses are untested by EXP002-C2: (a) PyTorch/NumPy/MKL each
default to spawning an intraop thread pool sized to the *visible* CPU count
inside every subprocess, so N concurrent CompressARC processes can request
N x (visible-CPU-count) threads for compute that could run correctly on 1
thread each, and (b) the true concurrency ceiling may be lower than 3-4
processes/GPU if the effective (cgroup/affinity-limited) CPU quota is
smaller than `os.cpu_count()` reports. Neither was measured in EXP002-C2.
This pilot measures both directly rather than assuming either.

## 5. Relationship to prior work

Direct continuation of `experiments/EXP002C2/PLAN.md` and `RESULTS.md`.
Reuses the identical 5-task sample, solver code (`solve_task_cli.py`
unmodified, byte-identical to EXP002-C/EXP002-C2), and archive conventions;
adds only a host-topology probe and CPU-thread/affinity orchestration
controls plus the telemetry to evaluate them. `experiments/EXP002C2/
BASELINE_SPEC.md`'s C3 assignment (GPU0={00576224,009d5c81,0520fde7},
GPU1={42f83767,8abad3cf}) is reused unchanged as B1's task assignment.

## 6. Exact baseline

**B0, reused where possible, not rerun unless a primary metric is
unrecoverable from archived telemetry.** `experiments/EXP002C2/RESULTS.md`'s
C3 result is the frozen baseline for every B1/B2 comparison:
- Task throughput: 7.42 tasks/hour (2.98x C1)
- Candidate throughput: 39.31 candidates/min (1.39x C1)
- Unique-candidate fraction: 93.96%
- Oracle coverage: 50.0% (3/6)
- GPU0 mean util 88.0%, CPU mean 99.6%
- 0 OOM, 0 archive corruption, 0 hard failures

## 7. Exact intervention

Two new configurations (`BASELINE_SPEC.md` §3 has the exact env/affinity
spec):

- **B1 — C3 thread-capped.** Identical process concurrency and task-to-GPU
  assignment as C3. Adds `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
  `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`,
  `VECLIB_MAXIMUM_THREADS=1`, `BLIS_NUM_THREADS=1` to each subprocess's
  environment (set before the subprocess's Python interpreter starts, so
  before any numerical library is imported) plus explicit non-overlapping
  CPU affinity per process where the host exposes enough usable CPUs and
  `psutil`/`os.sched_setaffinity` support it.
- **B2 — balanced vCPU-aware.** Concurrency derived from the measured
  effective CPU quota (Phase 1 probe), frozen by the deterministic rule in
  `BASELINE_SPEC.md` §4 before any B1/B2 result is seen. Same one-thread
  numerical-library caps as B1.

Both changes are implemented entirely in the orchestration/launch layer
(subprocess `env=` and `os.sched_setaffinity` calls in the notebook-
generation script). `solve_task_cli.py` and every vendored CompressARC
module are byte-identical to EXP002-C/EXP002-C2 — zero lines changed.

## 8. Frozen behavior

See `BASELINE_SPEC.md` §2 for the complete freeze list (identical to
EXP002-C2's, since the solver path is unmodified). Orchestration-layer
changes permitted: CPU thread-pool caps, explicit process-to-GPU assignment,
explicit CPU affinity, deterministic worker launch ordering, vCPU-aware
concurrency limits, telemetry collection, avoiding nested thread pools. Not
permitted: any change to training steps, model parameters, learning rates,
candidate extraction, task time limits, random seeds, solver phases,
candidate pruning, verification, or task-specific rules.

## 9. Telemetry

Full list in the acceptance message; implemented telemetry is enumerated in
`BASELINE_SPEC.md` §5. Notable additions over EXP002-C2: per-core CPU
utilisation, per-process CPU utilisation and context-switch counts (`psutil.
Process.cpu_times`, `.num_ctx_switches`), thread count per process, cgroup
CPU quota, CPU affinity map, solver phase timing already present in
`solve_task_cli.py`'s output.

## 10. Safety / early-abort rules

Unchanged from EXP002-C2 (`BASELINE_SPEC.md`-equivalent stall-deadline
check: process alive 20+ minutes past its own `time_limit_s` deadline, or
system RAM >95%). Abort only the active configuration, never the whole
kernel. Any triggered abort is logged with its real cause, never silently
downgraded to a lower concurrency and reported under the original config
name.

## 11. Primary metrics

The 21-metric list from the acceptance message, computed identically to
EXP002-C2's `analyse_config` plus the new CPU/context-switch/thread fields.
`QUALITY-ADJUSTED THROUGHPUT` and `DEPTH-ADJUSTED THROUGHPUT` as defined in
the acceptance message.

## 12. Success criteria

Exactly as specified in the acceptance message (7 mandatory + at least one
of 3 performance criteria). See `RESULTS.md` §"Success criteria" for the
scored checklist once B1/B2 complete.

## 13. Verdict logic

Five verdicts as specified: ADOPT VCPU-AWARE C3 / ADOPT BALANCED LOWER
CONCURRENCY / KEEP FROZEN C3 / REDESIGN ORCHESTRATION / REJECT FURTHER
MICRO-OPTIMIZATION.

## 14. Execution limits

Exactly the host-topology probe, B1, and B2. No third configuration. No
tuning after seeing B1's results (B2's rule is frozen in `BASELINE_SPEC.md`
§4 before either runs). No full 170-test-index acquisition. No RUN-002,
EXP003, EXP004, MODEL-001, MODEL-002. No NVARC or CompressARC solver
modification. No leaderboard submission.

## 15. State at preregistration

- Starting commit (branch point): `5147b2f32ff0ac814d40dfe4d6b20c9f2727726a`
  (EXP002-C2 final commit, branch `exp002c2-oversubscription-pilot`).
- Branch: `exp002c3-vcpu-throughput`, created from the above SHA.
- Upstream CompressARC: `83a22218024d46273eb32b769a906340202ffb4d`
  (`third_party/compressarc/NOTICE.md`).
- Prior Kaggle kernel: `redlotusthepotus/exp002c2-oversubscription-pilot`,
  last status `COMPLETE` (verified via `kaggle kernels status` at the start
  of this pilot).
- Five-task sample: `experiments/EXP002C/pilot_sample.json` (`00576224`,
  `009d5c81`, `0520fde7`, `42f83767`, `8abad3cf`).
- Seeds: `np.random.seed(0)`, `torch.manual_seed(0)`, module-level in
  `solution_selection.py`, unchanged.
- 40-minute (2400s) per-task safety cap, unchanged.
- Archive schema: per-task JSON, unchanged from EXP002-C/C2.
- Prior measurements this pilot builds on: C1 (2.49 tasks/hour), C3 (7.42
  tasks/hour, 39.31 candidates/min), C4 (7.45 tasks/hour, 39.05
  candidates/min) — see `experiments/EXP002C2/BASELINE_SPEC.md` §4 and
  `RESULTS.md`.
