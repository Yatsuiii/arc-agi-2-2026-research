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
| EXP002-C | Clean ARC-AGI-2 candidate-corpus acquisition using CompressARC | **PREREGISTERED — not executed, gated on GPU-run approval** | see `experiments/EXP002C/PLAN.md` commit | not run | none yet - acquisition only, feeds EXP002-D |

Status values: `PREREGISTERED`, `RUNNING`, `COMPLETE`, `KILLED`, `ABANDONED`
(with reason).

## Runs that are not experiments

RUN-001 is registered here for provenance but is **dataset acquisition plus a
competition-baseline capture**, not a hypothesis test. It supports no claim on
its own. Its purpose is to produce the candidate archive that EXP001-B needs,
and its accuracy number is contaminated by construction because the checkpoint
was trained on the split it scores (`docs/systems/NVARC.md` §9).

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
but `torch`/CUDA are not installed, and the corrected compute estimate for the
preregistered 500-test-index target is ~210-290 GPU-hours serially on this
card — far beyond a single Kaggle-style session. No GPU call was made. The
actual acquisition run (even a small timed pilot) remains gated on explicit
approval, separate from the preregistration itself.
