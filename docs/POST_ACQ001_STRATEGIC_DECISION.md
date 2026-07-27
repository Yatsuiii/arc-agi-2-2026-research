# POST-ACQ001 STRATEGIC DECISION

Written after EXP002-D (`experiments/EXP002D/`), the first powered
verifier evaluation run on ACQ-001's clean, leakage-checked 171-index
CompressARC candidate corpus. This document answers the question ACQ-001
was built to enable: given real, non-contaminated data at the
pre-registered power floor, is selection-side work (a verifier) or
generation-side work (a better candidate generator) the higher-value next
investment?

## How much of the 11.1-point selection gap was recovered

**None.** Every non-trivial verifier track (V2 through V6 — score-independent
pointwise, score-independent pairwise, hybrid pointwise, hybrid pairwise,
rule ensemble) scored *below* the frozen native top-2 baseline (13.45%),
most by a statistically significant margin (McNemar p<0.05 for V2, V3,
V5, V6; V4, the best of the alternatives, was 2.3 points below native and
not statistically distinguishable from it, p=0.289). Oracle-gap recovery
is negative for every track (`experiments/EXP002D/RESULTS.md`). This is a
**negative result** for V2/V3/V5/V6 and a **null-to-mildly-negative
result** for V4, evaluated against the pre-registered thresholds
(`experiments/EXP002D/PLAN.md`).

## Remaining selection headroom

The 11.1-point gap (24.56% oracle - 13.45% native) is **still entirely
unclaimed**. Nothing in this experiment closes it; if anything, this
experiment demonstrates that the specific score-independent grid features
tried here (F2/F3, from `structural_features`) and the specific
candidate-set relational features tried (F4) are not, on their own or in
combination with the native score, sufficient to out-rank CompressARC's
own `beam_score`. A different feature family (e.g. genuine transformation
program synthesis, object-correspondence reasoning explicitly out of
scope for this pass per `paper/FAILURE_TAXONOMY.md`'s "explicitly
rejected categories") might do better, but nothing tested here supports
that claim either way.

## The 75.44% candidate-generation failure rate

**This is the dominant fact.** 129 of 171 test-indices (75.44%) have **no
correct candidate anywhere in the archive**, regardless of any selection
mechanism (`experiments/EXP002D/ERROR_ANALYSIS.md`). Even a perfect
oracle verifier is bounded at 24.56% top-2 accuracy on this corpus. The
maximum a selection-only intervention could ever be worth, on this
generator, is closing the remaining 11.1 points — and this experiment
found no evidence that closing even a fraction of that is easy. Compare:
closing the 75.44-point generation gap even partially is worth an order
of magnitude more than the entire selection headroom combined.

## Whether verifier integration is justified

**No, not on the current evidence.** No tested verifier reached the
primary success threshold (+2.8 points / ~25% oracle-gap recovery); every
non-trivial track actively hurt performance. Integrating any of V2-V6 into
a production pipeline today would make results worse, not better.

## Whether confidence is valid for compute routing

**No.** Candidate-set sufficiency (Phase 8) — whether a track's own
score-distribution entropy predicts if a correct candidate exists at all
— measured AUROC at or near chance (0.46-0.54) for every track
(`experiments/EXP002D/CALIBRATION_RESULTS.md`). Among the 129 generation
failures, the sufficiency measure never once correctly flagged the
absence of a correct answer (0/129 scored below 0.1; all 129 scored
>=0.5). A stopping rule or compute allocator built on this signal would
not know when CompressARC has failed.

## Which candidate families are complementary

Not established by this pass. The verifier-rescue set (2 test-indices)
and native-only-success set (6 test-indices) are too small to characterise
a systematic complementary family (`ERROR_ANALYSIS.md`'s representative
examples). This question needs either a genuinely different generator (to
produce candidates CompressARC structurally cannot) or a larger corpus —
not more verifier engineering on the existing candidate pool.

## Which task families CompressARC misses

Generation failures skew toward the `same` and `smaller` size-relation
families in raw count (76 and 36 of 129 respectively,
`ERROR_ANALYSIS.md`), but this tracks the corpus's own family
distribution (102 and 48 of 171 total) rather than showing a
disproportionate failure rate concentrated in one family — a
family-normalised failure-rate breakdown was not computed this pass and
would need a dedicated analysis, not reused from this one.

## Which task families have correct candidates but poor selection

Only 17 of 171 test-indices ("both fail, correct candidate present" —
`ERROR_ANALYSIS.md`) fall in this category at all — too small a set for
this pass to identify a family pattern with any confidence. This is
itself informative: **the "selection is failing on task family X"
hypothesis has very little supporting data on this corpus**, because
generation failure so dominates the error budget.

## What properties the next generator must add

Based on this corpus's evidence, not speculation: the next generator
needs to change the **75.44% no-correct-candidate rate**, not the
selection mechanism operating on top of it. CompressARC (a per-task,
from-scratch neural compression solver, no pretraining, no program
synthesis, no explicit object/transformation reasoning) evidently cannot
find the correct transformation at all on three-quarters of this held-out
set. A generator that adds any of: pretrained cross-task priors (NVARC
branches), explicit object-correspondence/program-synthesis reasoning
(the exact category `paper/FAILURE_TAXONOMY.md` flagged as needing a
correspondence step this pass never attempted), or test-time refinement
loops (TRM-style) targets that gap directly, where this experiment's
evidence says the leverage actually is.

## Recommended next research phase (exactly one, not started)

**Restore and evaluate an NVARC-branch (or comparable pretrained-prior)
generator on this same clean 171-index corpus**, to measure its own
oracle coverage under the identical leakage-checked, family-disjoint
conditions ACQ-001 already established — directly answering whether a
pretrained-prior generator closes a meaningful fraction of the 75.44%
generation-failure rate that CompressARC alone cannot. This is a
generation-side acquisition experiment (ACQ-002-style), not a verifier
experiment, and not started by this document. It reuses ACQ-001's
existing split protocol, leakage controls, and frozen fold structure
directly, so its own preregistration burden is small relative to
building a wholly new evaluation harness.
