# GEN002-B — PLAN

## Objective

Test whether a redesigned CPU-only symbolic generator, built from ARC
TRAIN/DEV evidence and mature program-synthesis system design, can add
useful candidate coverage on a fresh 24-index held-out pilot that does
not overlap GEN001-A or the original GEN002-A pilot.

## Scope

GEN002-B is a clean successor to GEN002-A's frozen null result. The old
24-index GEN002-A pilot is no longer validation evidence; it is reused
only as development diagnostics. The new phase does not relaunch
CompressARC, does not touch GEN001-A, does not use Kaggle, and does not
train a verifier.

## Frozen phases

1. Isolation and recovery in a new worktree and branch.
2. Reclassify the GEN002-A pilot as `GEN002B_DEV_DIAGNOSTIC`.
3. Freeze a fresh 24-index validation manifest with no overlap against
   the old pilot and task-level disjointness preferred.
4. Analyse the GEN002-A `missing_language` cases using only
   demonstrations, traces, corpus evidence, and literature.
5. Audit mature symbolic ARC systems and choose one lineage before
   implementation.
6. Design a typed DSL V2 with grid, object, relational, pattern, and
   control/composition levels.
7. Implement executable transformation templates and a three-stage
   bounded search.
8. Benchmark expressivity on fixed TRAIN/DEV tasks and freeze the final
   configuration.
9. Run the fresh validation pilot exactly once.
10. Perform offline legal analysis and freeze one verdict.
11. Prepare, but do not launch, three-way comparison plumbing for later
   NVARC integration.

## Success criteria

Minimum viability:

- at least 6/24 validation indices emit one or more candidates;
- at least 2/12 Group-A2 generation failures are rescued;
- no leakage and no task-specific handwritten rules;
- runtime remains CPU-feasible.

Primary success:

- at least 3/12 Group-A2 rescues;
- at least 10/24 indices emit candidates;
- at least three distinct transformation families are solved;
- CompressARC union oracle improves by at least 12.5 absolute points on
  the fresh pilot.

Null:

- zero Group-A2 rescues;
- fewer than 4/24 indices emit candidates;
- `missing_language` remains dominant.

## Engineering constraints

- No Kaggle, no paid APIs, no cloud GPU.
- No modification of GEN001-A artifacts, code, or claims.
- No rerun of CompressARC or verifier training.
- No use of hidden test outputs during generation.
- No post-validation DSL/search edits before the result documents are
  frozen.

## Baseline note

The new branch starts from repository commit `4fbb980`. On this baseline,
plain `pytest -q` fails collection because `src` is not on `PYTHONPATH`;
`PYTHONPATH=. pytest -q` reaches 257 passed tests and one failure caused
by a GEN001 notebook test attempting to write into the read-only sibling
worktree. This is recorded as an environment property, not a GEN002-B
result.
