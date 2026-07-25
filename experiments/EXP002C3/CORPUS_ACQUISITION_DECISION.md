# EXP002-C3 — CORPUS_ACQUISITION_DECISION

Not a launch authorization. Per the acceptance message's execution limits
("Do not launch the full 170-test-index corpus during this task"), this
document specifies what a future, separately approved acquisition run
would use — it is a decision record, not an execution.

## Selected production configuration

**C3 as originally measured in `experiments/EXP002C2/BASELINE_SPEC.md`**:
3 CompressARC processes per T4 (6 total slots), default PyTorch threading
(no `OMP_NUM_THREADS`/etc. caps), no explicit CPU-affinity pinning, no
concurrency reduction below the measured host's GPU-validated safe level.
`RESULTS.md`'s verdict (KEEP FROZEN C3) is the reason: B1's thread caps and
B2's vCPU-derived lower concurrency both under-perform plain C3 on every
throughput metric that matters for corpus acquisition (task-count
throughput, quality-adjusted throughput), so the added orchestration
complexity (env vars, affinity maps, dynamic quota-derived concurrency)
buys nothing and should not be carried into a production acquisition
script.

## Deterministic shard plan

For a 170-test-index target (the McNemar floor), sharded into Kaggle's
12-hour competition-runtime cap:

- **Shard size**: driven by C3's measured 8.91 test-idx/hour and the
  ~1.2 test-idx/task ratio (`SCALING_PROJECTION.md`) — approximately 142
  tasks/shard would exhaust a 12h session, but a smaller shard (e.g. 40-60
  tasks, ~4-5 wall-clock hours) is recommended in practice to leave margin
  for the per-task variance already observed (steps/s ranging 0.07-0.67
  across just 5 sampled tasks) and to allow mid-acquisition inspection
  before committing further quota.
- **Task IDs per shard**: not yet assigned — requires drawing the actual
  ~140-170 test-index task sample from the ARC-AGI-2 training pool via
  `src/run002c/sample_tasks.py` (the same sampler that produced the 5-task
  pilot sample, extended to the target size), which is itself part of the
  separately-approved acquisition launch, not this pilot.
- **GPU assignment within a shard**: round-robin across the 6 available C3
  slots (3/GPU), in task-ID list order — the same deterministic pattern
  `BASELINE_SPEC.md` §3 already used for the 5-task pilot, generalized.

## Expected runtime per shard

At C3's measured 8.91 test-idx/hour and ~1.2 test-idx/task: a 50-task
shard (~60 test-indices) is expected to take approximately 6.7 wall-clock
hours (13.4 Kaggle quota GPU-hours), comfortably inside the 12h cap with
margin for per-task variance and the fixed 40-minute-per-task ceiling
already governing individual task duration.

## Exact acquisition command (not run)

```
python -m src.run002c.acquire_corpus \
    --task-sample <shard-task-list.json> \
    --concurrency-per-gpu 3 \
    --time-limit-s 2400 \
    --n-iterations 2000
```

`src/run002c/acquire_corpus.py` exists but is not yet wired to the C3
concurrency orchestration this and the prior pilot validated — building
that wiring (reusing `build_c3c4_notebook.py`'s `run_config`/
`launch_task` pattern with a task list read from a file instead of the
hardcoded 5-task pilot sample) is a prerequisite for the actual launch,
separate from this decision record.

## Checkpoint / restart procedure

Per-task JSON persistence (unchanged since EXP002-C): each task's result
is written exactly once, on completion, to its own file. A restarted
acquisition run should skip any `task_id` whose output file already
exists rather than re-running it — this is not yet implemented in
`acquire_corpus.py` and would need to be added before a multi-session
acquisition (which 170+ test-indices, spanning ~2 Kaggle sessions, will
require) can safely resume across sessions without wasting quota
re-running completed tasks.

## Artifact merge procedure

Concatenate each session's `per_task/*.json` files into a single archive
directory, keyed by `task_id` (no collision risk since each task runs
exactly once across the whole acquisition, by construction of the
checkpoint/restart rule above). No merge logic beyond union-by-filename is
needed — unlike the pilot's per-config aggregate reports, a full
acquisition's "report" is the per-task archive itself, consumed downstream
by `src/harness/` the same way RUN-001's archive already is.

## Quota estimate

170 test-indices: ~38 Kaggle quota GPU-hours, ~2 sessions (`SCALING_
PROJECTION.md`). 500 test-indices: 112-334 GPU-hours, 5-14 sessions
depending on whether the tested-optimistic or conservative bound holds at
real scale (untested beyond this project's 5-task pilot).

## Not launched

Per the acceptance message's explicit execution limits, no corpus
acquisition — of any size — is launched by this document or this pilot.
