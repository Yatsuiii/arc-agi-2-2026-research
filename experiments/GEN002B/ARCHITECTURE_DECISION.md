# GEN002-B — ARCHITECTURE_DECISION

## Chosen lineage

**Clean-room object-centric symbolic ARC-DSL lineage with template-first
search.**

This is the closest practical fit to the GEN002-A development failure
profile and to the phase constraints:

- CPU only;
- no LLM;
- auditable deterministic execution;
- legal clean-room implementation;
- ability to emit multiple candidates.

## What was rejected

- **SOAR lineage**: useful conceptual contrast, but it depends on LLM
  sampling/refinement and large external models.
- **NVARC / ARChitects lineage**: strong public systems, but neural,
  GPU-heavy, and not symbolic DSL search.
- **CompressARC lineage**: valuable complementarity baseline, not a typed
  symbolic generator.

## Implemented consequence

GEN002-B V2 uses:

- typed whole-grid templates;
- typed object-relational templates;
- deterministic background and connectivity hypotheses;
- legacy GEN002 bounded typed search only as the third fallback stage.

This is a narrower executable surface than the full aspirational DSL list,
but it is the auditable, CPU-feasible subset selected before the fresh
validation run.
