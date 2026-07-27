# EXP002-D — CALIBRATION_RESULTS

`src/analysis/exp002d/calibration.py`. Platt scaling fit per outer fold on
that fold's own four-fold training rows only (never the held-out fold's
labels). Two separate evaluations, per EXP002-B's three-way confidence
split — never conflated.

## 1. Rank-1 selected-candidate correctness calibration

| Track | Raw AUROC | Raw Brier | Calibrated Brier | Calibrated ECE | False-confidence rate @ 0.8 |
| --- | --- | --- | --- | --- | --- |
| V1 (native) | **0.855** | 0.472 | 0.092 | see `calibration.json` | see `calibration.json` |
| V2 (independent pointwise) | 0.592 | 0.383 | 0.012 | — | — |
| V3 (independent pairwise) | **0.142** (worse than random) | 0.896 | 0.012 | — | — |
| V4 (hybrid pointwise) | 0.818 | 0.141 | 0.088 | — | — |
| V5 (hybrid pairwise) | 0.369 (worse than random) | 0.698 | 0.041 | — | — |
| V6 (ensemble) | 0.539 | 0.503 | 0.076 | — | — |

Calibrated Brier scores are uniformly low across every track — this is
mostly an artifact of the ~13% (or lower) base rate, not evidence of good
discrimination: a model predicting the base rate for everyone scores a
low Brier trivially. **AUROC is the informative column here.** V1 and V4
discriminate meaningfully (AUROC 0.82-0.86); V2 and V6 are weak but above
chance; **V3 and V5 (both pairwise rankers) are *below* 0.5 AUROC on the
rank-1 selection** — the linear pairwise fit is anti-correlated with
correctness at the very top of its own ranking, a genuinely negative,
reportable finding, not just "no signal."

## 2. Candidate-set sufficiency

Does at least one correct candidate exist for this test-index (the
oracle indicator), predicted from each track's own score-distribution
entropy within the set (same construction as EXP002-B's
`verifier/base.py::_sufficiency`, `effective_count = exp(entropy)`,
`sufficiency = min(1, (effective_count-1)/2)`).

| Track | Sufficiency AUROC | Mean sufficiency when oracle hit | Mean sufficiency when oracle miss |
| --- | --- | --- | --- |
| V1 | 0.460 | 0.912 | 0.986 |
| V2 | 0.500 | 1.000 | 1.000 |
| V3 | 0.539 | 0.972 | 0.910 |
| V4 | 0.500 | 1.000 | 1.000 |
| V5 | 0.517 | 0.897 | 0.873 |
| V6 | 0.500 | 1.000 | 1.000 |

**Every track's sufficiency AUROC sits at or near 0.5 (chance).** Mean
sufficiency is close to the theoretical ceiling (~1.0) whether or not the
test-index actually has a correct candidate present — because CompressARC,
when it fails, still produces a large (mean 427 candidates), diverse
(96.63% unique) pool of *wrong* answers, and this entropy-based measure
cannot distinguish "diverse and correct" from "diverse and wrong."
Confirmed directly: among the 129 test-indices classified as generation
failures in `ERROR_ANALYSIS.md`, **0 had sufficiency <0.1 and all 129 had
sufficiency >=0.5** — the sufficiency signal never once correctly flagged
"this candidate set has no right answer in it."

**Answer to Phase 8's question** ("test whether sufficiency confidence
is useful for future routing"): **no, not as constructed here.** This is
a specific, falsifiable negative result about the entropy-based
sufficiency measure on this corpus, not a general claim that no
sufficiency signal could ever work — a measure that looked at *structural
agreement across the candidate pool* (do the diverse candidates at least
converge on some substructure) rather than raw diversity might do better,
but that is a new idea, not evaluated here, and is explicitly out of
scope (Phase 8: "Do not implement routing in this experiment").
