# GEN002-A — SEARCH_PROTOCOL

Frozen before implementation.

## Two policies, both frozen before Phase 6 runs

**S0 — enumerative baseline.** Deterministic cost-ordered enumeration over
typed programs up to a fixed depth, no heuristic ordering beyond
(cost, canonical-serialization) tie-breaking. Strongly bounded by a state
count, not just wall-clock.

**S1 — constraint-guided best-first search.** A priority queue ordered by,
lexicographically: (1) number of training demonstrations exactly solved so
far, descending; (2) mean pixel agreement against training outputs,
descending; (3) dimension agreement (fraction of training pairs whose
predicted shape matches), descending; (4) colour-set agreement, descending;
(5) program cost (MDL proxy — sum of each node's fixed primitive cost),
ascending; (6) canonical serialization, ascending (deterministic
tie-break). All five signals are computed only from visible training
demonstrations — never from a test output.

No LLM anywhere in this policy. No correctness label from any test output
is used during search, structurally: the search loop's scoring function
signature takes only `(program, train_pairs)`, never a test pair.

## Pruning, all applied before either policy's queue insertion

1. Type-directed expansion — only well-typed continuations are generated.
2. Maximum program depth (frozen constant, `search/pruning.py`).
3. Maximum program cost (frozen constant).
4. Canonical serialization — every program has one canonical AST repr;
   two syntactically different programs with the same canonical form are
   the same program and are only explored once.
5. Semantic hashing — a program's behaviour on the training inputs (its
   output grids, or its raised-error signature) is hashed; two
   syntactically different programs with identical semantic hashes on the
   current task's training inputs are observationally equivalent and only
   one is kept (observational-equivalence pruning).
6. Memoized execution — sub-expression results are cached per task.
7. Dead-program elimination — a program that raises `ProgramError` on any
   training input is dropped immediately, never expanded further.
8. Shape/dimension constraint pruning — if a program's output shape on a
   training input cannot possibly reach the training output's shape given
   the remaining primitive budget, drop it.
9. Colour-constraint pruning — if a program's output uses a colour absent
   from every training output and the DSL has no remaining recolour
   budget, drop it.
10. Object-count constraint pruning — analogous, on object counts.
11. Partial demonstration score — used by S1's priority only, not a prune.
12. MDL preference — used by S1's priority (5th key) and as S0's primary
    enumeration order (cost-ordered).
13. Deterministic tie-breaking — canonical serialization, always.
14. Strict per-task timeout — enforced independently of the state budget
    below (whichever binds first stops the task).

## Frozen resource budgets (the timeout deviation from `PLAN.md`)

| Policy | Per-task wall-clock cap | Per-task state-explored cap |
| --- | --- | --- |
| S0 | 20s | 20,000 states |
| S1 | 45s | 20,000 states |

Chosen so a 24-task pilot completes in well under 30 minutes total
(24 x 65s worst case = 26 minutes), CPU-only, without requiring a
multi-hour background run. The state-count cap is expected to be the
binding constraint in the large majority of tasks given this DSL's small
branching factor at shallow depth — most tasks either find an exact
program within a few thousand states or exhaust the budget long before
the wall-clock cap, which the resource analysis (`RESOURCE_ANALYSIS.md`)
reports directly rather than assumes.

## Parallelization

Conservative: `min(4, os.cpu_count() or 1)` worker processes, one task per
worker, no shared mutable state across workers (each task's search cache
is process-local). Chosen to avoid uncontrolled memory growth from a large
shared program cache, per the acceptance message's explicit instruction.

## Resume

`artifacts/GEN002A/run_manifest.json` records completed `(policy,
task_id, test_index)` triples; a resumed run skips any triple already
present, mirroring GEN001-A's `completed_indices.json` pattern.
