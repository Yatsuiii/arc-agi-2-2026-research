# GEN002-A — POST-PILOT DECISION MATRIX

Phase 10 freezes the action after both GEN002-A and GEN001-A have pilot
results. GEN002-A is already observed; GEN001-A remains unlaunched. No
cell may be changed after the NVARC pilot is seen.

## Shared outcome buckets

For direct comparison, each generator is bucketed by Group-A rescues on
the identical frozen 12-index set:

- **Promising**: at least 3/12 rescues.
- **Ambiguous**: exactly 2/12 rescues.
- **Null**: 0-1/12 rescues.

These are GEN001-A's preregistered primary thresholds
(`SUCCESS_CRITERIA.md`), reused without modification. Secondary execution
and integrity gates still apply. GEN002-A is **Null (0/12)**.

## Matrix

| GEN002-A program synthesis | GEN001-A NVARC | Action |
| --- | --- | --- |
| Promising | Promising | Preserve both generators in the union schema; preregister a larger clean program-synthesis run. NVARC remains competition-engineering evidence only because its checkpoint is contaminated. |
| Promising | Ambiguous | Scale only the clean program-synthesis hypothesis; do not spend on a larger NVARC run. |
| Promising | Null | Scale only program synthesis; stop this NVARC branch. |
| Ambiguous | Promising | Do not scale GEN002-A without a second clean pilot; retain NVARC only as a contaminated engineering lead. |
| Ambiguous | Ambiguous | Stop and redesign; neither signal pays for a larger run. |
| Ambiguous | Null | Stop NVARC; preregister one targeted clean follow-up only if Phase 8 identifies a general language gap rather than task-specific tuning. |
| **Null** | **Promising** | **Current possible path:** stop GEN002-A at its frozen DSL/budget; NVARC may justify competition engineering, but not a clean paper claim or verifier-corpus inclusion. |
| **Null** | **Ambiguous** | **Current possible path:** scale neither; preserve artifacts and seek a different clean generator family. |
| **Null** | **Null** | **Current possible path:** stop both branches; the complementarity hypothesis remains unresolved for other generator families, but these two implementations do not justify more compute. |

## Current state

Only the GEN002-A axis is known. This document does not authorize a
GEN001-A launch, query live Kaggle quota, or weaken GEN001-A's
contamination policy. Until that separately human-gated pilot runs, the
matrix has three possible current-path cells and no final cross-generator
verdict.
