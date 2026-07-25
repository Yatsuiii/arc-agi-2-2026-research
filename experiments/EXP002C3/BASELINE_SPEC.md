# EXP002-C3 — BASELINE_SPEC

The frozen configuration every EXP002-C3 run must match exactly, the B0
numbers every comparison is made against, and the exact, pre-registered
rule that fixes B2's concurrency before any B1/B2 result is seen.

## 1. The five tasks (frozen, unchanged from EXP002-C/EXP002-C2)

`experiments/EXP002C/pilot_sample.json`: `00576224`, `009d5c81`, `0520fde7`,
`42f83767`, `8abad3cf`. No task added, removed, or substituted.

## 2. Freeze list (identical to EXP002-C2's, solver path unmodified)

| Component | Frozen value |
| --- | --- |
| CompressARC upstream commit | `83a22218024d46273eb32b769a906340202ffb4d` |
| `solve_task_cli.py` | byte-identical to EXP002-C/C2 — 0 lines changed |
| Vendored modules | byte-identical to `third_party/compressarc/` |
| Iteration count | 2000 |
| Search procedure | `train.take_step` per-step loop |
| Native selection | `solution_selection.Logger._update_most_frequent_solutions` |
| Random seeds | `np.random.seed(0)`, `torch.manual_seed(0)` |
| Timeout | 2400s (40 min) per task |
| Archive schema | one JSON per task, unchanged |
| Candidate extraction | `logger.solution_grids` hash->grid map, unchanged |
| Correctness analysis | same `grid_digest` + exact-match logic |

**Changed variables**: subprocess environment (thread-pool caps), CPU
affinity, and process-to-GPU concurrency level. Nothing inside the Python
process that trains the model is touched.

## 3. B0 baseline, restated for direct comparison

Reused from `experiments/EXP002C2/RESULTS.md`'s C3 (not rerun unless a
primary metric proves unrecoverable from archived telemetry, in which case
`RESULTS.md` states the gap explicitly rather than estimating it):

| Metric | B0/C3 value |
| --- | --- |
| Wall-clock | 2425.2s (~40.4 min) |
| Task throughput | 7.42 tasks/hour (2.98x C1) |
| Candidate throughput | 39.31 candidates/min (1.39x C1) |
| Unique-candidate fraction | 94.0% |
| Oracle coverage | 50.0% (3/6) |
| GPU0 mean/max util | 88.0% / 100% |
| GPU1 mean/max util | 56.6% / 100% |
| CPU mean/max util | 99.6% / 100% |
| Hard failures / OOM / archive corruption | 0 / 0 / 0 |

**Not available from B0/C3** (instrumentation gap): per-core CPU
utilisation, per-process context-switch counts, thread count per process,
cgroup CPU quota, CPU affinity map. `RESOURCE_ANALYSIS.md` reports these as
"not measured (C3 predates this telemetry)" for the B0 column rather than
estimating them — this is exactly why B1 is defined as "same concurrency,
add thread caps + full telemetry" rather than a from-scratch design, so the
B0-vs-B1 delta isolates the thread-cap intervention as cleanly as the
missing columns allow.

## 4. B1 — C3 thread-capped

Same task-to-GPU assignment as EXP002-C2's C3:

| GPU | Tasks |
| --- | --- |
| GPU0 | `00576224`, `009d5c81`, `0520fde7` (3 processes) |
| GPU1 | `42f83767`, `8abad3cf` (2 processes) |

Each subprocess launched with an augmented environment (set via
`subprocess.Popen(..., env=...)`, before the child interpreter starts, so
before NumPy/MKL/PyTorch read any of these on import):

```
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
VECLIB_MAXIMUM_THREADS=1
BLIS_NUM_THREADS=1
```

CPU affinity: applied via `os.sched_setaffinity(pid, {core_ids})`
immediately after each subprocess starts, only if (a) the host exposes
`os.sched_setaffinity` (Linux; Kaggle's docker image qualifies) and (b) the
Phase-1 probe reports at least as many effective CPUs as launched
processes. The affinity map is deterministic: process launch order (GPU0's
3 tasks in list order, then GPU1's 2) is assigned consecutive core IDs
starting at 0, wrapping only if effective CPUs < 5. The exact realised map
is recorded in `RESULTS.md`, not assumed from this rule.

## 5. B2 — balanced vCPU-aware, frozen concurrency rule

**The rule (fixed now, before Phase 1's probe result is read for tuning
purposes):**

1. Let `Q` = the effective CPU quota measured in Phase 1 (the smaller of:
   cgroup CPU quota in whole cores, `len(os.sched_getaffinity(0))`, and
   `psutil.cpu_count(logical=True)` — the most conservative of the three,
   since any one of them can be the true ceiling).
2. Reserve 1 effective CPU for orchestration/telemetry/artifact I/O:
   usable budget `U = Q - 1`.
3. Per-GPU worker count `W = clamp(floor(U / 2), 1, 3)` — divided by 2
   because 2 GPUs share the host's CPUs, clamped to CompressARC's 3-per-T4
   nominal cap already validated as safe by C3, never exceeding it and
   never exceeding the 4-per-T4 experiment ceiling this project has set.
4. Total process slots = `2 * W`. If slots >= 5 (this pilot's task count),
   launch all 5 tasks in one wave using B1's GPU0/GPU1 split truncated or
   extended to `W` per GPU (task list order preserved: first `W` tasks to
   GPU0, remainder to GPU1, capped at `5 - W`). If slots < 5, the excess
   tasks queue for a second wave on the same GPU, launched immediately when
   a slot frees (first process to exit on that GPU).
5. Same one-thread numerical-library environment as B1, same affinity
   policy as B1 §4's rule, re-applied to B2's actual worker count.

This rule is mechanical and was written before Phase 1 ran. `RESULTS.md`
records `Q`, `U`, `W`, and the resulting exact GPU assignment as measured,
not as assumed here — if the realised host has, say, 4 effective CPUs,
`W = clamp(floor(3/2), 1, 3) = 1`, i.e. B2 degrades to C1-equivalent
concurrency; if it has 8, `W = clamp(floor(7/2), 1, 3) = 3`, i.e. B2 equals
B1's concurrency with a different affinity reservation. Both outcomes are
valid results of the rule, not failures of the pilot.

## 6. Telemetry added for B1/B2 (new, not present in B0/C3)

- Per-process: PID, task_id, device, start/end timestamp, wall-clock, exit
  code (as C3 had), plus thread count (`psutil.Process(pid).num_threads()`),
  voluntary/involuntary context switches
  (`psutil.Process(pid).num_ctx_switches()`), per-process CPU time
  (`psutil.Process(pid).cpu_times()`), and CPU affinity as actually set
  (`os.sched_getaffinity(pid)` read back, not merely the requested map).
- Host: per-core `psutil.cpu_percent(percpu=True)` in addition to the
  system-wide scalar C3 already sampled; load average
  (`os.getloadavg()`); swap (`psutil.swap_memory()`).
- GPU: same extended `nvidia-smi` query as C3 (power, temperature) plus
  per-process GPU memory where `nvidia-smi --query-compute-apps` is
  available inside the Kaggle container (recorded as unavailable if not,
  not fabricated).
- Archive/IO: bytes written per task-result flush, serialization duration
  (wrapping the existing `Path.write_text` call time), measured in the
  orchestration layer around (not inside) `solve_task_cli.py`.
