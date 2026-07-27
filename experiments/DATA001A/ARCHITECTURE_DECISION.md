# DATA001-A — ARCHITECTURE_DECISION

## Chosen lineage

Clean-room structured scene generator + typed transformation AST + executable validation, inspired by NVARC's executable SDG discipline but reimplemented without NVARC code or data reuse.

## Why this lineage

1. It preserves auditability: every task has an executable typed program and deterministic provenance.
2. It adopts the useful part of the strongest synthetic lineage: executable validation before acceptance.
3. It avoids the unusable part of that lineage: contaminated or unlicensed data/code reuse.
4. It supports both direct-grid supervision and structured-trace auxiliary supervision from the same task record.
5. It is CPU-feasible for corpus generation and local validation.

## Rejected alternatives

- NVARC-style direct reuse: scientifically blocked by provenance.
- Human/VLM filtered synthetic curation: too subjective and expensive for a clean preflight.
- Another symbolic solver redesign: frozen by GEN002-B's null result.
