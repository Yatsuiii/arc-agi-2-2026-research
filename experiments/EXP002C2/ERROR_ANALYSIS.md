# EXP002-C2 — ERROR_ANALYSIS

Two distinct findings this pass produced that are errors/inefficiencies in
a meaningful sense, kept separate because one is a bug in this pilot's own
code and the other is a real property of the system under test.

## 1. v1's false-positive stall abort (orchestration bug, fixed)

**What happened.** `redlotusthepotus/exp002c2-oversubscription-pilot` v1
killed every process in both C3 and C4 at exactly 1200s, reporting
`abort_reason: "no task progress for 20 minutes"` for all 10 processes.

**Root cause.** `run_config`'s stall check used `out_path.exists()` /
`out_path.stat().st_size` as a progress signal, where `out_path` is
`solve_task_cli.py`'s final result file. That file is written exactly once,
via `args.out.write_text(json.dumps(result))`, after the training loop
returns — never incrementally during training. A task that is training
normally therefore looks byte-for-byte identical, from this check's point
of view, to a task that has hung: neither has written anything to
`out_path` yet. The check's 20-minute grace window (`(time.time() -
config_start) > 1200`) simply measured how long it took for this
always-false "progress" signal to trip the abort, not anything about the
tasks themselves.

**Why it wasn't caught before pushing.** The local CPU smoke test
(`experiments/EXP002C2/PLAN.md`'s companion verification, same discipline
as `experiments/EXP002C/PILOT_RESULTS.md`'s own pre-push checks) used
`n_iterations=3` and `TIME_LIMIT_S=60`, deliberately short so the test
finishes in seconds. At that scale, every task completes and writes
`out_path` well before any stall check could plausibly fire, so the smoke
test never exercised the code path where a task is still running when a
periodic abort check runs — a real gap in the smoke test's coverage,
distinct from the bug itself.

**Cost.** ~3.33 GPU-hours (10 processes x 1200s wall-clock, both
configurations) spent with zero usable throughput data. Preserved for the
record at `artifacts/EXP002C2/pilot_kernel_output_v1_false_abort/` rather
than discarded — the GPU-utilisation telemetry from that window (GPU0 at
99-100% under 3x concurrency) corroborates v2's real measurement, so the
spend was not entirely wasted even though its primary purpose (throughput
data) was lost.

**Fix.** Replaced the file-existence check with a genuine stall condition:
a process still alive more than `time_limit_s + 1200` seconds after config
start (20 minutes past when it should have already self-terminated at its
own deadline, which `solve_task_cli.py` checks once per training step).
Re-verified locally before re-pushing (`experiments/EXP002C2/RESULTS.md`
§0), and confirmed working in v2 (`aborted: false` for both configurations,
matching the expectation that no process should stall within a 2400s
window it self-enforces).

**Lesson for future telemetry-heavy pilots in this project**: a "progress"
signal must be independently verified to actually change during a normal,
successful run — not just assumed to, from reading the code that writes
it — before it is trusted as an abort trigger. This is exactly the kind of
check a smoke test at unrealistically short durations can fail to surface.

## 2. Host CPU saturation (real finding, not a bug)

**What happened.** System-wide CPU utilisation measured ~99.6-99.8% mean
throughout both C3 and C4 (`experiments/EXP002C2/RESOURCE_ANALYSIS.md`),
while GPU0 utilisation reached only 88.0% (C3) and 97.7% (C4) — the host
CPU was the more fully saturated resource, not the GPU.

**Consequence measured**: the compute-bound throughput metric (candidates
or unique candidates per minute) scaled sub-linearly with concurrency
(1.39x at 3x concurrency, 1.38x at 4x) even though the task-count/test-index
throughput metric scaled linearly (2.98x, 2.99x) — because CPU contention
limits how much *training depth* each concurrent task receives within the
fixed time cap, not how many tasks can be started concurrently.

**Not classified as a failure or a blocker** (`RESULTS.md`'s verdict
reasoning): the corpus's power requirement is denominated in test-index
count, and the two quality checks sensitive to reduced per-task depth
(candidate oracle coverage, unique-candidate fraction) did not degrade
outside this pilot's own noise band. Recorded here as a diagnosed, specific,
and — per the CPU-vs-GPU utilisation gap — plausibly correctable
inefficiency worth a dedicated follow-up, not as an error that occurred
during this pilot's execution.

**What is not yet known** (also in `RESOURCE_ANALYSIS.md`): the host's
actual vCPU count was not logged, so whether the ceiling is "too many
processes for a small core count" (a scheduling fix: cap concurrency at
vCPU count) or "genuine per-step Python overhead in the postprocessing
path" (a code fix: reduce or batch that overhead) is not yet distinguished.

## 3. C4's tested load was asymmetric, not the nominal 4+4

By `experiments/EXP002C2/PLAN.md`/`BASELINE_SPEC.md`'s own design (5 tasks
split 4+1 for C4, to isolate the known outlier task `42f83767` on an
uncontended GPU1 slot), C4 never tested a symmetric 4-processes-on-each-GPU
load — only a genuine 4x load on GPU0, alongside a near-idle GPU1. This was
a deliberate, disclosed design choice
(`BASELINE_SPEC.md` §3's reasoning), not an oversight discovered after the
fact, but it means C4's measured numbers characterise "4x on one GPU while
the other GPU is quiet," not "both GPUs simultaneously at 4x" — relevant to
`SCALING_PROJECTION.md`'s uncertainty range and to why `RESULTS.md`
recommends adopting C3 (closer to its own nominal 6-slot capacity at 5/6)
rather than C4 as the next operating point.

## 4. Sample-size caveats carried forward, not re-derived

n=5 tasks / 6 test-indices is the same corpus EXP002-C used, with the same
limitations `PILOT_RESULTS.md` already stated in full (no bootstrap CIs
computed, oracle-coverage and diversity comparisons are point estimates
only). Not repeated in full here; `RESULTS.md` §8 cross-references rather
than restates.
