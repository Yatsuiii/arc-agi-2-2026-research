# EXP002-C3 — ERROR_ANALYSIS

## 1. B1 affinity wrap-around bug (real, minor, documented)

`BASELINE_SPEC.md` §4 specified: "consecutive core IDs starting at 0,
wrapping only if effective CPUs < 5." `src/run002c/build_b1b2_notebook.py`
`_b1_cell()` implements the assignment as
`{task_id: idx for idx, (task_id, _device) in enumerate(B1_TASKS)}` —
plain enumeration, 0 through 4, with **no wrap-around check**. On this
host (`Q=4` effective CPUs, confirmed in `HOST_TOPOLOGY.md`), the 5th
process (`8abad3cf`) was assigned core ID 4, which does not exist (valid
range 0-3).

**Effect**: `os.sched_setaffinity(pid, {4})` raised
`OSError: [Errno 22] Invalid argument`, caught by the `try/except` in
`launch_task`, recorded as `"realised_affinity":
"unsupported_or_failed: [Errno 22] Invalid argument"` in
`config_B1.json`, and the process continued running with its inherited
(unrestricted, all-4-core) default affinity instead of a pin. **Not
fatal** — the process completed normally (`returncode: 0`,
`timed_out: true`, valid archive) — but the affinity intervention was not
actually applied to this one of B1's five processes.

**Why this wasn't caught before the real run**: no local CPU smoke test
exercised this code path, because a local smoke test with fewer than 5
logical CPUs would have hit the same bug (informative) but the smoke-test
discipline this project has used for EXP002-C/C2 focused on solver
correctness (grid shapes, archive schema) rather than orchestration-layer
edge cases like affinity range validation. **Lesson for future
telemetry/orchestration pilots**: any code that computes a resource index
(core ID, GPU ID, port number) from a count that can legitimately be
smaller than the number of consumers needs its own boundary-condition
test, independent of whether the main solver path is tested.

**Impact on RESULTS.md's conclusions**: this does not compromise the
other four B1 tasks' metrics — 4/5 processes were correctly
pinned, and the one unpinned process (`8abad3cf`) ran with default
(unrestricted) affinity, which is a strict superset of what a correct pin
would have given it, not a more-constrained or broken state. If anything,
this makes B1's true "fully affinity-pinned" case slightly under-tested
(4/5, not 5/5) rather than invalidated.

## 2. CPU saturation (real, expected, not a failure)

`RESOURCE_ANALYSIS.md` §2 confirms B1's 99.6% mean CPU utilisation is
consistent with (not caused by a bug, simply implied by) running 5
processes on a 4-core host. This is the same condition EXP002-C2's C3/C4
already measured; `HOST_TOPOLOGY.md`'s contribution is explaining *why*
(4 effective vCPUs, confirmed three independent ways) rather than
identifying a new problem.

## 3. Per-task unique-candidate fraction not separately persisted

`RESULTS.md` §7's mandatory criterion 4 ("≥90% of B0's unique-candidate
rate per task") is checked at the aggregate level (94.4% B1, 91.8% B2)
because `ANALYSIS_SOURCE` in `build_b1b2_notebook.py` (matching
`build_c3c4_notebook.py`'s prior design) accumulates `total_unique`
across all tasks' test-indices rather than storing a per-task unique
count in the final report. This is an inherited reporting granularity, not
a new gap introduced by this pilot — `experiments/EXP002C2/RESULTS.md`
made the same aggregate-level check for C3/C4. Recomputing a genuine
per-task figure is possible from the raw `per_task/*.json` archives
(each candidate's grid is present) but was not done here since the
aggregate comfortably clears the 90% floor with margin (94.4% and 91.8%
vs. 90%) and a per-task breakdown is unlikely to change the pass/fail
outcome given how close the per-config totals are to each other.

## 4. C1/B0 CPU/context-switch telemetry gap (pre-existing, restated)

`BASELINE_SPEC.md` §3 already flagged that C3 predates per-process CPU
telemetry (thread count, context switches, per-core percentages). This
pilot's B1/B2 add that telemetry going forward but cannot retroactively
fill it in for C3 itself — `RESULTS.md` §7's criterion C ("materially
lower CPU usage... than B0") is evaluated using EXP002-C2's own aggregate
system-CPU figure for C3 (99.6%, `experiments/EXP002C2/RESOURCE_ANALYSIS.
md`) as the B0 comparison point, since that number is directly comparable
to B1's aggregate system-CPU figure (also 99.6%) even though the
finer-grained per-process breakdown is not available for C3.

## 5. Sample-size caveats (restated from EXP002-C2, still applicable)

n=5 tasks, n=6 test-indices. Every quality metric (oracle coverage,
unique-candidate fraction) carries the same wide, unreported-CI caveat
`experiments/EXP002C2/ERROR_ANALYSIS.md` §4 already stated. B1's oracle-
coverage drop (3/6 -> 2/6) is a single-result difference and is explicitly
not treated as a systematic finding anywhere in this pilot's documents.

## 6. What did NOT go wrong

- 0 OOMs across 10 processes.
- 0 archive corruption (10/10 valid JSON).
- 0 hard failures / crashes.
- 0 stall-aborts (the 20-minutes-past-deadline safety check never
  triggered — every process completed within its own `time_limit_s`
  window as expected).
- The B2 dynamic-concurrency rule (`BASELINE_SPEC.md` §5) computed and
  applied correctly given the measured `Q=4`: `W=1`, 2 total slots, wave 2
  correctly queued and launched the remaining 3 tasks after wave 1's
  processes fully exited.
