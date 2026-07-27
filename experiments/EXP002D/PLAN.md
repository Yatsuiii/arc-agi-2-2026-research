# EXP002-D — PLAN (preregistered before model fitting)

CPU-only. Does not touch Kaggle, does not regenerate candidates, does not
modify CompressARC. Operates entirely on the immutable ACQ-001 archives
(`artifacts/ACQ001/shard_a_output/`, `artifacts/ACQ001/shard_b_output/`).

## Question

Does a model-independent (or hybrid) verifier recover a meaningful fraction
of the measured 11.1-point gap between candidate-set oracle coverage
(24.56%) and CompressARC's own native top-2 selection accuracy (13.45%),
on the clean, leakage-checked 171-index ACQ-001 corpus?

## What is different from EXP002-B, stated up front

EXP002-B ran on RUN-001's NVARC archive: multi-seed, multi-augmentation,
with a rich provenance schema (`ttt_seed`, `augmentation_key`,
`n_seeds_producing`, etc.) and its own aggregation formula
(`score_kgmon`). ACQ-001's CompressARC archive is **one solver process per
task, no augmentation ensemble, no seed diversity** — each candidate
record carries only `beam_score` (`accumulated_score` in the raw
per-task JSON) and a discovery-order position within the beam search.
Consequently:

- F1 (score-replication) collapses onto F0 (native baseline) almost
  exactly — there is no separate aggregation formula to reconstruct, only
  the same `beam_score`/rank fields the archive already carries. V1 is
  kept as a pipeline sanity check (must reproduce V0 exactly), not as a
  meaningful independent track.
- Several F4/F5 items in the original spec (seed group, augmentation
  diversity, stability under inverse augmentation, source-process
  agreement, rank agreement across augmentations) **do not exist in this
  corpus** and are recorded as not-applicable rather than fabricated.
  What remains genuinely computable: duplicate multiplicity, consensus
  frequency, distance from the modal candidate, discovery-order position,
  and task-level solve telemetry (`steps_run`, `elapsed_s`,
  `hit_time_guard`).
- n=171 test-indices is the pre-registered power floor
  (`experiments/EXP002B/CORPUS_REQUIREMENTS.md`), not a large-sample
  regime — EXP002-B's own conclusion was that RUN-001's n=94 (and its
  n=18 held-out fold) could not resolve small effect sizes. This plan's
  statistical design and success thresholds are written accepting that
  n=171 gives real but still limited power, and pools bootstrap evidence
  across folds rather than trusting any single fold.

## Folds (frozen before any model touches data)

Five outer, task-grouped folds. All 171 test-indices belonging to one task
stay in the same fold (a task never crosses a fold boundary). Stratified
by `size_relation` family (`src/data_audit/statistics.py::describe`,
reusing the field ACQ-001's own `folds.json` was stratified on) computed
over the 160 corpus tasks, round-robin assignment within each stratum.
Frozen seed: `EXP002D_FOLD_SEED = 20260727`. Assignments persisted to
`artifacts/EXP002D/fold_assignments.json` before any feature is computed
on ground truth.

Inside each outer training partition (4/5 folds), a further 80/20
task-grouped split produces an inner calibration set (Platt scaling fit
here, never on the outer held-out fold). No inner-fold candidate ever
touches the outer test fold.

Repeating with additional fold seeds is skipped (single frozen seed) —
with only 160 tasks and up to 6 verifier tracks x 7 ablations, a
multi-seed repeat multiplies CPU time for a marginal precision gain the
paired-bootstrap already covers; this is a preregistered scope decision,
not a result-driven one.

## Feature groups (preregistered, see FEATURE_CATALOG.md for the full
audit table written before Phase 5 model fitting)

- **F0** — native baseline: `beam_score`, `beam_score` percentile within
  the test-index, `original_rank` (1-indexed rank by score within the
  test-index).
- **F1** — score-replication: identical fields to F0 in this corpus (see
  "what is different" above). V1 must tie V0 exactly; a mismatch
  invalidates every later comparison until fixed.
- **F2+F3** — score-independent grid features, computed by
  `src/harness/features/structural.py::structural_features` (candidate
  vs. test input vs. demonstration pairs, from the training challenges
  file). Never reads `beam_score` or any archive-order field. Candidate
  correctness is never used to compute it.
