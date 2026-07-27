# GEN002-A — RELATED_SYSTEMS_AUDIT

Which program-search concepts this project's local references demonstrate,
and which of those concepts are legally reimplementable vs. requiring
clean-room reconstruction. Concepts only — no code is copied into
`src/gen002/` from any of these; `LICENSE_AUDIT.md` states why.

## References inspected

| Reference | Path | Programme-synthesis relevance |
| --- | --- | --- |
| Barbadillo `arc25` | `references/score_winners/05_barbadillo/arc25/dsl.py` (402 lines) + `code_execution.py`, `code_analysis.py`, `parallel_code_execution.py` | A hand-written DSL (`Img`/`Object`/`bounding_box`/`point` types), execution sandboxing, parallel code execution, code-analysis tooling. Cites its own lineage (ARC24 DSL, BARC's `seeds/common.py`) in its module docstring. |
| SOAR | `references/paper_winners/02_soar/` | LLM-driven Python program synthesis with evolutionary refinement and hindsight relabeling — no hand-written DSL, no beam/best-first search over a typed grammar (an LLM proposes full Python programs directly). Not directly applicable to GEN002-A's DSL-search approach, but its "failed program is a correct program for a different task" framing is a useful naming lens for GEN002-A's own near-solution archive (Phase 5). |
| ARChitects | `references/score_winners/02_architects/` | Neural (TTT + DFS over token sequences), not symbolic program search. Object/scene representations not applicable; DFS-with-cutoff *search-control* concept (best-first-like pruning by cumulative score) is a general algorithmic pattern, not code, and is reused conceptually in S1's priority ordering. |
| NVARC | `references/score_winners/01_nvarc/` | Neural, not symbolic. No DSL or object representation to draw from. |
| CompressARC | `third_party/compressarc/` (already vendored, MIT) | Per-task compression-based neural search, not symbolic. Its per-task (not pretrained) inductive bias is the closest conceptual precedent for GEN002-A's own "no pretrained checkpoint" property, though the mechanism (gradient descent over a per-task network vs. discrete program search) is unrelated. |
| ARC Prize technical reports | `papers/00_arc_agi_2_technical_report.pdf`, `papers/00_arc_prize_2025_technical_report.pdf` | Survey-level discussion of program-synthesis approaches (object-centric DSLs, ARC-DSL lineage) as one of the three historically competitive families alongside TTT-neural and recursive-refinement approaches — background only, no code. |

## Concepts documented as legally reimplementable (general algorithmic
ideas, not any one author's expression)

- **Object extraction via connected-component labelling** (4- and
  8-connectivity) — a standard, decades-old computer-vision algorithm
  (Rosenfeld & Pfaltz 1966), not original to any ARC solver. Implemented
  from the textbook algorithm, not from Barbadillo's `dsl.py`.
- **Type-directed program search** — a standard program-synthesis
  technique (Osera & Zdancewic 2015, "type-and-example-directed program
  synthesis"; well outside any of these repos' authorship). Implemented
  from the published technique description.
- **Semantic hashing / observational-equivalence pruning** — standard in
  bottom-up program synthesis (Udupa et al. 2013, "TRANSIT"; also DeepCoder,
  Balog et al. 2017). General technique, clean-room implemented.
- **Best-first search with a multi-key priority** — standard AI search
  (Hart, Nilsson & Raphael 1968, A*; best-first search is textbook
  material). Not attributable to any single local reference.
- **Minimum-description-length program ranking** — standard Occam's-razor
  heuristic in program synthesis (Rissanen 1978's general MDL principle),
  used generically, not copied from any local reference's specific cost
  function.
- **DFS-with-cutoff as search control** (ARChitects' batched DFS,
  `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §2) — the *idea* of pruning a
  search tree by cumulative cost against a threshold is general (it is
  literally A*/branch-and-bound); GEN002-A's pruning (`SEARCH_PROTOCOL.md`
  items 8-10) is its own cost function over typed program-state shape/
  colour/object-count agreement, not a port of ARChitects' token-level
  DFS.

## Concepts explicitly not reused, and why

- Barbadillo's actual DSL implementation (`dsl.py`'s specific function
  signatures, `Img`/`Object` class definitions) — licensed `All rights
  reserved` (`docs/REFERENCE_LICENSE_AUDIT.md` §3), `RESEARCH REFERENCE
  ONLY`. GEN002-A's own `src/gen002/dsl/types.py`/`primitives.py` are
  independently designed (different type set: `Grid`/`ObjectSet`/`Mask`/
  `Direction` rather than `Img`/`bounding_box`/`point`; different
  primitive names and signatures throughout).
- BARC's `seeds/common.py` (cited by Barbadillo's own docstring as a
  further upstream source) — not fetched into this workspace at all
  (`paper/REPRODUCIBILITY.md`'s "NVARC submodules not fetched" list), so
  there is nothing local to even risk copying from.
- SOAR's LLM-driven synthesis approach — not reused at all; the
  acceptance message explicitly prohibits an LLM in GEN002-A, so this is
  a moot exclusion, restated here only for completeness of the audit.

## Conclusion

Every reusable idea in this document is a general, decades-old or
widely-published algorithmic technique, independent of any one local
reference's specific code. `src/gen002/` is a clean-room implementation
throughout — no function signature, class name, or code fragment is
copied from `references/`.
