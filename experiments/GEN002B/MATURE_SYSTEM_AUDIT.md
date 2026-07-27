# GEN002-B — MATURE_SYSTEM_AUDIT

Audit scope: locally available symbolic or program-synthesis ARC systems
and reports, evaluated for compatibility with GEN002-B's constraints:
CPU-only, no LLM in the loop, multiple candidates, auditable execution,
and legal clean-room feasibility.

| System | Identity / local evidence | Licence status | Representation / DSL | Search | CPU-feasible here | Direct reuse | GEN002-A gaps it speaks to |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Barbadillo `arc25` | `references/score_winners/05_barbadillo/` | No explicit permissive licence located in the local checkout; treat as reference-only | Object-centric typed DSL over images, objects, boxes, points | Hand-authored symbolic code and search tooling | Yes | No direct reuse; clean-room only | Object selection, object transforms, richer scene abstractions |
| SOAR | `references/paper_winners/02_soar/README.md` | MIT | Full Python program synthesis via LLM prompts and refinement | Evolutionary sample-and-refine | Not under this phase's constraints | Not selected | Candidate plurality, hindsight relabeling, refinement loop |
| NVARC | `references/score_winners/01_nvarc/` | Mixed / competition artifacts; not a symbolic DSL | Neural transduction with TTT | Decoder search + learned scoring | No, not CPU-only for the real method | No | None directly for typed symbolic redesign |
| ARChitects | `references/score_winners/02_architects/` | Report/docs only in local evidence | Neural decoder, not symbolic | Batched DFS over token sequences | No practical CPU analogue | No | Search-control ideas only |
| CompressARC | `third_party/compressarc/`, `papers/03_compressarc.pdf` | MIT | Per-task neural compression, not symbolic | Gradient descent + native candidate selection | GPU-oriented | No reuse in GEN002-B generation | Complementarity target only |

## Selection outcome

Exactly one lineage is selected:

**Clean-room object-centric ARC-DSL lineage, closest to Barbadillo-style
symbolic systems, with GEN002-A's typed fallback retained only as a
bounded compositional backstop.**

Reasons:

1. It is the only locally evidenced lineage directly aligned with the
   dominant GEN002-A missing-language failures: object correspondence,
   layout construction, and reusable symbolic scene transforms.
2. It is CPU-feasible and fully auditable.
3. It can emit multiple candidates without any learned scorer.
4. Clean-room reimplementation is feasible without depending on
   unlicensed source reuse.
5. SOAR, NVARC, and ARChitects violate one or more phase constraints
   (LLM dependency, GPU dependence, or lack of typed symbolic execution).
