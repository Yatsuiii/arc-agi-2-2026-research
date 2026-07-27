# GEN002-B — MISSING_LANGUAGE_ANALYSIS

This postmortem reclassifies the 17 GEN002-A `missing_language` cases as
development-only evidence. Counts below are overlapping: one failure can
plausibly require more than one capability family.

## Dominant recurring gaps

| Capability family | Plausibly addresses | TRAIN/DEV support | GEN002-A composable already? | New primitive / abstraction needed | Task-specificity risk | Search-space cost |
| --- | ---: | --- | --- | --- | --- | --- |
| Object correspondence and relative placement | 6/17 | Common in ARC train tasks with moved/copied shapes, marker objects, and anchor-relative placement | No reliable correspondence primitive | New abstraction | Medium | Medium |
| Pattern continuation / repetition count / motif reuse | 5/17 | Train tasks such as scaling, tiling, periodic completion, and repeated-object completion | Only weakly, via raw tile/scale composition | New abstraction | Low | Medium |
| Symmetry completion / mirror construction | 4/17 | Train tasks with bilateral completion and reflected fill | Partially through raw reflections, but not completion | New abstraction | Low | Low |
| Separator/panel reasoning and output-layout construction | 4/17 | ARC tasks with row/column separators and multi-panel recombination | No | New abstraction | Medium | Medium |
| Colour-role inference / background ambiguity | 4/17 | Role-based recolouring and non-zero backgrounds recur broadly | Partially, but colour IDs were too literal | New abstraction | Low | Low |
| Connected-component recomposition / region partition | 3/17 | Object merge/split and bbox-based reconstruction are common on TRAIN/DEV | Weakly | New primitive and abstraction | Medium | Medium |
| Line/ray propagation / geometric projection | 3/17 | ARC tasks with extending strokes to boundaries or markers | No | New primitive | Medium | Low |
| Conditional multi-stage composition | 3/17 | Many tasks require object selection then a second transformation | No | New abstraction | Low | High |

## What GEN002-B changed

GEN002-B did not try to solve every family above at once. It introduced a
narrow executable V2 centred on:

- explicit whole-grid transforms;
- colour-role mapping;
- pattern scale/tile templates;
- symmetry completion;
- single-object correspondence by translation;
- object-level crop selection;
- legacy typed fallback search as S2-C.

This was deliberately smaller than the full capability wishlist because
the purpose of GEN002-B was to test whether a modest but typed, auditable,
CPU-feasible redesign could cross the viability threshold on a fresh
held-out sample.

## Outcome

It did not. On the fresh 24-index validation manifest, GEN002-B still
emitted zero candidates and ended with 22/24 `missing_language`, so the
old development postmortem remains directionally correct: the broad gap is
still language coverage, not merely search ranking or test-time
generalization.
