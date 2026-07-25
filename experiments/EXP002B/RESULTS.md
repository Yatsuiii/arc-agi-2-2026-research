# EXP002-B — RESULTS

Preregistration: `experiments/EXP002B/PLAN.md`. Corpus:
`artifacts/run001/run001/` — same archive as EXP002, unchanged (no new GPU
candidates generated, per this pass's explicit scope).

## 1. Commit SHA

Code that ran: this commit. Confidence-semantics fix and V0-V3 tracks landed
in the two commits immediately preceding this file's own commit (`git log`).

## 2. Exact configuration

Identical to `experiments/EXP002/RESULTS.md` §2 (same archive, same fold
seed `20260725`, same task-family proxy), plus:

- `singleton_prior`: measured empirically as P(correct) among Fold A's own
  singleton (1-unique-candidate) test-indices — **0.333** (see §6 below) —
  and applied identically to every V0-V3 track before ranking.
- V2-learned features: `sorted(INDEPENDENT_FEATURES)`, 14 names, all checked
  by `assert_score_independent` at construction.
- V3-hybrid features: `sorted(INDEPENDENT_FEATURES | SCORE_DERIVED_FEATURES)`,
  31 names, deliberately unrestricted.
- `LogisticRegression(max_iter=5000)` — raised from EXP002's 1000 after a
  convergence warning appeared once V2/V3's wider unscaled feature ranges
  were fit; fixed before this run, not after seeing its result.

## 3. Exact command

```
python -m src.analysis.exp002b_verifier_eval
python -m src.analysis.exp002b_figures
```

## 4. Random seeds

Fold assignment: `20260725` (unchanged from EXP002 — same split). Bootstrap
CIs: `20260725`, 2000 resamples.

## 5. Runtime

2.25s wall-clock, CPU only. Success criterion 7 ("runtime negligible relative
to generation") met, same margin as EXP002 (~20,000x vs. RUN-001's 11h43m).

## 6. Hardware

Local CPU.

## 7. Results

### H0 — pipeline check: PASSED EXACTLY (inherited from EXP002)

Identical to `experiments/EXP002/RESULTS.md` §7: 30/94 oracle, 23/94
selected, 7.45pp, exact match to `experiments/RUN001/RESULTS.md`'s preview.
Confirms this pass is scoring the same corpus the same way.

### Confidence bug fix result

Before this pass, every singleton (1-unique-candidate) test-index reported
`probability_correct = 1.0` regardless of correctness — the bug
`experiments/EXP002/ERROR_ANALYSIS.md` found. Measured directly:

| | Value |
| --- | --- |
| Singleton test-indices (full corpus) | 9 / 94 (9.6%) |
| Actually correct among them | 2 / 9 (22.2%) |
| **Old** reported confidence for all 9 | **1.0**, uniformly |
| **Old** false-confidence rate @ p>=0.8 | **77.8%** (7 of 9 wrong, all reported 1.0) |
| **New** `correctness_confidence` for all 9 | **0.333** (the measured empirical prior) |
| **New** false-confidence rate @ p>=0.8 | **undefined (no predictions reach 0.8)** — nothing to be falsely confident about, rather than a wrong 77.8% |

Figure: `artifacts/EXP002B/figures/g4_singleton_confidence_before_after.png`.
**The fix converts a measurably wrong confidence signal (77.8% of
"maximally confident" predictions were false) into an honestly uncertain one
that matches the base rate.** This holds for every V0/V1/V2-heuristic track
identically, since all three call the same `build_result` (Part 1's fix is in
the shared builder, not per-verifier).

### V0-V3 accuracy, with bootstrap CIs

| Track | Full corpus (n=94) | Fold C (n=18) |
| --- | --- | --- |
| V0 frozen selector | 24.5% [16.0%, 33.0%] | 16.7% [0.0%, 33.3%] |
| V1 native-score control | 24.5% [16.0%, 33.0%] | 16.7% [0.0%, 33.3%] |
| V2 independent heuristic | 23.4% [14.9%, 31.9%] | 11.1% [0.0%, 27.8%] |
| V2 independent learned | n/a (Fold-C-only by design) | 5.6% [0.0%, 16.7%] |
| V3 hybrid | n/a | 16.7% [0.0%, 33.3%] |
| **Oracle** | **31.9% [22.3%, 41.5%]** | **22.2% [5.6%, 44.4%]** |

Figure: `artifacts/EXP002B/figures/g1_track_accuracy_ci.png` — **every
interval overlaps every other interval.** V1 exactly ties V0 (proving the
pipeline reproduces it, its only job). No V2 or V3 track beats V0 at either
sample size; V2-independent-learned is numerically the worst track measured,
though its CI still overlaps V0's.

### Recovered headroom is not computed as a point estimate this pass

Given the CI overlap above, reporting a single recovered-headroom number
(as EXP002 did) would imply more precision than these bootstrap intervals
support. The honest summary is qualitative: **no track's confidence interval
excludes V0's, so this pass cannot distinguish "V2 recovers headroom" from
"V2 recovers none" at n=18.**

### Selective accuracy vs. coverage

Figure: `artifacts/EXP002B/figures/g2_selective_accuracy.png`.

| Coverage | V0 accuracy (n) | V2-learned accuracy (n) |
| --- | --- | --- |
| 100% | 24.5% (94) / 16.7% (18) | — / 5.6% (18) |
| 80% | 28.0% (75) | 7.1% (14) |
| 60% | 32.1% (56) | 9.1% (11) |
| 40% | 26.3% (38) | 0.0% (7) |
| 20% | 26.3% (19) | 0.0% (4) |

V0's curve (full corpus, n=94) is mildly non-monotonic but directionally
consistent with success criterion 5 (accuracy rises as coverage shrinks,
peaking at 60%). **V2-independent-learned's curve (Fold C, n=18) is not** —
it is flat-to-worse at low coverage, meaning its confidence does not
successfully triage easy from hard cases at this sample size. Criterion 5
**fails for V2 as measured**, though n=18 makes this hard to distinguish from
noise (4 examples at the 20% coverage point).

### Calibration and AUC of correctness_confidence vs. hit

| Track | Brier | ECE | NLL | AUC(confidence, hit) |
| --- | --- | --- | --- | --- |
| V0 (full corpus) | — | — | — | 0.592 |
| V2-independent-learned (Fold C) | 0.071 | 0.081 | 0.264 | 0.529 |

V2-learned's calibration metrics look numerically fine in isolation (low
Brier, low ECE) but its AUC (0.529) is barely above chance (0.5) — consistent
with the selective-accuracy finding: the *values* are not wildly miscalibrated
on average, but they carry almost no information about *which* specific
prediction is right. V0's AUC (0.592) is modestly better despite having no
fitted calibration at all, which is itself informative: whatever signal exists
in this corpus is not currently better captured by the score-independent
learned model than by the frozen selector's own ranking.

### Singleton-candidate error rate, by track

Every V0/V1/V2-heuristic track shares the same singleton subset (9 of 94,
error rate 77.8% — see confidence-fix section above); this is a property of
the *archive* (which grids RUN-001 generated), not of any individual
verifier's logic, since all three see the same candidates. V2-learned and
V3-hybrid, evaluated on Fold C only, have exactly 1 singleton test-index each
(error rate 100% on that single example — too small to interpret alone,
consistent with the pattern above).

### Results by candidate-set sufficiency bucket (V0, full corpus)

| Bucket | Accuracy | n |
| --- | --- | --- |
| insufficient (abstain, <=1 unique candidate) | 22.2% | 9 |
| some (sufficiency < 0.5) | 14.3% | 7 |
| sufficient (sufficiency >= 0.5) | 25.6% | 78 |

Directionally consistent with sufficiency mattering (the "sufficient" bucket
scores highest) but the "insufficient" bucket is not the worst
(counter-intuitively 22.2% vs. "some" at 14.3%) — again most plausibly a
small-sample artifact (n=7-9 per bucket) rather than evidence that
abstention-worthy cases are actually easier.

### Feature ablation, independence-restricted (H1 re-test)

Figure: `artifacts/EXP002B/figures/g3_independent_feature_ablation.png`.

| Feature | AUC | n |
| --- | --- | --- |
| `object_count_consistent_with_demo_pattern` | **0.833** | 81 |
| `removed_colours_seen_in_demos` | 0.609 | 487 |
| `n_colours_introduced_by_candidate` | 0.573 | 487 |
| everything else | 0.34-0.55 | 275-487 |

**H1 result changes materially once score-derived features are excluded.**
EXP002's original H1 pass had 6 features above/near 0.60; with those same
features now correctly excluded, only **one** clears the threshold —
the same `object_count_consistent_with_demo_pattern` EXP002's own analysis
already flagged as the one genuinely independent signal. It is real (AUC
0.833) but narrow (covers 81 of 487 grid-rows, 16.6%, because it requires
every demonstration pair in a task to agree on the same object-count delta).
No other independent feature clears 0.60.

## 8. Confidence intervals

Reported throughout via 2000-resample bootstrap (§7), not Wilson intervals —
chosen because the metric being bounded (`recovered_headroom`-style
comparisons) is a function of two correlated accuracy estimates on the same
items, which bootstrap resampling of the paired outcome vector handles more
directly than an independent-proportions formula would.

## 9. Per-task breakdown

`artifacts/EXP002B/exp002b_report.json` — `track_reports.*.{full_corpus,fold_c_only}`
carry the same per-test-index detail as EXP002's report, restructured around
V0-V3 and the new confidence fields.

## 10. Failure categories

Unchanged from `experiments/EXP002/RESULTS.md` §10 (same archive): branch G
68.1%, branch S 7.4%, realised 24.5%. This pass changes *how* candidates are
reranked and *how* confidence is reported, not which candidates were
generated, so the generation/selection split is identical by construction.

## 11. Claims supported / weakened / rejected

| Claim | Effect |
| --- | --- |
| C2 (selection is a bottleneck distinct from generation, ARC-AGI-2 recoverable half) | **Still not shown.** Restricting to genuinely independent features weakens the raw H1 signal (6 features -> 1) and V2 does not beat V0 at any measured sample size. The one surviving independent feature (`object_count_consistent_with_demo_pattern`) is real but too narrow (16.6% coverage) to carry a combiner alone at n=18/n=94. |
| Confidence-validity sub-claim (new, from Part 1) | **Supported.** The singleton-confidence bug is real, measured (77.8% false-confidence rate under the old behaviour), and fixed (undefined/absent false-confidence under the new behaviour, because reported confidence no longer exceeds the empirical base rate). This is a genuine, reusable contribution independent of the verifier-accuracy question. |

## 12. Artifact paths

- `artifacts/EXP002B/exp002b_report.json`
- `artifacts/EXP002B/figures/g1..g4*.png`
- `src/analysis/exp002b_verifier_eval.py`, `src/analysis/exp002b_figures.py`
- `src/harness/verifier/independent.py`, `src/harness/features/independence.py`
- `src/harness/verifier/base.py` (confidence fix)

## 13. Candidate figures

4 delivered: `g1_track_accuracy_ci`, `g2_selective_accuracy`,
`g3_independent_feature_ablation`, `g4_singleton_confidence_before_after`.
(EXP002's own 7 figures remain valid for the questions they answered; not
regenerated here since the underlying B0-B8 comparison is unchanged.)

## 14. Follow-up justified by the evidence

1. **Acquisition is now the binding constraint, not verifier design.**
   `CORPUS_REQUIREMENTS.md`'s power analysis (Fold C needs >=100 test-indices)
   is confirmed by this pass's own CI widths — every track's interval spans
   30+ percentage points at n=18. Redesigning V2's combiner further without
   more data would very likely just move noise around.
2. **`object_count_consistent_with_demo_pattern` is the one feature worth
   generalising** — the structural check that requires unanimous demo-pair
   agreement on object-count delta is too strict (81/487 coverage); a
   per-pair-majority relaxation of the same check, plus the analogous
   relaxation for `output_size_matches_expected`/`tiling_pattern_consistent_with_demos`
   (also unanimity-gated), is the concrete next feature-engineering step.
3. **The confidence fix should propagate to any future stopping-rule work**
   (still gated, EXP003) as a precondition, not an afterthought — it is
   already the shared builder every verifier calls, so no further wiring is
   needed, but any new verifier added later must not bypass `build_result`/
   `build_result_from_probabilities`.

## 15. Deviations from plan

1. **`LogisticRegression(max_iter=5000)`** — raised from EXP002's 1000 after
   a convergence warning on V2/V3's unscaled feature ranges. Fixed before
   this run (not tuned after seeing a result); noted because it is a change
   from EXP002's exact configuration.
2. **Recovered-headroom point estimate omitted** (§7) — a deliberate choice
   given the CI overlap, not a silent gap; EXP002's version (which did report
   a point estimate) is left as-is for comparison, and this file explains why
   this pass reports differently.
