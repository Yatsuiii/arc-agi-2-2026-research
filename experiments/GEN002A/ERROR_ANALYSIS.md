# GEN002-A — ERROR_ANALYSIS

Phase 8 classifies every unsuccessful index in the frozen 24-index pilot.
The per-index table is `artifacts/GEN002A/error_taxonomy.csv`; the
training-only diagnostic rerun is
`artifacts/GEN002A/search_diagnostics.json`.

## Operational categories

The categories are applied in this order:

1. **Success**: at least one emitted candidate equals the test target.
2. **Generalization failure**: at least one program exactly matched every
   visible demonstration and emitted a test candidate, but no emitted
   candidate equals the target.
3. **Search failure**: no candidate was emitted, but S1 explored at least
   one program that exactly solved one or more (not all) demonstrations.
4. **Missing language**: no candidate was emitted and no explored program
   exactly solved even one complete demonstration.

The last two labels are bounded-search diagnostics, not proofs. In
particular, `missing_language` means "missing from the language explored
within the frozen depth/cost/state bounds"; it does not prove that no
deeper composition in the DSL could express the task. Conversely, a
program solving one demonstration does not prove the full rule is in the
DSL; it is evidence that search reached a locally relevant behavior.

## Counts

| Category | Group A | Group B | Group C | Total |
| --- | ---: | ---: | ---: | ---: |
| Missing language | 10 | 4 | 3 | **17** |
| Search failure | 2 | 2 | 3 | **7** |
| Generalization failure | 0 | 0 | 0 | **0** |
| Success | 0 | 0 | 0 | **0** |
| Total | 12 | 6 | 6 | 24 |

All 24 S0 and S1 runs consumed the full 20,000-state budget and none hit
its wall-clock timeout. Seven tasks produced at least one S1 program that
exactly solved a strict subset of the demonstrations; none produced a
program exact on all demonstrations. The other 17 did not exactly solve
one full demonstration with any explored program, although many reached
high mean pixel agreement. Pixel agreement is reported as a diagnostic
only because a high value can be achieved by preserving a large
background and is not evidence of rule correctness.

## Interpretation

The primary result remains the Phase 7 null: program synthesis added zero
correct candidates and zero Group-A rescues. Phase 8 narrows the failure
mechanism. The majority bucket (17/24) is consistent with insufficient
language or insufficient reachable composition under the frozen bounds;
7/24 show a stronger bounded-search signal. There is no generalization
bucket to study because the demonstration-exact emission gate rejected
every program before any test candidate could be emitted.

No primitive, cost, depth, beam width, or state budget is changed in
response. Any broader DSL or larger search is a future separately
preregistered experiment, as required by `LEAKAGE_POLICY.md`.
