# PAPER_DRAFT

Working draft. Sections carry a status marker so it is always clear what is
evidence and what is intention.

- `[EVIDENCE]` — every statement traceable to a local artifact or an experiment.
- `[SCAFFOLD]` — structure only, no claims yet.
- `[BLOCKED]` — waiting on a named prerequisite.

---

## Title

`[BLOCKED on Phase 12]` Depends on the selected thesis.

## Abstract

`[BLOCKED]`

## 1. Introduction

`[SCAFFOLD]`

Intended shape:

1. ARC-AGI-2 is unsolved: the best 2025 Kaggle public-leaderboard result was
   27.64%, and 29.72% shortly after the deadline (NVARC25).
2. The strongest public systems converged on one recipe — pretrain on augmented
   and synthetic grids, LoRA test-time-train per task, search the decoder for
   many candidates, score candidates by augmentation-consistent likelihood.
3. Within that recipe, the reported gains are dominated by data scale, not by
   the parts of the system that a small-compute researcher can move.
4. `[BLOCKED]` Our contribution.

## 2. Background

`[EVIDENCE]` sourced from `paper/RELATED_WORK.md`.

- 2.1 ARC-AGI-2 task format and scoring (2 attempts, exact grid match).
- 2.2 The 2025 recipe: TTT, augmentation, DFS decoding, augmented rescoring.
- 2.3 The alternative lines: recursion (TRM), program synthesis (SOAR),
  compression (CompressARC).

## 3. Related work

`[EVIDENCE]` See `paper/RELATED_WORK.md`. To be condensed, not rewritten. The
per-idea organisation there is deliberate and should survive into the paper.

## 4. Method

`[BLOCKED on Phase 12]`

## 5. Experimental setup

`[EVIDENCE]` partially available now.

- 5.1 Data. Kaggle ARC Prize 2026 files are authoritative. The GitHub ARC-AGI-2
  public evaluation set differs on 6 of 120 tasks, including 5 test pairs absent
  from the public repository (`docs/PROJECT_STATE.md` §5). Every number in this
  paper states its snapshot.
- 5.2 Splits and the contamination position. Any NVARC-derived checkpoint has
  been trained on data derived from the 120 public evaluation tasks
  (`nvarc_2025.pdf` §2.1, §3.1). Numbers measured for such a checkpoint on that
  split are reported as contaminated.
- 5.3 Hardware. `[BLOCKED]` — see `paper/COMPUTE_LEDGER.md`.
- 5.4 Statistical treatment. n = 120 on public eval. One task is 0.83pp.
  Confidence intervals on every number; no claim rests on fewer than ~10 tasks
  of difference.

## 6. Results

`[BLOCKED]` for the paper's headline result. One component result is
available: EXP002-D's powered verifier evaluation
(`experiments/EXP002D/RESULTS.md`) found that no model-independent or
hybrid verifier recovers any of the measured 11.1pp gap between
candidate-set oracle coverage (24.56%) and CompressARC's native top-2
selection (13.45%) on ACQ-001's clean 171-index corpus — a negative
result for the selection-side thesis (C2), reported honestly per this
project's negative-result discipline (Appendix B). The dominant finding,
75.44% of held-out test-indices having no correct candidate at all
regardless of selection mechanism, redirects the paper's likely
contribution toward generation-side analysis rather than a verifier
result, per `docs/POST_ACQ001_STRATEGIC_DECISION.md`.

## 7. Ablations

`[BLOCKED]` Structure fixed in `paper/ABLATION_MATRIX.md`.

## 8. Failure analysis

`[SCAFFOLD]` Taxonomy and labelling protocol in `paper/FAILURE_TAXONOMY.md`.
Must report counts on real predictions, not intuition.

## 9. Limitations

`[EVIDENCE]` Already knowable and worth writing before the results exist, so
they cannot be quietly dropped later:

- The public evaluation split is n = 120 and is contaminated for any
  NVARC-derived checkpoint.
- The public leaderboard is half of the hidden set; we do not tune against it
  (`paper/CLAIM_LEDGER.md` A4).
- The strongest public decoder is non-deterministic under batching
  (`nvarc_2025.pdf` §3.3), so candidate sets are not exactly reproducible.
- MindsAI and Lonnie artifacts are unavailable, so our cross-system comparison
  omits two systems that scored.
- We cannot retrain the NVARC pretraining stage: it took 4 nodes x 8xH100 for 27
  hours (`nvarc_2025.pdf` §3.1).

## 10. Conclusion

`[BLOCKED]`

## Appendix A: Reproducibility

`[EVIDENCE]` See `paper/REPRODUCIBILITY.md`.

## Appendix B: Negative results

`[SCAFFOLD]` Every killed experiment from `paper/EXPERIMENT_REGISTRY.md` appears
here with its original preregistered hypothesis. This appendix is not optional.

One entry available now: **EXP002-D** preregistered 6 verifier tracks
(`experiments/EXP002D/PLAN.md`) against a >=2.8pp top-2 accuracy success
threshold; every non-trivial track scored below the frozen native
baseline instead, most significantly (`experiments/EXP002D/RESULTS.md`).
Reported here in full per this project's negative-result discipline, not
omitted because the hypothesis failed.
