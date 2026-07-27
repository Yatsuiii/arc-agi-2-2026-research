# EXP002-D — METRIC_SPEC

All metrics computed at the **test-index level** (one row per `(task_id,
test_index)`), never at the raw candidate-row level — candidates within a
test-index are dependent, so candidate-level rows are not an independent
statistical unit.

## Primary

**Top-2 test-index accuracy**: a test-index counts as correct if either of
the verifier's two selected candidates exactly matches ground truth.

## Secondary

- **Top-1 accuracy**: the verifier's single highest-ranked candidate
  matches ground truth.
- **Mean reciprocal rank (MRR)**: `1 / rank_of_first_correct_candidate`
  in the verifier's full ranking of unique candidates for that
  test-index; 0 if no correct candidate exists in the set (a generation
  failure, not a ranking failure).
- **Correct-candidate rank**: for test-indices where a correct candidate
  exists, its rank under the verifier's ordering.
- **Oracle-gap recovery**:
  `(verifier_top2 - native_top2) / (candidate_oracle - native_top2)`,
  computed per fold and pooled. `candidate_oracle = 24.56%`,
  `native_top2 = 13.45%` (both restated from
  `experiments/ACQ001/FINAL_CORPUS_REPORT.md`, recomputed independently
  in Phase 1 to confirm agreement before use as denominators here).

## Calibration (rank-1 and rank-2 selected candidates)

Brier score, log loss, expected calibration error (ECE, 10 bins), AUROC,
AUPRC, precision at confidence >=0.8, selective accuracy vs. coverage
curve. Reuses `src/harness/metrics.py` (`brier_score`,
`expected_calibration_error`, `negative_log_likelihood`,
`false_confidence_rate`, `reliability_bins`, `auc`) directly — the same
functions EXP002-B's `CONFIDENCE_SEMANTICS.md` fix was measured with, so
EXP002-D's calibration numbers are on the same scale as that prior work.

## Candidate-set sufficiency

A separate binary target: does at least one correct candidate exist for
this test-index (the oracle indicator). Evaluated with the same
AUROC/AUPRC/Brier/calibration battery, kept in its own report section —
never conflated with "is the selected candidate correct," per EXP002-B's
three-way confidence split (`ranking_confidence` /
`correctness_confidence` / `candidate_set_sufficiency`).

## Statistical tests

- **McNemar's test** (paired, exact binomial when discordant-pair count
  is small): compares each V-track's top-2 correctness indicator against
  V0's, test-index by test-index.
- **Stratified bootstrap**: 2000 resamples, stratified by outer fold,
  seed `20260727`. 95% CIs on top-2 accuracy, top-1 accuracy, MRR, and
  oracle-gap recovery.
- Reported per fold and pooled — a pooled CI alone is not sufficient
  evidence per this plan's success criteria ("not driven by one fold").

## What is not claimed

No candidate-level AUROC/AUPRC is presented as if candidates were i.i.d.
rows — Phase 9 of the acceptance message explicitly prohibits this. Any
candidate-level classification metric reported (e.g. for feature
ablation diagnostics) is labelled as a diagnostic over dependent rows,
not a claim of statistical significance.
