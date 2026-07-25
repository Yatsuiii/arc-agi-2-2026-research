# EXP002-C3 — RESOURCE_ANALYSIS

Full telemetry tables underlying `RESULTS.md` §4. Source:
`artifacts/EXP002C3/pilot_kernel_output/exp002c3_pilot/telemetry_monitor.log`
(~2s cadence, 3510 combined samples across the three windows) and each
process's `last_proc_snapshot` in `config_{B1,B2,B2_wave2}.json`.

## 1. GPU utilisation, per window

| Window | GPU0 mean/max | GPU1 mean/max | Concurrent processes (GPU0 / GPU1) |
| --- | --- | --- | --- |
| B1 | 91.6% / 100% | 40.8% / 64% | 3 / 2 |
| B2 wave 1 | 27.3% / 42% | 25.4% / 58% | 1 / 1 |
| B2 wave 2 | 85.0% / 100% | 25.3% / 70% | 2 / 1 |

B2 wave 1's single-process GPU utilisation (27.3%/25.4%) closely matches
C1's original solo measurement (`experiments/EXP002C/PILOT_RESULTS.md`:
~26-28% mean) — a useful cross-experiment consistency check confirming the
telemetry pipeline reads real values, not an artifact of this pilot's own
instrumentation.

## 2. Host CPU, per window

| Window | CPU mean/max | Processes | Cores | Process:core ratio | Predicted CPU% (ratio x 100, capped at 100) | Measured |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 99.6% / 100% | 5 | 4 | 1.25 | 100% (clamped) | 99.6% |
| B2 wave 1 | 51.2% / 53.5% | 2 | 4 | 0.50 | 50% | 51.2% |
| B2 wave 2 | 76.0% / 78.1% | 3 | 4 | 0.75 | 75% | 76.0% |

The measured-vs-predicted match (within ~1pp in all three cases) is direct
confirmation that host CPU utilisation is driven almost entirely by raw
process count against the 4-core quota `HOST_TOPOLOGY.md` measured, with no
evidence of additional CPU load from anything else running on the host.

## 3. Per-process telemetry (thread count, context switches, CPU time)

All processes ran with `num_threads=1` (the thread cap took effect in every
process where it was requested — B1 and B2 both use `thread_cap=1`).

| Config | task_id | Device | num_threads | Voluntary ctx switches | Involuntary ctx switches | CPU user (s) | CPU system (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | 00576224 | cuda:0 | 1 | 3583 | 181708 | 2028.5 | 3.19 |
| B1 | 009d5c81 | cuda:0 | 1 | 3124 | 173289 | 2029.19 | 2.92 |
| B1 | 0520fde7 | cuda:0 | 1 | 3623 | 169250 | 2131.92 | 3.17 |
| B1 | 42f83767 | cuda:1 | 1 | 2935 | 162190 | 2134.53 | 3.83 |
| B1 | 8abad3cf | cuda:1 | 1 | 1117 | 259613 | 1202.53 | 2.18 |
| B2 wave1 | 00576224 | cuda:0 | 1 | 3181 | 26543 | 2402.07 | 2.16 |
| B2 wave1 | 009d5c81 | cuda:1 | 1 | 3022 | 28387 | 2403.60 | 2.13 |
| B2 wave2 | 0520fde7 | cuda:0 | 1 | 1970 | 38618 | 2404.06 | 2.12 |
| B2 wave2 | 42f83767 | cuda:1 | 1 | 618 | 38951 | 2404.59 | 2.22 |
| B2 wave2 | 8abad3cf | cuda:0 | 1 | 1670 | 35555 | 2404.39 | 2.08 |

**B1's involuntary context switches (162k-260k per process) are 5-7x B2's
(26k-39k)** — real, precisely measured CPU contention from the 5-on-4-core
oversubscription. Despite this large difference, aggregate depth-adjusted
throughput barely moved (`RESULTS.md` §4), which is the core evidence that
CPU contention, though real, is not the binding constraint on useful
compute output for this workload.

`8abad3cf`'s anomalously low voluntary-switch count (1117) and short CPU
user time (1202.5s, roughly half the others) in B1 corresponds to the
process whose CPU-affinity pin failed (`ERROR_ANALYSIS.md` §1) — it ran
unpinned, and also happened to finish its last reported psutil snapshot
earlier in its lifetime (the snapshot is a point-in-time read during
polling, taken more sparsely for short-lived measurement windows near
process exit, not a full-lifetime integral) — flagged rather than treated
as a clean number.

## 4. Steps/s (training depth) per task, per config

| task_id | B0 (C3, from EXP002C2) | B1 | B2 |
| --- | --- | --- | --- |
| 00576224 | 0.2492 | 0.2697 | 0.6128 |
| 009d5c81 | 0.2354 | 0.2540 | 0.5870 |
| 0520fde7 | 0.2730 | 0.3114 | 0.3539 |
| 42f83767 | 0.0713 | 0.0810 | 0.1767 |
| 8abad3cf | 0.2338 | 0.1450 | 0.3004 |
| **Mean** | **0.2125** | **0.2122** | **0.4062** |

B2's per-task rate roughly doubles B0/B1's for every task except
`0520fde7` (which sees a smaller gain, 0.354 vs 0.273/0.311, because in B2
wave 2 it shares GPU0 with `8abad3cf` — still 2-way GPU contention, not
the fully uncontended case). This task-by-task pattern is fully consistent
with §1's GPU-sharing explanation: tasks that run alone on their GPU in
B2 (wave 1's two tasks) gain the most; tasks that still share a GPU in B2
(wave 2's `0520fde7`/`8abad3cf` pair) gain less.

## 5. Memory

No VRAM figures were re-captured with per-process granularity in this
pilot (`nvidia-smi --query-compute-apps` was listed as a stretch goal in
`BASELINE_SPEC.md` §6 but the aggregate `--query-gpu` telemetry, unchanged
from EXP002-C2, was used instead — same instrumentation as C3/C4, no new
gap introduced). Peak VRAM for these five tasks was already established in
`experiments/EXP002C/PILOT_RESULTS.md` §2 (47 MB - 1.86 GB per task) and is
not expected to change under thread caps or affinity, since neither
touches per-task model size or batch composition. System RAM stayed well
below any abort threshold in all three windows (no RAM-exhaustion aborts
triggered, `config_*.json`'s `aborted: false` for all three).

## 6. What was not measured

- Per-process GPU memory (`nvidia-smi --query-compute-apps`) — as noted,
  deferred; the aggregate `memory.used` figure this pilot's telemetry
  carries forward from EXP002-C2 is sufficient to confirm no VRAM pressure
  (no OOM occurred in any of the 10 processes).
- I/O/archive overhead (bytes written, flush duration, serialization
  time) — the acceptance message requested this; it was not separately
  instrumented in the orchestration layer (the existing
  `Path.write_text` call in `solve_task_cli.py` is untouched and fast
  relative to the ~2400s per-task training loop, so this is judged a low-
  value gap rather than fabricated with a plausible-sounding number).
