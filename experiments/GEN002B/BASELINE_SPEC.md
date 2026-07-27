# GEN002-B — BASELINE_SPEC

## Frozen predecessor

GEN002-A is the only direct predecessor. Its frozen result is:

- 24 preregistered test-indices;
- 12 Group-A generation failures, 6 Group-B oracle-only successes, 6
  Group-C native successes;
- S0 cost-ordered enumeration and S1 constraint-guided best-first
  search;
- 0 emitted candidates;
- 0/12 Group-A rescues;
- 17/24 bounded `missing_language`;
- 7/24 bounded `search_failure`;
- no archive corruption and no leakage.

Interpretation is deliberately narrow: the null rejects only the frozen
GEN002-A DSL and search implementation. It does not support any claim
that program synthesis in general is invalid for ARC-AGI-2.

## What changes in GEN002-B

GEN002-B changes all three load-bearing pieces:

1. The language: replace the flat GEN002-A primitive surface with a
   structured typed DSL V2 spanning grid, object, relational, pattern,
   and composition layers.
2. The search: replace the S0/S1-only design with template-first,
   relational, and bounded compositional stages under stronger
   demonstration-derived constraints.
3. The validation sample: retire the original 24 indices as development
   data and freeze a new 24-index held-out manifest before redesign.

## What stays fixed

- CPU-only execution.
- Exact-demonstration consistency as the emission gate.
- Deterministic semantics and canonical serialization.
- No hidden-output access during generation.
- No verifier training or learned confidence routing.

## Comparison target

The comparison target is CompressARC's already-frozen archive on ACQ-001.
GEN002-B is evaluated as a complementary candidate generator, not as a
replacement solver. The key effect size is incremental held-out coverage
over CompressARC on the fresh 24-index pilot.
