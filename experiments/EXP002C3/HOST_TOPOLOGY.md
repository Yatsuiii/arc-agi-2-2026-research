# EXP002-C3 — HOST_TOPOLOGY

Phase 1 output. Metadata-only Kaggle probe kernel
(`redlotusthepotus/exp002c3-host-probe`, v1, status COMPLETE), no
CompressARC code, no task solving. Raw output:
`artifacts/EXP002C3/host_probe_output/host_topology_report.json`
(sha256 `93a4943ffd3e77c6e9677fd2ce3cc5e390c4c9f118f4690d5562dcae51fb6799`).

## Headline finding

**The Kaggle 2xT4 container exposes only 4 effective vCPUs total, for both
GPUs combined.** This is confirmed three independent ways, not inferred
from `os.cpu_count()` alone:

| Measurement | Value |
| --- | --- |
| `os.cpu_count()` | 4 |
| `os.sched_getaffinity(0)` | `{0,1,2,3}`, count 4 |
| `psutil.cpu_count(logical=True)` | 4 |
| `psutil.cpu_count(logical=False)` | 2 (physical cores; 4 is the hyperthread-logical count) |
| cgroup v2 `cpu.max` | `400000 100000` = 4.0 effective CPUs |
| cgroup v1 quota | not present (host uses cgroup v2) |
| `cpuset.cpus` | `0-3` |

All three independent signals (`os.cpu_count()`, `sched_getaffinity`,
`psutil`) and the cgroup v2 quota agree exactly: **Q = 4**. There is no
discrepancy between "reported" and "effective" CPU count on this host —
unlike some container platforms, Kaggle's cgroup quota is not tighter than
what `os.cpu_count()` reports.

This means **EXP002-C2's C3 (5 processes: 3 on GPU0 + 2 on GPU1) and C4 (5
processes: 4 on GPU0 + 1 on GPU1) both ran 5 concurrent CompressARC
processes on a 4-vCPU host** — genuine, measured oversubscription at the
CPU level, not merely a GPU-level design choice. This directly explains
`experiments/EXP002C2/RESOURCE_ANALYSIS.md`'s finding of 99.6-99.8% CPU
saturation: 5 processes competing for 4 cores is expected to saturate CPU
regardless of anything each process does internally.

## Thread-pool defaults

| Signal | Value |
| --- | --- |
| `OMP_NUM_THREADS` / `MKL_NUM_THREADS` / etc. (ambient env) | unset (all `None`) — Kaggle's base image does not pre-set any of these |
| `torch.get_num_threads()` (ambient env) | 2 |
| `torch.get_num_interop_threads()` (ambient env) | 2 |
| `torch.get_num_threads()` with all `*_THREADS` env vars stripped | 2 (unchanged) |
| `torch.get_num_interop_threads()` with env vars stripped | 2 (unchanged) |

**PyTorch is not reading a large ambient thread-count from the environment
and is not defaulting to something as large as `os.cpu_count()`** on this
host — it already self-limits to 2 intraop threads whether or not the
`*_THREADS` env vars are set (its own internal heuristic, roughly
`physical_cores`). This means the CPU-contention mechanism EXP002-C2's
`RESOURCE_ANALYSIS.md` hypothesized as "nested thread-pool oversubscription
inside every worker" is **only a secondary factor at best**: even at
PyTorch's already-conservative default of 2 threads/process, 5 concurrent
processes request up to 10 intraop threads against 4 physical/4 logical
cores — 2.5x oversubscribed on threads alone, before counting any
NumPy/MKL activity in `preprocessing.py`'s data prep or `scoring.py`'s
candidate scoring. **B1's thread cap (1 thread/process) is still a
meaningful, testable intervention** — it reduces the per-process thread
request from 2 to 1, which at 5 processes changes total requested threads
from 10 (2.5x over 4 cores) to 5 (1.25x over 4 cores), much closer to the
core count — but the finding reframes Q1: the dominant driver is most
likely raw process-count-vs-core-count oversubscription (5 processes, 4
cores), not runaway per-process thread pools. B1 and B2 both test this
directly.

## Multiprocessing / Python

| Signal | Value |
| --- | --- |
| Python version | 3.11.13 |
| `multiprocessing.get_start_method()` | `fork` (default; not overridden, and not needed — this project uses `subprocess.Popen`, not `multiprocessing`, per `solve_task_cli.py`'s design note) |
| PyTorch version | 2.6.0+cu124 |

## GPU topology

| Signal | Value |
| --- | --- |
| GPU count | 2 |
| GPU names | Tesla T4 x2 |
| VRAM per GPU | 14,911 MiB (~14.6 GiB) |
| CPU-GPU affinity (`nvidia-smi topo -m`) | Both GPUs report CPU affinity `0-3` (the same 4 cores) and NUMA affinity `0` — **no CPU-core partition exists between the two GPUs**. There is no way to statically assign, say, cores 0-1 to GPU0's workers and cores 2-3 to GPU1's workers based on hardware topology; the 4 cores are a single shared pool for both GPUs. |
| Interconnect | PHB (PCIe Host Bridge) between GPU0 and GPU1 |
| NUMA | single node (`numactl` not installed to probe further; `nvidia-smi topo` reports NUMA affinity 0 for both GPUs, consistent with a single-socket host) |

## Memory

| Signal | Value |
| --- | --- |
| RAM total | 32,100 MiB (~31.3 GiB) |
| RAM available at probe time | 30,859 MiB |
| Swap | 0 MiB (none configured) |
| Load average (1/5/15 min) at probe time | 0.40 / 0.32 / 0.15 (idle, as expected for a fresh kernel) |

## Consequence for BASELINE_SPEC.md §5's B2 rule

Applying the frozen rule with the measured `Q = 4`:

```
Q = 4
U = Q - 1 = 3          (reserve 1 effective CPU for orchestration/I/O)
W = clamp(floor(U/2), 1, 3) = clamp(floor(1.5), 1, 3) = clamp(1, 1, 3) = 1
```

**B2 evaluates to W = 1 worker/GPU, i.e. 2 total slots — C1-equivalent
concurrency.** This is exactly the degraded case `BASELINE_SPEC.md` §5
anticipated in its worked example ("if the realised host has, say, 4
effective CPUs, `W = clamp(floor(3/2), 1, 3) = 1`, i.e. B2 degrades to
C1-equivalent concurrency") and is not a failure of the pilot — it is the
rule doing exactly what it was designed to do: refuse to recommend
concurrency the measured host cannot actually support without CPU
starvation. B1 (still run at C3's 5-process/4-core concurrency, but with
thread caps and affinity) is therefore the more informative of the two new
configurations for Q1/Q2 on this specific host; B2's result answers Q3/Q4
directly by demonstrating that, under this project's own frozen safety
rule and this host's real resources, "3-4 processes/T4" is not a
CPU-safe concurrency level at all — it was GPU-safe (verified by EXP002-C2)
but not CPU-safe, and the two are different constraints that C3/C4's
success criteria (throughput, quality) did not surface because neither
was CPU-utilization-gated.

## What was not measured

- `numactl --hardware` output (binary not installed in the Kaggle image;
  `nvidia-smi topo -m`'s NUMA-affinity column is used instead as a
  coarser substitute).
- Per-process GPU memory via `nvidia-smi --query-compute-apps` — deferred
  to the B1/B2 run itself (`BASELINE_SPEC.md` §6), not probed here since
  no compute processes exist during a metadata-only kernel.