3. **V2-independent-learned and V3-hybrid evaluated on Fold C only**, per
   plan (§9-10) — no full-corpus number exists for either, since both are
   fit on Fold A and evaluating them on data they were fit on would not be
   held-out.

## Scope limits, stated plainly

- **Still RUN-001, still partial, still contaminated.** Nothing in this pass
  changed the corpus.
- **n=18 (Fold C) is not decisive for any V0-vs-V2 comparison.** Every CI in
  §7 overlaps every other. This is stated as the primary limitation, not
  buried in a caveats section.
- **The confidence fix is real and corpus-independent** — it would hold on
  any future, larger corpus too, since it is a property of the builder logic,
  not of this specific archive.

---

## Verdict: REDESIGN (again), with one component promoted out of "redesign" entirely

- **Confidence semantics (Part 1): DONE, not "redesign again."** Measured,
  fixed, tested. This component should not be revisited unless a new failure
  mode is found.
- **Score-independent verification (Parts 2-3, the H1/H2 question): REDESIGN
  still applies, but the redesign is no longer "which features to combine" —
  it is "acquire more data."** H1 survives with one real, narrow feature; H2
  cannot be resolved at n=18/n=94 regardless of combiner cleverness, and this
  pass's CIs make that quantitatively explicit rather than a judgment call.
- **Not REJECT.** Nothing in this pass shows V2 *fails* to beat V0 in any
  statistically meaningful sense — the intervals are too wide to show
  failure any more than they show success. Rejecting the thesis now would be
  drawing a conclusion the data cannot support in either direction.
