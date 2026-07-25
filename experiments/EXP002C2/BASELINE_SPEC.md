# EXP002-C2 — BASELINE_SPEC

The frozen configuration every EXP002-C2 run must match exactly, and the C1
numbers every comparison is made against.

## 1. The five tasks (frozen, unchanged from EXP002-C)

From `experiments/EXP002C/pilot_sample.json`, fold seed `20260725`:

| task_id | n_test | fold | C1 steps/s (measured) | C1 role |
| --- | --- | --- | --- | --- |
| `00576224` | 1 | C | 0.627 | phase 1 solo baseline, GPU0 |
| `009d5c81` | 1 | A | 0.578 | phase 2 concurrent, GPU0 |
| `0520fde7` | 1 | A | 0.672 | phase 2 concurrent, GPU1 |
| `42f83767` | 2 | A | 0.178 (outlier) | phase 3 concurrent, GPU0 |
| `8abad3cf` | 1 | A | 0.578 | phase 3 concurrent, GPU1 |

No task is added, removed, or substituted. No seed, iteration count, or
per-task timeout changes.

## 2. Freeze list

Unchanged from `experiments/EXP002C/PILOT_RESULTS.md`'s run and from
upstream CompressARC, verified by inspecting the same vendored source
(`third_party/compressarc/`, `src/run002c/solve_task_cli.py`) this pilot
reuses without modification:

| Component | Frozen value |
| --- | --- |
| CompressARC upstream commit | `83a22218024d46273eb32b769a906340202ffb4d` (`third_party/compressarc/NOTICE.md`) |
| Candidate-generation logic | `arc_compressor.py`, `layers.py`, `initializers.py`, `multitensor_systems.py` — byte-identical to `third_party/compressarc/` |
| Iteration count | 2000 (`--n-iterations 2000`, unchanged) |
| Search procedure | `train.take_step` per-step training loop, unchanged |
| Native selection | `solution_selection.Logger._update_most_frequent_solutions`, unchanged |
| Random seeds | `np.random.seed(0)`, `torch.manual_seed(0)` (`solution_selection.py` module level), unchanged |
| Task ordering within a config | insertion order in the config's process list (below) |
| Timeout | 2400s (40 min) per task, unchanged |
| Archive schema | one JSON per task per `solve_task_cli.py`'s existing schema, unchanged |
| Candidate extraction | `logger.solution_grids` hash->grid map, unchanged (the one documented instrumentation from EXP002-C, itself frozen since) |
| Phase aggregation | per-config JSON record (`phase_c1/c3/c4_*.json`), same shape as EXP002-C's `phase_*.json` |
| Correctness analysis | same `grid_digest` + exact-match-against-`solutions[task_id]` logic as `build_pilot_notebook.py`'s analysis cell |
| Output persistence | one file write per task immediately on completion, before the config's aggregate report is written |

**The only changed variable is process concurrency per GPU** (1 for C1, up to
3 for C3, up to 4 for C4) and the telemetry collection added around it.

## 3. C3 / C4 GPU assignment

| Config | GPU0 (task_id list) | GPU1 (task_id list) | GPU0 load | GPU1 load |
| --- | --- | --- | --- | --- |
| C1 (reused) | sequential: solo, then paired (see `experiments/EXP002C/PILOT_RESULTS.md`) | — | 1x throughout | 1x in 2 of 3 phases |
| C3 | `00576224`, `009d5c81`, `0520fde7` | `42f83767`, `8abad3cf` | 3x | 2x |
| C4 | `00576224`, `009d5c81`, `0520fde7`, `8abad3cf` | `42f83767` | 4x | 1x (uncontended control) |

`42f83767` (the measured outlier — `n_test=2`, largest peak memory, 0.178
steps/s uncontended in C1) is deliberately isolated on GPU1 in both C3 and
C4 rather than mixed with three other tasks on the same card, so its known
intrinsic slowness cannot be misread as a symptom of contention, and so C4's
GPU1 slot doubles as a genuinely uncontended re-measurement of it (distinct
from C1 phase 3, where it ran paired with `8abad3cf`).

## 4. C1 baseline, restated for direct comparison

From `experiments/EXP002C/PILOT_RESULTS.md` (all values exact, not rerun):

| Metric | C1 value |
| --- | --- |
| Total wall-clock (3 phases) | 2410.7s + 2406.8s + 2406.4s = 7223.9s (~2.01h) |
| Tasks completed (of 5) | 5/5 (all timed_out at the 2400s cap, none crashed) |
| Total GPU-hours (both cards) | ~3.35 |
| Mean GPU utilisation | 27.8% (solo), 25.1%/25.8% (pair 1), 26.0%/27.3% (pair 2) |
| Peak GPU utilisation | 42% (solo), 59%/39% (pair 1), 74%/41% (pair 2) |
| Peak VRAM | 47 MB - 1.86 GB per task |
| Total candidates | 3,399 |
| Unique candidates | 3,194 (94.0%) |
| Candidate oracle coverage | 3/6 = 50.0% |
| Timeouts | 5/5 (expected, all hit the 2400s cap) |
| Hard failures / OOM / archive corruption | 0 |
| Completed tasks per wall-clock hour | 5 tasks / 2.01h = **2.49 tasks/hour** |

**Not available from C1** (instrumentation gap, not rerun to fill it, per
`PLAN.md` §6): per-process PID, power draw, temperature, CPU utilisation,
system RAM, disk use, process-launch delay, per-phase breakdown within a
task. `experiments/EXP002C2/RESOURCE_ANALYSIS.md` reports these columns as
"not measured (C1 predates this telemetry)" rather than estimating them.

## 5. Telemetry added for C3/C4 (new, not present in C1)

- Per-process record: PID, task_id, device, start timestamp, end timestamp,
  wall-clock, exit code.
- Extended `nvidia-smi` query: adds `power.draw`, `temperature.gpu` to the
  existing `utilization.gpu,memory.used,memory.total` fields C1 already
  sampled.
- Host telemetry: CPU utilisation (`psutil.cpu_percent`), system RAM
  (`psutil.virtual_memory`), disk usage of the run directory, all sampled on
  the same ~2s cadence as the GPU monitor.
- Per-task candidate-write throughput: candidates written since the last
  sample, computed from the growing per-task JSON's size/candidate count
  rather than re-parsing the whole file every tick.
