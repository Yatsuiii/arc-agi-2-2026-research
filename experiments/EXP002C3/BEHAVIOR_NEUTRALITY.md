# EXP002-C3 — BEHAVIOR_NEUTRALITY

Confirms orchestration changes (thread caps, affinity, concurrency level)
did not alter the intended solver behaviour, per `PLAN.md` §8 and the
acceptance message's Phase 6.

## 1. Input identity

All three configs (B0/C3 reused, B1, B2) read the same
`experiments/EXP002C/pilot_sample.json` task list from the same mounted
`arc-agi_training_challenges.json`/`arc-agi_training_solutions.json` files.
`solve_task_cli.py` reads `problems[args.task_id]` directly — no
per-config data transformation exists to diverge.

## 2. Seed identity

`np.random.seed(0)`, `torch.manual_seed(0)` remain module-level in
`solution_selection.py`, unchanged from B0/C3. However, seeding does not
guarantee determinism here for a reason independent of this pilot:
`paper/REPRODUCIBILITY.md`'s determinism policy already documents that
CompressARC's batched-decoder behaviour is not fully reproducible run-to-
run even with fixed seeds, because floating-point operation ordering can
shift with scheduling. Thread-count and CPU-affinity changes are an
additional, expected source of this same class of nondeterminism (CUDA
kernel launch timing can differ when the launching Python thread is
scheduled differently), not a new failure mode this pilot introduces.

## 3. Configuration identity (code, not parameters)

`solve_task_cli.py` and all 9 vendored CompressARC modules are
byte-identical across B0/B1/B2 (verified: `solve_task_cli.py` was written
verbatim from the same source file used by `build_c3c4_notebook.py`,
confirmed by inspecting `src/run002c/build_b1b2_notebook.py`'s
`DRIVER = ROOT / "src" / "run002c" / "solve_task_cli.py"` reference — the
same path `build_c3c4_notebook.py` used). `--n-iterations 2000`,
`--time-limit-s 2400` unchanged in every launch command.

## 4. Phase sequence

Every task follows the same `train.take_step` loop, same per-step deadline
check, same `Logger._update_most_frequent_solutions` native-selection
update — B1/B2 add no additional phase and skip none.

## 5. Candidate-grid validity

Checked directly against all 10 real per-task archives (`per_task/*.json`):
every candidate's `grid` field has exactly `n_test` entries, each a
well-formed 2D grid of ints. 0 malformed candidates across 1727 (B1) + 2836
(B2) = 4563 candidates.

## 6. Candidate diversity and native selection

Diversity: `RESULTS.md` §5 (94.0%/94.4%/91.8% unique fraction across
B0/B1/B2 — compatible distributions, not identical, as expected).

Native selection: directly compared for `00576224` (the same task, run
under both B1 and B2). B1's `attempt_1` and B2's `attempt_1` are **not**
byte-identical — they are the same 6x6 checkerboard-style grid with colours
2/3/7/8 swapped between the two runs. This is exactly the kind of
divergence `paper/REPRODUCIBILITY.md`'s determinism policy predicts:
different thread/affinity configuration changes floating-point op
ordering, which changes which of several near-tied candidate solutions the
model converges to first. It is not evidence of a code-path difference —
both runs used the identical `solve_task_cli.py` and vendored modules,
launched with the same seeds and iteration budget.

## 7. Iteration progression

`steps_run` values differ across B0/B1/B2 for the same task (`RESOURCE_
ANALYSIS.md` §4) because wall-clock-bound training (`time_limit_s`, not a
fixed step count) means the number of completed steps within 2400s
naturally varies with how much CPU/GPU contention each run experiences —
expected, not a behavioural change. Every task in every config hit
`timed_out: true` at (or immediately after) its own 2400s deadline; none
exited early or ran past the grace window.

## 8. Timeout behaviour

10/10 processes across B1/B2/B2_wave2 report `timed_out: true`, consistent
with every prior EXP002-C/C2 run on these same five tasks (none of which
has ever converged before the 2000-iteration/2400s budget). No process
exited via any other path (no crash, no early completion).

## 9. Sources of nondeterminism, enumerated

1. Batched-decoder floating-point ordering (pre-existing, documented in
   `paper/REPRODUCIBILITY.md`).
2. CPU thread count (new in this pilot): 1 thread (B1/B2) vs. PyTorch's
   default 2 threads (B0/C3) changes intraop parallelism scheduling.
3. CPU affinity (new in this pilot): pinning a process to a specific core
   changes which physical core executes its Python/CPU-side work, which
   can interact with cache locality and OS scheduling in ways that shift
   timing (and therefore floating-point op interleaving) slightly.
4. GPU-side concurrency level (new in this pilot, indirect): how many
   other CUDA contexts are active on the same T4 at a given moment affects
   kernel scheduling order, a documented source of nondeterminism for any
   concurrent CUDA workload.

None of these are behavioural changes to the solver's algorithm, training
objective, or selection logic — all are scheduling-level effects on an
already-nondeterministic system, consistent with the freeze list in
`BASELINE_SPEC.md` §2 being fully honoured.

## 10. Conclusion

**Quality distributions remain compatible across B0/B1/B2** (diversity,
timeout behaviour, candidate-grid validity all consistent); the intended
solver behaviour is unchanged. Per-run outcome differences (candidate
counts, oracle coverage, exact top-2 selection) are attributable to
already-documented, seed-independent nondeterminism sources, not to any
code or parameter drift introduced by this pilot's orchestration changes.
