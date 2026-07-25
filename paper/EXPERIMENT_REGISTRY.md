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
| EXP002 | Model-independent candidate verification feasibility (thesis T2's decisive experiment) | **PREREGISTERED**, BLOCKED on RUN-001 | `c8f08a4` | pending | C2 |

Status values: `PREREGISTERED`, `RUNNING`, `COMPLETE`, `KILLED`, `ABANDONED`
(with reason).

## Runs that are not experiments

RUN-001 is registered here for provenance but is **dataset acquisition plus a
competition-baseline capture**, not a hypothesis test. It supports no claim on
its own. Its purpose is to produce the candidate archive that EXP001-B needs,
and its accuracy number is contaminated by construction because the checkpoint
was trained on the split it scores (`docs/systems/NVARC.md` §9).

## EXP002, and why it is preregistered before RUN-001 has landed

EXP002 (`experiments/EXP002/PLAN.md`) is a real hypothesis test, not
acquisition, but its plan is committed and its status set to
`PREREGISTERED, BLOCKED on RUN-001` while RUN-001 is still running, so the
design cannot be tuned after the fact to whatever the archive turns out to
contain. Its own preconditions (`experiments/RUN001/POST_RUN_CHECKLIST.md`)
gate execution on RUN-001 reaching a terminal state and passing
`src/run001/validate_outputs.validate`. No code beyond the ingestion and
headroom-analysis tooling it depends on (`src/run001/download_outputs.py`,
`src/run001/validate_outputs.py`, `src/analysis/candidate_headroom.py`) has
been written for it.
