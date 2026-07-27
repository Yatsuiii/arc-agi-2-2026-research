# EXP002-D — LEAKAGE_AUDIT

Three distinct leakage surfaces, audited separately.

## 1. Corpus-level leakage (inherited from ACQ-001, restated)

Already established and unchanged: 0 exact-duplicate tasks, 0 canonical
(D4 + colour-relabel) duplicate tasks, 0 shared demonstration pairs across
TRAIN/DEV/TEST (`experiments/ACQ001/SPLIT_MANIFEST.md`). EXP002-D reads
only the TEST-fold candidate archives; it does not touch TRAIN or DEV.
Not re-audited here since no new task enters the corpus in this
experiment — re-running `src/data_audit/duplicates.report` would be
redundant, not a new check.

## 2. Cross-validation leakage (new to EXP002-D, the main risk)

- **Task-grouping**: every test-index belonging to one task is assigned
  to exactly one outer fold and, within a training partition, exactly
  one of {inner-fit, inner-calibration}. Verified programmatically after
  fold assignment (Phase 2): for every fold, the set of task IDs in that
  fold is disjoint from every other fold's task-ID set.
- **Feature computation never touches ground truth**: F0-F5 (Phase 4)
  are computed from `beam_score`, `grid`, `test_input`, and demonstration
  pairs only. Verified by construction — the feature-computation
  functions never receive a `solutions` argument at all (checked by
  reading `src/analysis/exp002d/features.py`'s function signatures).
  Ground truth enters the pipeline in exactly one place: the label
  column built in Phase 1 (`is_correct`), joined onto the feature table
  after both are built independently.
- **Model fitting never sees its own outer-fold labels**: each V-track's
  outer-fold model is fit only on the other four folds' `is_correct`
  labels; the held-out fold's labels are used only for scoring after
  prediction, never for fitting, calibration, threshold selection, or
  feature normalization (Phase 2's requirement, enforced by the fold
  loop's structure — a model object is never constructed with access to
  the held-out fold's `DataFrame` rows).
- **Calibration leakage**: Platt/isotonic calibrators (Phase 8) are fit
  on the inner-calibration split only, never on the outer test fold.
- **Ensemble (V6) weight selection**: grid-searched inside inner folds
  only (Phase 5), never against outer-fold outcomes — audited by
  confirming the ensemble-weight-selection function's only label input
  is the inner-calibration split's `is_correct` column.

## 3. Score leakage into "independent" tracks (V2/V3)

`src/analysis/exp002d/features.py` classifies every feature name into
exactly one of `SCORE_DERIVED` or `INDEPENDENT`
(following `src/harness/features/independence.py`'s enforced pattern).
`beam_score`, any percentile/rank/normalisation derived from it, and any
F4 feature that indirectly encodes vote strength through the archive's
own multiplicity counts are classified `SCORE_DERIVED` — wait, this last
point needs care: duplicate multiplicity (F4) is a property of the
*candidate set as CompressARC's beam search produced it*, not of
`beam_score` directly, but a beam search that revisits the same grid
often is itself evidence the search process favoured that grid, which is
a search-behaviour signal, not a purely score-independent grid property.
**Decision, made here in the audit rather than post-hoc**: F4 relational
features (multiplicity, consensus frequency, distance-from-modal) are
classified `SCORE_DERIVED` for the purposes of V2/V3 (strict
score-independent tracks) and are only available to V4/V5/V6 (hybrid
tracks) — this is stricter than the acceptance message's phase grouping
(which lists F4 under V2's inputs) but is the more defensible reading of
"score-independent," so V2/V3 in EXP002-D use **F2+F3+F5 only**, and this
deviation is recorded here rather than silently reclassified after
seeing results (this decision was made during Phase 0/preregistration,
before any model was fit).

`assert_score_independent` raises `ScoreLeakageError` if any
`SCORE_DERIVED` or unclassified name reaches a V2/V3 model constructor —
checked at import/fit time, not just documented.