- **F4** — candidate-set relational features, computed within each
  test-index's own candidate set only: duplicate multiplicity, consensus
  frequency (multiplicity / total), pixel-distance from the modal
  (highest-multiplicity) candidate, mean pixel-distance from the rest of
  the set, discovery-order position (index in the per-task beam-search
  candidate list, normalised 0-1).
- **F5** — provenance: task-level `steps_run`, `elapsed_s`,
  `hit_time_guard`, `device`. Thin in this corpus (see above); reported
  and audited for zero variance rather than dropped silently.
- **F6** — hybrid: union of F0/F1 and F2-F5.

Score-independence enforcement: a new frozen `SCORE_DERIVED`/`INDEPENDENT`
classification lives in `src/analysis/exp002d/features.py`, following
`src/harness/features/independence.py`'s pattern (`assert_score_independent`
raises on any unclassified or score-derived name reaching a V2/V3 track).

## Model families (frozen; no broad hyperparameter search)

- **V0** — native top-2 selector (the archive's own `selection` records,
  `algorithm="compressarc_top2"`). Primary baseline, measured 13.45%.
- **V1** — native-score replication (F0/F1 pointwise logistic
  regression). Must reproduce V0's ranking within tolerance; a pipeline
  sanity check only.
- **V2** — score-independent pointwise verifier: F2-F5 only, two models
  (`sklearn.linear_model.LogisticRegression(C=1.0, max_iter=5000)`,
  `sklearn.ensemble.HistGradientBoostingClassifier` — both already in the
  installed `scikit-learn 1.8`, no new dependency). No sweep beyond these
  two fixed configurations.
- **V3** — score-independent pairwise ranker: F2-F5, trained on
  within-test-index (correct, incorrect) candidate pairs. Deterministic
  negative sampling (Phase 6): every positive paired against up to 20
  hard negatives (nearest in F2-F5 feature space) plus up to 5 easy
  negatives (random draw), capped so no test-index with a huge candidate
  set dominates the pair count.
- **V4** — hybrid pointwise verifier: F0/F1 union F2-F5, same two model
  configurations as V2.
- **V5** — hybrid pairwise ranker: same sampling as V3, F0/F1 union
  F2-F5 features. Included as originally specified.
- **V6** — rule ensemble: a fixed linear combination of (native rank,
  best V2 score, best V4 score, F4 consensus-frequency signal), with
  combination weights selected by grid search **inside the inner folds
  only**, never against outer-fold outcomes.

No neural network, no GPU training, no `xgboost`/`lightgbm` (not
installed; would add a new dependency the plan does not preregister).

## Metrics (see METRIC_SPEC.md)

Primary: top-2 test-index accuracy. Secondary: top-1 accuracy, mean
reciprocal rank, correct-candidate rank, oracle-gap recovery. Calibration:
Brier score, log loss, ECE, AUROC, AUPRC, reliability, selective accuracy.
Candidate-set sufficiency evaluated separately against the oracle
indicator (does any correct candidate exist for this test-index).

## Statistical tests

McNemar (paired, test-index level) for every V-track vs. V0. Stratified
(by fold) bootstrap 95% CIs, 2000 resamples, seed `20260727`. The
statistical unit is the held-out test-index grouped by task — never a
raw candidate row (candidates within a test-index are dependent).

## Success thresholds (frozen, restated from the acceptance message)

- Primary success: >=2.8 absolute points top-2 gain over V0 (~25% oracle-gap
  recovery), CI meaningfully positive or McNemar supports a real
  improvement, not driven by one fold, calibration beats naive
  relative-score confidence.
- Strong success: >=5.5 points (~50% recovery), stable fold-level results,
  useful sufficiency prediction.
- Null result: <1.5 points, unstable/fold-specific, no useful calibration.
- Negative result: net top-2 reduction, non-monotonic confidence, gain
  disappears under task-grouped evaluation, or feature leakage found.

## Stopping rule

Fit every preregistered model family exactly once per outer fold, using
the preregistered feature groups and the preregistered fixed
hyperparameter set. No outer-fold result is inspected before every model
in every fold has been fit. No feature, model, or threshold in this
document is changed after Phase 5 begins. Deviations, if any become
necessary, are recorded in RESULTS.md as deviations, not silently
folded into a rewritten plan.

## Explicit non-goals

No compute allocation, no confidence-based stopping, no MODEL-001, no
RUN-002, no new candidate generator, no CompressARC modification, no
Kaggle GPU use.
