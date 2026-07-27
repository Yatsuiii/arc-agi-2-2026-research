# EXPERIMENT_REGISTRY

Every experiment in this project appears here, before it runs and after it
finishes. A failed hypothesis stays in this file with its original text intact.
We do not rewrite history to make the final approach look inevitable.

## Rules

1. An experiment may not run until its `PLAN.md` exists under
   `experiments/<ID>/` and is committed. The commit SHA of that preregistration
   is what makes it a preregistration.
2. The plan is never edited after the run. Deviations go in `RESULT.md` under
   "deviations from plan", with the reason.
3. Results are recorded whether they support the hypothesis or not.
4. An experiment that hits its kill criterion is marked `KILLED` and stays
   listed. The kill is a finding.

## Preregistration template

Copy into `experiments/<ID>/PLAN.md`. All sixteen fields are mandatory; "not
applicable" is an acceptable value but silence is not.

```
1.  Experiment identifier
2.  Research question
3.  Falsifiable hypothesis
4.  Theoretical motivation
5.  Relationship to prior work
6.  Exact baseline
7.  Exact intervention
8.  Training split
9.  Validation split
10. Held-out evaluation split
11. Leakage risks
12. Compute budget
13. Success criterion
14. Kill criterion
15. Intended paper claim
16. Possible negative interpretation
```

## Result template

Copy into `experiments/<ID>/RESULT.md`.

```
1.  Commit SHA (of the code that ran)
2.  Exact configuration
3.  Exact command
4.  Random seeds
5.  Runtime
6.  Hardware
7.  Results
8.  Confidence intervals
9.  Per-task breakdown (path to artifact)
10. Failure categories (per paper/FAILURE_TAXONOMY.md)
11. Claims supported / weakened / rejected (cross-ref paper/CLAIM_LEDGER.md)
12. Artifact paths
13. Candidate table or figure (cross-ref paper/FIGURE_REGISTRY.md)
14. Follow-up justified by the evidence
15. Deviations from plan, and why
```

## Registry

