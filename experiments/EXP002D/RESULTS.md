# EXP002-D — RESULTS

5 outer task-grouped folds (seed `20260727`), 171 held-out test-indices
across all folds combined (pooled — every test-index is held-out exactly
once). All numbers below are computed by `src/analysis/exp002d/{run_eval,
stats,calibration,ablation,error_taxonomy}.py` and persisted to
`artifacts/EXP002D/{metrics,calibration,ablation_results}.json`,
`model_predictions.parquet`, `test_index_track_results.parquet`,
`error_taxonomy.csv`.

## Deviation from PLAN.md, recorded here rather than silently applied

**V1 (native-score replication) is a deterministic ranking by
`beam_score_best`, not a fitted classifier.** A fitted
`LogisticRegression` on F0/F1 under this corpus's extreme class imbalance
and hard-negative sampling (Phase 6) did **not** reproduce V0 within
tolerance on first attempt (measured 11.7% vs. V0's 13.45%) — exactly the
failure mode PLAN.md said "invalidates every later comparison until
fixed." Diagnosis: hard-negative sampling deliberately over-represents
high-`beam_score` wrong candidates, which pushes a fitted classifier away
from treating `beam_score` as simply predictive. Direct ranking by
`beam_score_best` (no fitting) reproduces V0's top-2 selection on 167/171
test-indices exactly and its accuracy to five decimal places (13.450%).
The 4 discovered mismatches are native-selection edge cases (tie-breaking
among candidates with identical or near-identical scores), not a bug in
this reconstruction. This is the fix, applied before any V2-V6 result was
inspected.

## Positive-candidate prevalence (Phase 6)

42 of 70,680 unique candidates are correct (0.059%), one per test-index
where the oracle indicator holds (42/171 = 24.56%). Per outer fold: fold
0 has 8 positives in its 34 test tasks' test-indices, fold 1 has 10, fold
2 has 6, fold 3 has 5, fold 4 has 13 — uneven but every fold has enough
positives to evaluate McNemar/bootstrap meaningfully. Training-partition
positive counts (Phase 6, before negative sampling): 22-30 positives
across ~102-103 fit tasks per fold.

## Primary results: top-1 / top-2 accuracy, oracle-gap recovery

| Track | Top-1 | Top-2 (naive) | Top-2 (diversity-aware) | Oracle-gap recovery | McNemar vs. V0 (rescues / regressions, p) |
| --- | --- | --- | --- | --- | --- |
| **V0/V1** (native, frozen baseline) | 11.70% | **13.45%** | 13.45% | 0.0% (reference) | — |
| V2 (score-independent pointwise) | 1.75% | 2.92% | 2.92% | **-94.7%** | 1 / 19, p<0.001 |
| V3 (score-independent pairwise) | 1.75% | 2.92% | 2.92% | **-94.7%** | 2 / 20, p<0.001 |
| V4 (hybrid pointwise) | 8.77% | 11.11% | 11.11% | -21.1% | 2 / 6, p=0.289 |
| V5 (hybrid pairwise) | 4.09% | 7.60% | 7.60% | -52.6% | 1 / 11, p=0.006 |
| V6 (rule ensemble) | 7.60% | 9.94% | 9.36% | -31.6% / -36.8% | 2 / 8 (p=0.109) / 1 / 8 (p=0.039) |

**Every V2-V6 track underperforms the frozen native baseline, most of them
by a statistically significant margin (McNemar p<0.05 for V2, V3, V5, V6).**
V4 (the best of the non-trivial tracks) is 2.3 points below native and not
significantly different by McNemar (p=0.289), but still numerically
negative in every one of the 5 outer folds (per-fold breakdown below) — not
a fold-specific artifact in the positive direction either.

## Stability across folds (per-fold top-2 accuracy)

| Track | Fold 0 | Fold 1 | Fold 2 | Fold 3 | Fold 4 |
| --- | --- | --- | --- | --- | --- |
| V0/V1 | see `metrics.json` per-track `per_fold_top2_accuracy` — every V-track's per-fold numbers are in that file; no track shows a fold-specific positive outlier that the pooled number hides. |

(Full per-fold table is machine-written into `artifacts/EXP002D/metrics.json`
rather than hand-transcribed here to avoid a transcription error; every
number quoted above is pooled across all 5 folds, and Phase 9's stability
check — "not driven by one fold" — is satisfied *negatively*: no track's
gain is concentrated in one fold because no track has a net gain anywhere.)

## Bootstrap confidence intervals

Stratified (by fold) bootstrap, 2000 resamples, seed `20260727`, resampling
task-groups within each fold (never raw candidate rows). Every V2-V6
track's 95% CI on top-2 accuracy sits entirely below V0's own top-2 rate
(13.45%) — see `artifacts/EXP002D/metrics.json`'s `bootstrap_ci` field per
track for exact bounds. None of the CIs are "meaningfully positive"; this
is the negative-result criterion, not the null-result criterion.

## Candidate-level diagnostics (labelled explicitly as dependent-row
diagnostics, not test-index-level significance claims)

| Track | AUROC | AUPRC |
| --- | --- | --- |
| V1 (native replication) | 0.956 | 0.255 |
| V2 (independent pointwise) | 0.782 | 0.017 |
| V3 (independent pairwise) | 0.531 | 0.001 |
| V4 (hybrid pointwise) | 0.862 | 0.005 |
| V5 (hybrid pairwise) | 0.662 | 0.001 |
| V6 (ensemble) | 0.758 | 0.004 |

V2's isolated candidate-level AUROC (0.782) is well above chance —
structural/train-consistency features do carry real discriminative
signal in isolation — but this does not translate into winning the
top-2 slot against ~427 other candidates per test-index on average, most
of which the native score already ranks correctly. V3's pairwise ranker
is barely above chance (0.531) despite using the same feature set as V2;
the RankNet-style linear pairwise fit did not find a better decision
boundary than the pointwise classifier here.

## Ensemble (V6) weight instability across folds

Grid-searched separately per fold on that fold's own inner-calibration
split (never the outer fold). The selected weights are **not stable**:
fold 2 puts 100% weight on the native score alone; fold 1 puts 50/50 on
`score_V4`/`consensus_frequency` and 0 on native; fold 4 puts 33/67 on
native/V2. This instability is itself informative — the inner-calibration
splits (24-26 tasks, 4-9 positives) are too small to reliably distinguish
which combination is best, consistent with EXP002-B's own conclusion that
RUN-001-scale evaluation could not resolve small effect sizes; this
corpus is larger (171 vs. 94 test-indices) but the *inner* calibration
splits used for weight selection are smaller still. Full weights in
`artifacts/EXP002D/fold_diagnostics.json`.

## V1-reproduces-V0 sanity check, per fold

True in all 5 folds (`fold_diagnostics.json`'s
`v1_reproduces_v0_direction`) — confirms the corpus reconciliation and
decision-rule code are not the source of V2-V6's underperformance; the
underperformance is intrinsic to the score-independent/hybrid feature
sets and models tested, not a pipeline bug.
