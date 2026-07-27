# GEN002-A — RESULTS

## Verdict

**NULL: STOP THIS FROZEN DSL/SEARCH CONFIGURATION.**

Under the 42-primitive typed DSL implemented and frozen before the pilot,
the preregistered depth/cost bounds, and 20,000-state budgets, neither S0
nor S1 found a program exact on every visible demonstration for any of
the 24 frozen pilot tasks. Consequently they emitted zero test candidates,
achieved 0/24 program-synthesis oracle coverage, and rescued 0/12
CompressARC Group-A generation failures. `PRIMITIVE_CATALOG.md` records
the implementation-time deviations from `DSL_SPEC.md`'s anticipated
37-primitive surface; every deviation predates Phase 6.

This rejects the scoped hypothesis that this bounded implementation is a
useful complementary generator. It does not reject program synthesis as
a family: the pilot is n=24 and Phase 8 shows most failures are consistent
with language/reachability limits under the frozen bounds.

## Primary metrics

| Metric | Result |
| --- | ---: |
| Pilot indices completed | 24/24 |
| S0 candidate oracle | 0/24 (0%) |
| S1 candidate oracle | 0/24 (0%) |
| Program-synthesis union oracle | 0/24 (0%) |
| CompressARC oracle on frozen pilot | 12/24 (50%) |
| CompressARC + program-synthesis union oracle | 12/24 (50%) |
| Incremental program-synthesis rescues | 0 |
| Group-A rescues | **0/12** |
| Group-B rescues | 0/6 |
| Group-C redundant successes | 0/6 |
| C/P Jaccard | 0.0 (P is empty) |

The union oracle is unchanged from CompressARC alone. Selection accuracy is
undefined for GEN002-A because there are no candidates to rank.

## Search behavior

Every S0 and S1 task run consumed exactly 20,000 states. No run reached
its wall-clock cap: the state budget was binding on 48/48 policy/task
runs, matching `SEARCH_PROTOCOL.md`'s preregistered expectation. Aggregate
per-task policy time was 23.565 CPU-seconds for S0 and 31.537 CPU-seconds
for S1; the parallel pilot completed in 16.11 wall-clock seconds.

The search implementation is not trivially inert: unit fixtures find and
validate one-step rotation/reflection programs. The real pilot null is
therefore a coverage result for the frozen task sample, not evidence that
the emission path never functions.

## Failure taxonomy

Phase 8 assigns 17/24 indices to bounded `missing_language` and 7/24 to
bounded `search_failure`; none reach `generalization_failure` because no
training-exact program was emitted. Definitions, limitations, and the
per-group table are in `ERROR_ANALYSIS.md`.

## Leakage and contamination

Generation reads only demonstrations and test inputs. Solutions are first
loaded by offline Phase 7/8 analysis after candidate archives exist. The
generator has no pretrained parameters or training corpus, so
pretrained-checkpoint contamination is structurally absent. No primitive
or search parameter changed after correctness was observed.

## Follow-up

Do not increase this run's budget or add primitives in place. Either action
would tune against the pilot. A future broader program language or search
must be separately preregistered and evaluated on a new frozen sample.
Phase 10's `DECISION_MATRIX.md` records how this null combines with each
possible outcome of the still-unlaunched, contaminated GEN001-A pilot.

## Verification

`tests/gen002/`: **112 passed**. Full repository suite: **370 passed**,
0 failures. The artifact manifest's nine SHA-256 digests and byte sizes
were independently recomputed after generation and all matched.