| ID | Title | Status | Preregistration SHA | Result | Claims touched |
| --- | --- | --- | --- | --- | --- |
| EXP001-A | Selection and compute headroom from CompressARC recorded traces (ARC-AGI-1) | **COMPLETE** | `9230ca9` | `experiments/EXP001/RESULT.md` | C2 supported, C3 supported, B5 strengthened |
| EXP001-B | Same analysis on ARC-AGI-2 candidate records | **READY** (RUN-001 archive available; preview: 7.4pp headroom on 94 test-inputs) | `9230ca9` | pending | C1, C2, C3 |
| RUN-001 | NVARC T4x2 baseline execution and candidate archive | **COMPLETE (TIMED_OUT, partial)** | `131eba8` | `experiments/RUN001/RESULTS.md` | none - acquisition only |
| EXP002 | Model-independent candidate verification feasibility (thesis T2's decisive experiment) | **COMPLETE — verdict REDESIGN** | `c8f08a4` | `experiments/EXP002/RESULTS.md` | C2 (extended, not confirmed) |
| EXP002-B | Score-independent verification + confidence repair (redesign of EXP002) | **COMPLETE — verdict REDESIGN (acquisition-bound, not rejected)** | see `experiments/EXP002B/PLAN.md` commit | `experiments/EXP002B/RESULTS.md` | C2 (still not confirmed; confidence-validity sub-claim supported) |
| EXP002-C | Clean ARC-AGI-2 candidate-corpus acquisition using CompressARC (bounded 5-task smoke pilot) | **COMPLETE — verdict PARALLELISE AND SCALE** | see `experiments/EXP002C/PLAN.md` commit | `experiments/EXP002C/PILOT_RESULTS.md` | none yet - acquisition feasibility only, feeds EXP002-D |
| EXP002-C2 | CompressARC oversubscription and throughput pilot (C3/C4 vs. frozen C1 baseline) | **COMPLETE — verdict PARALLELISE AND SCALE (adopt C3)** | `93ed8a0` | `experiments/EXP002C2/RESULTS.md` | none yet - acquisition-throughput engineering, feeds EXP002-D |
| EXP002-C3 | vCPU-aware CompressARC throughput pilot (B1 thread-capped, B2 vCPU-derived concurrency, vs. frozen C3) | **COMPLETE — verdict KEEP FROZEN C3** | `441e9b6` | `experiments/EXP002C3/RESULTS.md` | none yet - acquisition-throughput engineering, feeds EXP002-D |
| EXP002-D | Powered clean-corpus verifier evaluation: V0-V6 over ACQ-001's 171-index corpus, task-grouped 5-fold CV | **COMPLETE — verdict FREEZE VERIFIER RESEARCH; GENERATION IS THE DOMINANT BOTTLENECK** | `21ccd59` | `experiments/EXP002D/RESULTS.md` | C2 (negative result: no tested verifier recovered any of the 11.1pp oracle gap; every non-trivial track underperformed the frozen native baseline, most significantly) |

Status values: `PREREGISTERED`, `RUNNING`, `COMPLETE`, `KILLED`, `ABANDONED`
(with reason).

## Runs that are not experiments

RUN-001 is registered here for provenance but is **dataset acquisition plus a
competition-baseline capture**, not a hypothesis test. It supports no claim on
its own. Its purpose is to produce the candidate archive that EXP001-B needs,
and its accuracy number is contaminated by construction because the checkpoint
was trained on the split it scores (`docs/systems/NVARC.md` §9).

ACQ-001 is likewise dataset acquisition, not a hypothesis test — it supports
no claim on its own. Frozen TRAIN/DEV/TEST folds and a 171-index TEST corpus
(`experiments/ACQ001/SPLIT_MANIFEST.md`), production driver built and
validated (`experiments/ACQ001/VALIDATION_GATE.md`, PASS), both shards
acquired under the identical frozen C3 configuration and verified
byte-for-byte identical to each other's executed code before Shard B's
launch: Shard A (80 tasks/85 test-indices,
`experiments/ACQ001/SHARD_A_RESULTS.md`) and Shard B (80 tasks/86
test-indices, `experiments/ACQ001/SHARD_B_RESULTS.md`), both COMPLETE,
160/160 tasks, 0 failures, 73,489 combined archive records, 0 leakage across
TRAIN/DEV/TEST, disjoint task-ID sets whose union matches the frozen
160-task/171-test-index TEST corpus exactly
(`experiments/ACQ001/FINAL_CORPUS_REPORT.md`). **This is the clean,
non-contaminated 171-index corpus EXP001-B/C2 need — corpus acquisition is
now COMPLETE.** No verifier training, MODEL-001, or RUN-002 work has begun;
those remain separate, not-yet-started tasks.

## EXP002: preregistered before RUN-001 landed, executed after

EXP002's plan (`experiments/EXP002/PLAN.md`) was committed at `c8f08a4` while
RUN-001 was still `RUNNING`, so the design could not be tuned after the fact
to whatever the archive turned out to contain. It executed once RUN-001
reached `TIMED_OUT` (a terminal, usable state,
`experiments/RUN001/RESULTS.md`) and `src/run001/validate_outputs.validate`
reported zero hard problems (`experiments/RUN001/VALIDATION_REPORT.md`).
Result: `experiments/EXP002/RESULTS.md`, verdict **REDESIGN** — a
model-independent feature (`reconstructed_score_kgmon` and relatives) clears
the preregistered H1 signal threshold (AUC up to 0.88), but no reranking
built from it beats the frozen NVARC selector on held-out tasks (H2), and the
held-out fold is small enough (18 test-indices) that the honest read is
"redesign the combiner and retest on more data," not "the thesis is dead."
Full reasoning in `RESULTS.md`'s verdict section.

The harness built to run it (`src/harness/`) is deliberately scoped past
EXP002's own needs: it also defines the allocator interfaces
(`src/harness/allocator/`) that later experiments (EXP003+) will exercise,
per `experiments/EXP002/PLAN.md`'s note that this is thesis T2's decisive
experiment within a larger, gated roadmap. Only `AllocationAction.STOP` has
an executor (`src/harness/allocator/actions.py`); no allocator policy has
been evaluated by any experiment, consistent with Gate 1 not yet having
passed.

## EXP002-B: the user-directed redesign, same corpus, four fixes

Accepted EXP002's REDESIGN verdict and specified the redesign directly
(`experiments/EXP002B/PLAN.md`): (1) fix a confidence bug EXP002's own error
analysis found — singleton candidate sets always reported `probability_correct
= 1.0` regardless of correctness, measured as a 77.8% false-confidence rate
at the p>=0.8 threshold before the fix, undefined/absent after; (2) enforce
score-independence by name (`src/harness/features/independence.py`) rather
than by convention, since EXP002's strongest "independent" features turned
out to be reconstructions of NVARC's own selector; (3) define four verifier
tracks (V0 frozen, V1 native-score control, V2 strict-independent, V3 hybrid)
so a pipeline-reproduction check (V1) is never confused with the actual
hypothesis (V2); (4) recommend, but not execute, a clean-corpus acquisition
plan (`experiments/EXP002B/CORPUS_REQUIREMENTS.md`) with a McNemar-based
minimum sample size (>=500 test-indices, >=100 in the held-out fold) derived
from RUN-001's own measured V0/V2 disagreement rate.

Result: `experiments/EXP002B/RESULTS.md`. The confidence fix is a completed,
measured contribution. The verification question (H1/H2) remains REDESIGN,
but the redesign this pass converges on is "acquire more data" — every
V0-vs-V2 bootstrap CI at n=18/n=94 overlaps every other, which is a
quantitatively different (and more conclusive) statement than EXP002's
qualitative small-sample caveat. Not REJECT: the data cannot show V2 fails
any more than it can show V2 succeeds.

## EXP002-C: acquisition, preregistered, gated before the GPU run itself

Executes `experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s recommendation:
CompressARC, vendored into `third_party/compressarc/` under its MIT licence
and instrumented to persist full candidate grids (not just hashes, closing
that document's option-A gap), run against ARC-AGI-2's training split. This
pass preregistered the plan (`experiments/EXP002C/PLAN.md`), vendored and
instrumented the solver, wrote the acquisition driver
(`src/run002c/{solve_task_cli,sample_tasks,acquire_corpus}.py`), and verified
feasibility (`experiments/EXP002C/FEASIBILITY.md`): a local GPU exists (RTX
4050 Laptop, 6 GB, previously "not verified" in `paper/COMPUTE_LEDGER.md`),
but `torch`/CUDA are not installed locally, and the preregistered
500-test-index target was estimated at ~210-290 GPU-hours before any
measurement existed.

The user then approved a bounded, explicitly scoped 5-task smoke pilot on
Kaggle 2xT4 (not the full acquisition). Result:
`experiments/EXP002C/PILOT_RESULTS.md`. Real measurement revised the cost
estimate **upward**: every task hit a 40-minute safety cap before completing
2000 iterations, and extrapolated full-length per-task cost puts the 500-task
target at 454-675 serial GPU-hours, not 210-290. But the same pilot measured
~26-28% mean GPU utilisation and sub-2GB VRAM per task on 16GB T4s, plus
clean, interference-free concurrent execution across both GPUs — direct
evidence of a large, untested oversubscription opportunity (matching why
CompressARC's own upstream `parallel_train.py` schedules many puzzles per
GPU). Verdict: **PARALLELISE AND SCALE**, with a smaller-corpus fallback
(~140 tasks, ~170 test-indices, the pre-registered floor of
`CORPUS_REQUIREMENTS.md`'s McNemar range) already justified if a follow-on
oversubscription pilot does not pay off. No further acquisition was
launched; the next experiment (an oversubscribed-parallelism pilot) is
specified but not started, per explicit instruction.

## EXP002-C2: the oversubscription pilot, executed

Executes exactly the follow-up `experiments/EXP002C/PILOT_RESULTS.md`
specified: C1 (1 process/GPU) reused unchanged from that pilot, C3 (3
processes/GPU) and C4 (4 processes/GPU) newly run against the identical
5-task sample, same frozen solver
(`experiments/EXP002C2/{PLAN,BASELINE_SPEC}.md`).

A first kernel version (v1) had a false-positive stall-detection bug (its
progress check read a file `solve_task_cli.py` only writes once, at the
end, so "no output yet" was indistinguishable from "stalled") that killed
every process at exactly 20 minutes, burning ~3.33 GPU-hours before the fix
was found and re-pushed as v2 — full account in
`experiments/EXP002C2/ERROR_ANALYSIS.md`.

v2's real measurement: task-count/test-index throughput scales ~linearly
with concurrency (C3 2.98x, C4 2.99x over C1, both clearing the
preregistered 1.75x threshold), because wave duration stays fixed at the
2400s cap regardless of concurrency — an empirically observed fact, not an
assumption. A second, compute-bound metric (candidates/minute) scales only
~1.4x, explained by measured host CPU saturation (~99.6-99.8%, exceeding
GPU0's own 88.0-97.7%) limiting per-task training depth, not task breadth.
Candidate diversity (93.5-94.0% unique fraction) and oracle coverage
(33-50% on n=6, within noise) held steady across every configuration — the
throughput gain did not cost measurable quality. Verdict: **PARALLELISE AND
SCALE**, adopting C3 (not C4, which was only tested asymmetrically) as the
next operating point. Full numbers: `experiments/EXP002C2/RESULTS.md`,
`RESOURCE_ANALYSIS.md`, `SCALING_PROJECTION.md`.

`experiments/EXP002C2/SCALING_PROJECTION.md` revises the acquisition cost
downward: the preregistered 500-test-index target now projects to
112-334 Kaggle quota GPU-hours (vs. the pre-oversubscription 454-675 serial
GPU-hour estimate), and the pre-registered power-requirement floor (170
test-indices, `CORPUS_REQUIREMENTS.md`) is payable in ~38 GPU-hours / 2
sessions. No further acquisition was launched, per the explicit execution
limits this pass operated under.

## EXP002-C3: the vCPU-aware throughput pilot, executed — null result

Follows directly from EXP002-C2's open question: why did ~3x task-count
throughput produce only ~1.4x candidate throughput? A Phase 1 metadata-only
Kaggle probe (`experiments/EXP002C3/HOST_TOPOLOGY.md`) measured the answer's
precondition directly: the 2xT4 container exposes only **4 effective
vCPUs total, shared across both GPUs with no CPU-core partition between
them** (confirmed three independent ways plus the cgroup v2 quota, all in
exact agreement) — meaning EXP002-C2's C3/C4 ran 5 concurrent processes on
4 cores, real oversubscription. PyTorch was also found to already
self-limit to 2 intraop threads per process by default on this host,
independent of any `*_THREADS` environment variable, narrowing the
plausible explanation before any GPU run.

Two new configurations tested this directly, both reusing the byte-
identical solver path (zero lines of `solve_task_cli.py` or any vendored
CompressARC module changed — only subprocess environment, CPU affinity,
and concurrency level): **B1** (C3's exact 5-process/4-core concurrency,
plus single-thread numerical-library caps and CPU-affinity pinning) and
**B2** (concurrency derived at runtime from the measured 4-vCPU quota via
a rule frozen before the run, which evaluated to `W=1`, i.e. 1
process/GPU — a legitimate output of the pre-registered rule, not a
failure of it).

Neither configuration improved on plain C3. B1's mean per-task training
rate (0.212 steps/s) was statistically identical to C3's own (0.213
steps/s) despite running under the same CPU oversubscription — thread
capping bought nothing measurable. B2 roughly doubled per-task training
depth when uncontended (0.406 steps/s mean) but lost that gain entirely to
having to run in two sequential waves (only 2 slots for 5 tasks), landing
at a lower aggregate depth-adjusted throughput than B0/B1, not a higher
one. Direct per-process telemetry (new in this pilot: context-switch
counts, per-core CPU%) confirmed CPU contention is real and precisely
proportional to process-count/core-count ratio (2/4=50% measured 51.2%;
5/4 clamped to 100% measured 99.6%) — but GPU utilisation, not CPU load,
tracked with per-task training rate (GPU0 jumped 27%→85% mean utilisation
purely from a second process joining it, at a CPU load nowhere near
saturated). **The throughput ceiling is GPU-level time-sharing among
concurrent CUDA contexts on the same T4, not CPU thread-pool contention**
— full derivation `experiments/EXP002C3/RESULTS.md` §4.

Neither B1 nor B2 cleared any of the three pre-registered performance
criteria (≥20% higher unique-candidates/min, ≥20% higher iterations/min, or
similar throughput at materially lower CPU usage), while both cleared
every mandatory safety/quality criterion (0 OOM, 0 archive corruption, 0
failures, diversity preserved above the 90% floor). Verdict: **KEEP FROZEN
C3** — no further CPU-side orchestration tuning is worth pursuing for this
workload on this host; C3 as originally measured in EXP002-C2 remains the
frozen operating point for any future acquisition. `experiments/EXP002C3/
SCALING_PROJECTION.md` and `CORPUS_ACQUISITION_DECISION.md` restate the
unrevised acquisition-cost numbers with the added confidence that C3's
rate is close to this workload's real ceiling, not a placeholder awaiting
an orchestration fix. `docs/MODEL_SELECTION_RESOURCE_CONSTRAINTS.md`
records the resource constraints (4 effective vCPUs, 14.6 GiB VRAM/T4,
GPU-sharing throughput tax) this pilot's measurements impose on any future
MODEL-001 base-model choice. No further acquisition was launched, per the
explicit execution limits this pass operated under.
