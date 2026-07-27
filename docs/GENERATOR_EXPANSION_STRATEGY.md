# GENERATOR_EXPANSION_STRATEGY

The strategic decision memo connecting EXP002-D's frozen verifier verdict
to GEN001-A's pilot preflight, and what would justify each next step this
project could take.

## Why verifier research was frozen

`experiments/EXP002D/RESULTS.md` (verdict, `fb3e93d`): on ACQ-001's
leakage-audited, appropriately-powered (171-index) clean corpus, every
preregistered verifier track — score-independent and hybrid, pointwise and
pairwise, single-model and ensemble — scored below the frozen native
selector, most of them significantly so (McNemar p<0.05). The best
alternative (V4, hybrid) produced 2 rescues against 6 regressions. Candidate-
set sufficiency, the proxy for "should this ranking be trusted at all," was
at chance (AUROC 0.46-0.54) and never once correctly flagged a generation
failure. There is no reranking mechanism this project tested, on this data,
that recovers any of the 11.1-percentage-point gap between candidate oracle
coverage and native selection accuracy.

## Why generation now dominates

The reason the gap is unrecoverable by reranking is upstream of ranking
entirely: **129 of 171 test-indices (75.44%) have no correct CompressARC
candidate in the archive at all**
(`experiments/EXP002D/error_taxonomy.csv`). No verifier, however good,
can select a candidate that was never generated. Only 17/171 (9.9%) are
genuine ranking failures — a correct candidate present, neither selector
finding it. The error budget is overwhelmingly generation-side, by a factor
of roughly 7.6:1.

## What CompressARC currently solves

24.56% candidate-set oracle coverage, 13.45% realised (native top-2)
selection accuracy, on ACQ-001's clean 171-index corpus
(`experiments/EXP002D/BASELINE_SPEC.md`). The 11.1pp gap between those two
numbers is the entire space verifier research could have claimed, and
EXP002-D established it cannot currently be claimed by reranking alone.

## What task families it misses

Not yet characterised at the family level with any statistical power —
`docs/POST_ACQ001_STRATEGIC_DECISION.md` already noted this limitation
(129 generation failures spread thin across `size_relation` families is not
enough to support a family-conditional claim at this sample size). This
remains an open question a larger corpus or a second generator's
complementary coverage pattern could help answer, not one this memo
resolves.

## How the NVARC pilot tests complementarity

GEN001-A does not ask whether NVARC's own selection beats CompressARC's —
that comparison is contaminated and, separately, not the lever EXP002-D's
finding points at. It asks a narrower, decision-relevant question: does
NVARC's *candidate set* contain correct grids on test-indices where
CompressARC's candidate set contains none (`GENERATOR_COMPARISON.md`'s
union-oracle metric, `SUCCESS_CRITERIA.md`'s primary threshold — at least
3/12 preregistered Group-A generation failures rescued). This is the
cheapest available test of "is a second, architecturally different
generator complementary," using a generator this workspace has already
restored and validated end-to-end once (RUN-001), rather than building a
new generator from nothing.

## How contamination limits paper claims

`experiments/GEN001A/CONTAMINATION_AUDIT.md`: all 160/160 ACQ-001 tasks are
members of the exact file glob NVARC's SDG pipeline used to build its
`arc2_training` fine-tuning dataset, which concatenates each task's test
pair directly into training messages at 256 augmented copies per task.
Classified **SCIENTIFICALLY CONTAMINATED**. Any future pilot result is
therefore permanently barred from entering `paper/CLAIM_LEDGER.md` as clean
evidence, and permanently barred from training or evaluating the EXP002-D
clean-verifier corpus or any successor
(`experiments/GEN001A/CONTAMINATION_POLICY.md`'s consequences). A pilot can
still answer the competition-engineering question above — set
complementarity is a property of what the model generates, not
straightforwardly guaranteed by what it memorized — but it can never
license a "NVARC improves ARC-AGI-2 accuracy by X points" sentence in this
paper.

## Whether a clean-room NVARC-derived generator may later be necessary

If the pilot's answer to the complementarity question is positive (meets
`SUCCESS_CRITERIA.md`'s primary or strong-success bar), the honest
follow-on is not "use this checkpoint in the paper" — it is "a
generator with NVARC's architectural properties (TTT, DFS search,
augmented rescoring) appears complementary to CompressARC's compression-
based search; is that complementarity attributable to the architecture or
to memorized answers, and can it be reproduced by a checkpoint trained
without ACQ-001's 160 tasks in its data." That would require either
retraining NVARC's SDG pipeline with ACQ-001's 160 tasks excluded (compute
cost per `paper/REPRODUCIBILITY.md`'s "permanently out of reach" listing
for full pretraining, though a fine-tune-only exclusion may be far
cheaper) or an entirely different pretrained-prior generator whose training
data is checkable against ACQ-001 from the start. This decision is not
made now — it is conditional on a pilot result that does not yet exist.

## Conditions under which the full 171-index NVARC run would be justified

All of the following, not any one alone:

1. The 24-index pilot meets at least the primary success threshold
   (`SUCCESS_CRITERIA.md`): >=3/12 Group-A rescues.
2. The pilot's measured cost-per-incremental-solved-index projects to a
   feasible full-corpus GPU-hour budget (comparable order of magnitude to
   ACQ-001's own 37.67 GPU-hours, not a multiple of it).
3. Incremental coverage is not concentrated in a single task family in a
   way that would make a full run redundant with the pilot's own signal.
4. A decision has been made (per the clean-room question above) about
   whether the full run's results will ever be paper-eligible, or whether
   it is explicitly scoped as competition-engineering only — decided
   before launch, not after seeing results.

## Relation to the competition architecture: heterogeneous generators first, selection second

EXP002-D's and GEN001-A's findings together point at the same structural
lesson the strongest public 2025 systems already encode implicitly: NVARC's
own branch-ensembling result (`docs/NVARC_LINEAGE.md`) found near-zero
marginal value from combining TRM and Qwen3 at the 4B scale specifically
*because* branch coverage overlap was already high at that scale — but the
same document also notes the sentence "about 2-3 puzzles solved by TRM were
not always picked by Qwen3 scoring," meaning heterogeneous generation
*did* have unique coverage even when selection wasted some of it. This
project's own evidence is stronger and larger-sample: 75.44% generation
failure on a corpus no verifier can rerank around. The architecture this
points toward is **heterogeneous candidate generation first (multiple,
architecturally distinct generators, each contributing an independent
candidate pool), selection second (a verifier or ranking stage operating
over the union)** — not a single generator optimized harder, and not a
verifier asked to do more with a fixed, insufficient candidate pool. GEN001-A
is the first test of whether this project has access to a second generator
worth adding to that pool.

## What this memo does not decide

It does not launch the pilot. `PILOT_PROTOCOL.md`'s launch gate and
`QUOTA_PROJECTION.md`'s minimum-quota condition remain the only path to a
real pilot result, and that launch is a separate, explicit, human-confirmed
action this phase does not take.
