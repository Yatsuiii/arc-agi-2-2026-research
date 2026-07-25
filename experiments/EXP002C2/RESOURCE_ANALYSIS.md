# EXP002-C2 — RESOURCE_ANALYSIS

Full telemetry breakdown behind `RESULTS.md`'s verdict. Source:
`artifacts/EXP002C2/pilot_kernel_output/exp002c2_pilot/telemetry_monitor.log`,
2320 samples at ~2s intervals, sliced into C3/C4 windows by each config's
own measured wall-clock duration (the two config cells ran back to back,
so cumulative duration is an exact window boundary).

## GPU utilisation, memory, power, temperature

| | C3 GPU0 (3 procs) | C3 GPU1 (2 procs) | C4 GPU0 (4 procs) | C4 GPU1 (1 proc, uncontended) |
| --- | --- | --- | --- | --- |
| Mean utilisation | 88.0% | 56.6% | **97.7%** | **12.2%** |
| Peak utilisation | 100% | 100% | 100% | 46% |
| Peak VRAM | 983 MB | 2223 MB | 1251 MB | 1955 MB |
| Mean power draw | 47.0 W | 42.7 W | 48.7 W | 28.0 W |
| Peak power draw | 52.0 W | 58.4 W | 52.8 W | 35.8 W |
| Mean temperature | 58.1C | 52.8C | 59.0C | 42.8C |
| Peak temperature | 60C | 54C | 60C | 49C |

No temperature or power reading approaches a concerning range for a T4 (rated
up to 70C / 70W typical); the early-abort thermal/power safety rules were
never close to triggering.

**C4's GPU1 slot (`42f83767` alone, fully uncontended) reads 12.2% mean
utilisation — lower than C1's own solo-task baseline (27.8%, a different
task).** This is consistent with `BASELINE_SPEC.md`'s characterisation of
`42f83767` as intrinsically slow for structural reasons (n_test=2, large
grids, largest peak memory of any task in the sample) rather than
GPU-compute-bound: a task whose bottleneck is memory movement or per-step
Python overhead rather than raw SM occupancy will show low GPU utilisation
regardless of concurrency level, which is exactly what both C1 (paired) and
C4 (solo) show for this specific task.

## Host telemetry (new in this pilot, not available for C1)

| | C3 | C4 |
| --- | --- | --- |
| Mean CPU utilisation (system-wide) | **99.6%** | **99.8%** |
| Peak CPU utilisation | 100.0% | 100.0% |
| Mean RAM used | 6207 MiB | 6167 MiB |
| Peak RAM used | 6306 MiB | 6223 MiB |
| Disk usage | negligible in both (candidate JSON files are small; not separately broken out) |

**System CPU was essentially saturated in both configurations, throughout
the entire run — not just at peak, but on average.** This is the central
new finding this pilot's added telemetry (absent from C1) makes visible.

## Why this changes the interpretation of "GPU headroom"

`experiments/EXP002C/PILOT_RESULTS.md` read C1's ~26-28% mean GPU
utilisation as evidence of "substantial headroom" for oversubscription — a
reasonable reading at the time, since C1 had no CPU telemetry to check the
alternative explanation `experiments/EXP002C2/PLAN.md` §16 named ("CPU-side
overhead in the per-step logging/postprocessing... rather than raw GPU
compute could be the true bottleneck").

This pilot's own telemetry resolves that ambiguity directly:

- Going from 1x to 3x concurrency, GPU0 utilisation rose from 27.8% to
  88.0% — a real, large increase, showing the GPU genuinely was
  underused at 1x and genuinely is doing more work at 3x.
- But system CPU was *already* at 99.6% by 3x concurrency (C3) — before
  GPU0 itself even reached saturation. Going from 3x to 4x (C4) pushed GPU0
  to 97.7% (near-saturated) while CPU stayed pinned at 99.8% (no further
  room to give).
- The scaling-efficiency numbers in `RESULTS.md` §7 metric 13 (41.5% at 3x,
  33.3% at 4x, both relative to an ideal-linear GPU0 candidate rate) are
  consistent with a system where **CPU time per task, not GPU time per
  task, sets the achievable concurrency ceiling on this hardware.** Each
  additional concurrent process adds a roughly fixed CPU cost (Python
  interpreter, per-step postprocessing in `solution_selection.py`'s
  `_track_solution`, `_postprocess_solution`) that competes for the same
  small number of vCPUs regardless of how much GPU capacity remains.

## What is not measured, worth resolving in a later throughput-optimisation pass

- **Host vCPU count.** Not logged this pass (`psutil.cpu_count()` was not
  called). If Kaggle's standard notebook environment provides a small
  number of vCPUs (commonly 4 on the free tier), running 4-5 concurrent
  heavyweight Python/PyTorch processes would saturate CPU by simple
  arithmetic, independent of any inefficiency in the postprocessing code
  itself — a much simpler explanation than a deep architectural problem,
  and one that changes the fix (request more CPU, or cap concurrency to
  vCPU count) versus a code-level redesign.
- **Per-process CPU time breakdown.** The 99.6-99.8% figure is system-wide,
  not attributed to a specific process or code path (training loop vs.
  postprocessing vs. Python/CUDA driver overhead) — `RESULTS.md`'s
  "correctable orchestration bottleneck" framing is a well-evidenced
  hypothesis, not yet a pinpointed one.
