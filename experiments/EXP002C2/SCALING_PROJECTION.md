# EXP002-C2 — SCALING_PROJECTION

Extrapolates C1/C3/C4's measured numbers to real acquisition targets.
Basis: **C3 (3 processes/GPU), the adopted operating point per
`RESULTS.md`'s verdict**, using the task-count/test-index throughput axis
(the metric the corpus's power requirement is actually denominated in — see
`RESULTS.md` "What the numbers actually show" for why the compute-bound
candidate-rate metric is the wrong basis for this specific projection).

## Basis numbers

| | Value | Source |
| --- | --- | --- |
| C3 test-indices/hour | 6 / 0.6737h = **8.91/hour** | `RESULTS.md` §7 |
| Kaggle quota-hours per wall-clock hour | 2 (both T4s allocated for the whole session regardless of intra-session process count) | `paper/COMPUTE_LEDGER.md` "Our available compute" |
| Test-indices per task (this 5-task sample) | 6/5 = 1.2 | `experiments/EXP002C/pilot_sample.json` — **highly uncertain**, n=5 tasks is nowhere near enough to fix this ratio for the full ~1000-task ARC-AGI-2 training pool |
| Bytes per candidate (uncompressed JSON) | 354.4 | measured directly from `artifacts/EXP002C2/pilot_kernel_output/exp002c2_pilot/per_task/C3_*.json` |
| Candidates per test-index (C3) | 1589/6 = 264.8 | `RESULTS.md` §7 |
| Observed failure rate | 0/10 task-processes (C3+C4 combined) | `RESULTS.md` §10-11 |

## Projections

| Target | Wall-clock hours | Kaggle sessions (12h cap) | Kaggle quota GPU-hours | Estimated storage | Estimated candidates | Failure/retry allowance |
| --- | --- | --- | --- | --- | --- | --- |
| 100 test-indices | 11.2 | 1 | 22.4 | ~9.5 MB | ~26,480 | +10-15% wall-clock margin recommended |
| 140 test-indices (McNemar floor, see below) | 15.7 | 2 | 31.4 | ~13.3 MB | ~37,072 | same |
| 250 test-indices | 28.1 | 3 | 56.2 | ~23.8 MB | ~66,200 | same |
| 500 test-indices (preregistered conservative target) | 56.2 | 5 | 112.3 | ~47.6 MB | ~132,400 | same |

**Uncertainty range.** Using C1's own measured rate (2.99 test-idx/hour, no
oversubscription) as the conservative bound and C3/C4's rates (~8.9/hour)
as the tested-optimistic bound, the 500-test-index target spans roughly
**56-167 wall-clock hours** (112-334 Kaggle quota GPU-hours) depending on
how much of the projected gain holds at real scale — this pilot measured 5
tasks, not 500, and `RESOURCE_ANALYSIS.md`'s CPU-saturation finding means
the *shape* of the throughput curve past 4x/GPU is genuinely unknown (this
experiment was capped at 4 processes/GPU by explicit instruction and did
not probe further).

The **retry/failure allowance is a recommendation, not a measurement**: 0/10
task-processes failed in this pilot, but n=10 cannot establish a low failure
rate with any confidence at 100-500-task scale, where a more diverse task
population will exercise edge cases (unusual grid shapes, colour counts,
memory outliers like `42f83767`) this 5-task sample could not. Budgeting
10-15% extra wall-clock as a retry margin is a standard engineering
allowance, not a number derived from this pilot's data.

## Comparison against the pre-oversubscription estimate

`experiments/EXP002C/PILOT_RESULTS.md` §5-6 estimated the 500-test-index
target at 454-675 serial GPU-hours (1 process/GPU, no oversubscription).
This projection's tested-optimistic figure (112 Kaggle quota GPU-hours)
is roughly **4-6x cheaper**, and even the conservative bound of this
projection's own uncertainty range (334 GPU-hours) is somewhat cheaper than
the earlier estimate's midpoint. Oversubscription is a real, usable lever
for the acquisition cost problem `experiments/EXP002C/PLAN.md` §16 and
`experiments/EXP002C/PILOT_RESULTS.md`'s verdict identified.

## Minimum statistically powered corpus

`experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s McNemar-based planning gave
**170-500 test-indices**, with 500 (the top of the range) chosen there as
the conservative target and 170 as the acceptable, still-justified floor —
not an arbitrary smaller number chosen for cost reasons, but the
pre-registered lower bound of the same power calculation.

**170 test-indices is the smallest corpus that satisfies the preregistered
power requirement without revising that requirement.** At C3's measured
rate: 170/8.91 = 19.1 wall-clock hours, 38.1 Kaggle quota GPU-hours, ~2
Kaggle sessions — a small, clearly payable fraction of the project's
remaining ~100-day / multi-week compute budget
(`paper/COMPUTE_LEDGER.md` "Calendar" / "Budgeting principle"), even before
considering the uncertainty range above.

**Do not select a corpus smaller than 170 test-indices merely because it is
cheaper still** — that would revise `CORPUS_REQUIREMENTS.md`'s power
analysis after the fact rather than execute it, exactly the anti-pattern
this project's preregistration discipline exists to prevent.

## Recommendation

The 500-test-index target (`CORPUS_REQUIREMENTS.md`'s conservative choice)
is now feasible within the tested-optimistic bound (112 GPU-hours, ~5
Kaggle sessions, ~3.7 weeks of quota) and remains feasible even at this
projection's conservative bound (334 GPU-hours, ~14 sessions, ~11 weeks) —
tight against the ~100-day project runway but not implausible, especially
once addressed by (a) the CPU-bottleneck follow-up
`RESOURCE_ANALYSIS.md` identifies as a further optimisation opportunity, or
(b) targeting 170-250 test-indices first, which is unambiguously payable
inside 1-3 weeks and re-evaluating whether more is needed once real V0-V3
results exist. **Not launched by this pass** — the acceptance message's
execution limits explicitly exclude "launch the full corpus" from this
pilot's scope; this is the projection that a future, separately approved
acquisition run would use.
