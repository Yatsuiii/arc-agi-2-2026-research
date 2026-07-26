# ACQ-001 — BASELINE_SPEC

The frozen production configuration this acquisition runs under. Nothing
here is decided by this task — it restates the verdict of
`experiments/EXP002C2/RESULTS.md` (adopt C3) and
`experiments/EXP002C3/RESULTS.md` (KEEP FROZEN C3, no further
CPU-orchestration tuning), so that ACQ-001's own docs are self-contained.

## Configuration

| Parameter | Value | Source |
| --- | --- | --- |
| Concurrency | 3 CompressARC processes per T4, 6 total slots on 2xT4 | EXP002-C2 |
| CPU thread controls | None — plain library thread defaults, no `OMP_NUM_THREADS` cap, no affinity pinning | EXP002-C3 (B1 showed no measurable gain) |
| Per-task timeout | 2400s (40 min) | EXP002-C/C2/C3, unrevised |
| Training iterations | 2000 | EXP002-C/C2/C3, unrevised |
| Solver | CompressARC, vendored + grid-persistence instrumentation, unchanged since EXP002-C | `third_party/compressarc/` |
| Wave construction | Deterministic: first 3 task IDs (in the shard's own frozen order) to `cuda:0`, next 3 to `cuda:1`, repeat | `src/run002c/acquire_shard.py:build_waves` |
| Retry policy | 1 retry (`MAX_ATTEMPTS=2`) for a nonzero-exit crash, on the next wave, never immediately; OOM never retried | `src/run002c/acquire_shard.py` |
| Abort policy | Stall-abort if any process is 20+ min past its own deadline; RAM-abort if system RAM >95%; either stops the entire remaining shard, not just the current wave | Reused from EXP002-C2/C3 |

## What this task did not change

No parameter in this table was touched by ACQ-001. This task built the
orchestration layer around the frozen configuration (checkpointing,
retries, archiving) and used it to acquire real corpus data; it performed
no new concurrency, thread-affinity, or scheduling experiment. Per the
explicit acceptance instruction: "Do not perform further CPU-thread,
affinity, concurrency, C4, or orchestration micro-optimization."

## Expected behaviour, confirmed by Shard A

Every prior pilot (EXP002-C/C2/C3, this task's own Phase 3 validation) found
CompressARC never converges early under this timeout — every task hits the
2400s time guard. Shard A confirms this at full scale: **80/80 tasks
hit_time_guard=1**, wall-clock 2410-2425s per task, matching the 2410-2425s
range measured in every earlier pilot on the one task (`00576224`) common
to all of them.
