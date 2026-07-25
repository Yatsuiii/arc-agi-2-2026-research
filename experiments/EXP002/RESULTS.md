# EXP002 — RESULTS

Preregistration: `experiments/EXP002/PLAN.md`, committed `c8f08a4` (registered
`paper/EXPERIMENT_REGISTRY.md` at `0d7c17e`), before RUN-001 finished. Nothing
below was tuned against a result that was already known.

## 1. Commit SHA

Code that ran: this commit (harness foundation at `22fda55`..`94127ef`, plus
this file's own commit). Exact SHAs recorded in `git log` at commit time; see
`ARTIFACT_MANIFEST.tsv` for the frozen input archive's own SHA256s.

## 2. Exact configuration

- Candidate archive: `artifacts/run001/run001/` (RUN-001, `TIMED_OUT`,
  72/120 tasks, 94/172 test-inputs, `experiments/RUN001/RESULTS.md`).
- Ground truth: `arc-agi_evaluation_solutions.json` — **CONTAMINATED** for
  this checkpoint (`docs/DATASET_AUDIT.md` §6.1).
- Task-family proxy: `artifacts/data_audit/task_statistics.csv`'s
  `size_relation` flag (`docs/DATASET_AUDIT.md` §6.4).
- Fold split: task-stratified by `size_relation`, round-robin 3:1:1 per
  stratum -> Fold A (fit, 46 tasks) / Fold B (calibration, 13 tasks) / Fold C
  (untouched final eval, 13 tasks, 18 test-indices). Seed `20260725`
  (`src/analysis/exp002_verifier_eval.py:FOLD_SEED`), frozen at first run,
  never re-rolled.
- Learned verifier: logistic regression (`sklearn.linear_model.LogisticRegression`,
  `C=1.0`), 18 features (`LEARNED_FEATURES`), fit on Fold A candidate-grid rows
  only.

## 3. Exact command

```
python -m src.analysis.exp002_verifier_eval
python -m src.analysis.exp002_figures
```

## 4. Random seeds

Fold assignment: `20260725`. `sklearn.LogisticRegression` fitting is
deterministic given fixed input order (no internal randomness at `C=1.0` with
the default `lbfgs` solver on this small a design matrix — not separately
seeded because none of its randomness is exposed at this scale).

## 5. Runtime

`exp002_verifier_eval.py`: **2.05 s wall-clock, CPU only, zero GPU, zero
network.** RUN-001's own generation took 11 h 43 m on 2x T4
(`experiments/RUN001/RESULTS.md`) — a **~20,000x** ratio. Success criterion 6
("runtime negligible relative to candidate generation") is met without
qualification.

## 6. Hardware

Local CPU.

## 7. Results

### H0 — pipeline check: PASSED EXACTLY

| | Value |
| --- | --- |
| Oracle hits (correct grid generated) | 30 / 94 |
| Selected hits (correct grid in NVARC's top-2) | 23 / 94 |
| Headroom | 7.45pp |
| Matches `experiments/RUN001/RESULTS.md`'s independently-published preview | **yes, exactly** |

This is the harness's own version of EXP001-A's H0 gate: the same
oracle/realised computation, run through the new `CandidateStore` /
`OriginalSelectionVerifier` machinery instead of a one-off script, reproduces
the number RUN-001's own writeup already reported. `runner.py`'s frozen-
baseline mode additionally reproduces **all 179 of 179** non-placeholder
submitted attempts in `submission.json` exactly
(`tests/harness/test_runner.py::test_frozen_baseline_reproduces_run001_submission`,
against the real archive). Two independent checks on two independent code
paths agree with RUN-001's own record. The archive is being read the same way
twice.

**Mechanism-test note.** A structural-feature mechanism test against
CompressARC's clean ARC-AGI-1 traces (as the fallback plan allowed) is not
possible: those traces store only a hash and a score per candidate, never the
grid itself (`src/analysis/headroom.py` module docstring), so none of
`structural.py`'s features have anything to compute over. EXP001-A's own H0
(exact reproduction of CompressARC's published 20%/34.75% on 800 clean tasks,
`experiments/EXP001/RESULT.md` §7) is the mechanism evidence available for the
oracle/realised half of this pipeline; the harness's H0 above is the
equivalent check for the part CompressARC's schema cannot exercise.

### Corpus and evidence-track separation

| | |
| --- | --- |
| Track | **COMPETITION-ENGINEERING.** CONTAMINATED (checkpoint trained on this split) + PARTIAL (RUN-001 `TIMED_OUT` at 72/120 tasks). |
| Tasks with candidates | 72 |
| Test-indices with candidates | 94 |
| Fold A (fit) | 46 tasks |
| Fold B (calibration) | 13 tasks |
| Fold C (untouched eval) | 13 tasks, **18 test-indices** |

**No clean ARC-AGI-2 track exists for this run.** RUN-001 only generated
candidates against the contaminated 120-task evaluation split; the training
split (which does have legally clean ground truth) was never run through the
solver, so there is no clean-track ARC-AGI-2 corpus to fall back to beyond the
CompressARC/ARC-AGI-1 mechanism test above. **This is the central limitation
of this result and it is stated here plainly, not buried:** every accuracy
number in this file is competition-engineering evidence. None of it is a
claim about verifier accuracy under `paper/CLAIM_LEDGER.md`'s clean-research
bar.

### Candidate oracle / original / verifier accuracy

| Verifier | Full corpus (n=94) | Fold C only (n=18) |
| --- | ---: | ---: |
| B0 original NVARC | 24.47% | 16.67% |
| B1 raw score | 13.83% | 11.11% |
| B2 duplicate frequency | 23.40% | 16.67% |
| B3 augmentation consensus | 23.40% | 16.67% |
| B4 seed consensus | 21.28% | 11.11% |
| B5 score-weighted consensus | **24.47% (tie)** | 16.67% |
| B6 transformation consistency | 23.40% | 11.11% |
| B7 learned logistic | n/a (Fold-C-only by design) | 16.67% |
| **B8 oracle (upper bound)** | **31.91%** | **22.22%** |

Figure: `artifacts/EXP002/figures/f1_accuracy_comparison.png`.

**No non-oracle method beats B0, at either sample size.** B5 (score-weighted
consensus — a from-scratch reconstruction of NVARC's own `score_kgmon`
formula from archived vote counts and mean augmentation scores) exactly ties
B0 on the full corpus, which is the expected result of independently deriving
the same score B0 was already ranking by. Every other frozen baseline
underperforms B0. B7 (the learned verifier, fit on Fold A only) ties B0 on
Fold C.

### Recovered selection headroom (primary metric, Fold C)

`recovered_headroom = (verifier_acc - original_acc) / (oracle_acc - original_acc)`,
zero-denominator handled per `src/harness/metrics.py` (not triggered here:
Fold C's oracle-original gap is 5.56pp, nonzero).

| Verifier | Recovered headroom |
| --- | ---: |
| B0 original | 0.0 (reference) |
| B1 raw score | −1.00 |
| B2 duplicate frequency | 0.0 |
| B3 augmentation consensus | 0.0 |
| B4 seed consensus | −0.43 |
| B5 score-weighted consensus | 0.0 |
| B6 transformation consistency | −0.14 |
| B7 learned logistic | 0.0 |
| B8 oracle | 1.0 (by construction) |

Figure: `artifacts/EXP002/figures/f2_recovered_headroom.png`. **Zero or
negative for every non-oracle method.** At Fold C's n=18 (4 oracle-correct
test-indices, 3 originally-selected-correct), a single additional correct
pick moves any of these numbers by 1/(oracle_hits − selected_hits) ≈ 1.0 —
this table has almost no statistical resolution and is reported as such, not
smoothed over.

### Correct-candidate rank distribution and MRR

| | mean rank | median rank | n present (of 94) | MRR |
| --- | ---: | ---: | ---: | ---: |
| B0 original | 1.90 | 1.0 | 30 | 0.247 |
| B8 oracle | 1.00 | 1.0 | 30 | 0.319 |

Figure: `artifacts/EXP002/figures/f4_rank_distribution.png`. B0's own mean
rank (1.90) is already close to 1 among the 30 test-indices where the correct
grid was generated at all — most of the headroom is concentrated in a
minority of test-indices where the correct candidate is ranked well outside
top-2 (see representative failures, `ERROR_ANALYSIS.md`), not spread evenly.

### Calibration (B7, Fold C, n=18)

| Metric | Value |
| --- | ---: |
| Brier score | 0.049 |
| Expected calibration error | 0.114 |
| Negative log-likelihood | 0.164 |
| False-confidence rate @ p>=0.8 | 0.0 (no predictions crossed 0.8) |

Figure: `artifacts/EXP002/figures/f3_reliability_diagram.png`. Brier and NLL
look good in isolation, but at n=18 that is barely distinguishable from a
constant low-confidence predictor scoring well on a mostly-negative label set
(14 of 18 wrong) — not read as evidence of good calibration, just as
"nothing here contradicts it either." Success criterion 5 ("calibration
useful enough to distinguish reliable from unreliable predictions") is
**inconclusive at this sample size.**

### Accuracy by task family, candidate-set size, margin bucket

Reported in `artifacts/EXP002/exp002_report.json` under
`baseline_reports.*.full_corpus.accuracy_by_{task_family,candidate_set_size,margin_bucket}`
and figure `f5_accuracy_by_family.png`. `size_relation="same"` (46 of 72
tasks) dominates the corpus; every other stratum has too few test-indices
(2-17) for a per-family comparison to mean anything beyond "not obviously
concentrated in one stratum." **Accuracy by solver branch is N/A**: RUN-001
used exactly one branch (`nvarc_architects_qwen3_4b`); there is no second
solver's candidates in this archive to compare against.

### Feature ablation — H1 check (Fold A+B, grid-level, n up to 487)

Figure: `artifacts/EXP002/figures/f6_feature_ablation.png`.

| Feature | AUC | n |
| --- | ---: | ---: |
| `reconstructed_score_kgmon` | **0.882** | 487 |
| `n_augmentations_producing` | 0.862 | 487 |
| `duplicate_generation_count` | 0.862 | 487 |
| `object_count_consistent_with_demo_pattern` | 0.833 | 81 |
| `set_duplicate_fraction` | 0.802 | 487 |
| `removed_colours_seen_in_demos` | 0.609 | 487 |
| `set_top_margin` | 0.591 | 479 |
| everything else | 0.29-0.53 | — |

**H1 PASSES clearly**: 6 features exceed or approach the 0.60 threshold, the
top one reaching 0.88 on n=487. This is the headline positive finding.

**But read the list carefully.** The four strongest features
(`reconstructed_score_kgmon`, `n_augmentations_producing`,
`duplicate_generation_count`, `set_duplicate_fraction`) are all, by
construction, close paraphrases of vote count and mean augmentation score —
exactly the inputs `score_kgmon` (B0's own selection formula,
`experiments/RUN001/BASELINE_SPEC.md` "Candidate scoring and ranking")
already combines. Their high AUC is evidence the *reconstruction* is accurate,
not evidence of *new* information B0 lacks. Only one feature in the top tier
is structurally independent of B0's own score:
`object_count_consistent_with_demo_pattern` (AUC 0.833) — and it is only
computable for 81 of 487 grid-rows (17%), because it requires every
demonstration pair in a task to agree on the same input-to-output
object-count delta (`structural.py`'s `structural_features`), which most
tasks in this corpus do not satisfy uniformly.

## 8. Confidence intervals

Not computed formally: Fold C's n=18 with 3-4 positive outcomes is below where
a Wilson interval would be informative beyond "wide." Reported qualitatively
throughout instead of with false-precision intervals.

## 9. Per-task breakdown

`artifacts/EXP002/exp002_report.json` — `baseline_reports.*.full_corpus.{hits,margins,ranks_of_correct_candidate}`
are per-test-index (in the archive's own iteration order); `fold_of_task`
gives every task's fold assignment for reproducing the exact split.

## 10. Failure categories

Not run through `paper/FAILURE_TAXONOMY.md`'s full G1-G6/S1-S4 automatic
labeller in this pass (that labeller is a separate, not-yet-built module);
the generation-vs-selection split it is built on is exactly what `oracle_hits`
vs `selected_hits` already measures here (branch G: 64/94 = 68.1% of
test-indices, correct grid never generated at all; branch S: 7/94 = 7.4%,
generated but not selected — see representative examples,
`experiments/EXP002/ERROR_ANALYSIS.md`).

## 11. Claims supported / weakened / rejected

| Claim | Effect |
| --- | --- |
| C2 (selection is a bottleneck distinct from generation) | Preview extended to ARC-AGI-2 by RUN-001 itself (7.4pp, contaminated+partial); this experiment adds that **model-independent features can predict which candidate is correct** (H1, AUC up to 0.88) but **does not yet show that predictive power converts into beating the frozen selector** (H2 fails at measured sample sizes). Net: C2's premise (headroom exists, is measurable from features) strengthens; the "recoverable" half is **not yet demonstrated on ARC-AGI-2**. |
| Thesis T2 (verification) | Premise holds (H1). Decisive test (H2) is inconclusive, not failed — see verdict below. |

## 12. Artifact paths

- `artifacts/EXP002/exp002_report.json` — full numeric report, every table above.
- `artifacts/EXP002/figures/f1..f7*.png` — all seven required figures.
- `src/analysis/exp002_verifier_eval.py`, `src/analysis/exp002_figures.py` — regenerate both from the frozen RUN-001 archive.
- `src/harness/` — the verifier/feature code under test.

## 13. Candidate figures

All seven delivered: `f1_accuracy_comparison`, `f2_recovered_headroom`,
`f3_reliability_diagram`, `f4_rank_distribution`, `f5_accuracy_by_family`,
`f6_feature_ablation`, `f7_margin_vs_correctness`.

## 14. Follow-up justified by the evidence

1. **A combiner restricted to score-independent features** (drop
   `reconstructed_score_kgmon`/`duplicate_generation_count`/
   `n_augmentations_producing`, which cap out at reproducing B0; keep
   `object_count_consistent_with_demo_pattern` and broaden its coverage) is
   the concrete next experiment, not a vague "try harder."
2. **A complete RUN-002** (not `TIMED_OUT`) would give Fold C ~4-5x more
   test-indices at the same 20% split fraction, which is the single biggest
   lever on this result's statistical resolution — most of what looks
   inconclusive here is a sample-size problem, not a demonstrated absence of
   signal.
3. Widen structural-feature coverage: right now most structural checks
   (`output_size_matches_expected`, symmetry, tiling) require every
   demonstration pair to agree, which most tasks fail; a per-pair-majority
   version of the same checks would cover far more than 17% of grid-rows.

## 15. Deviations from plan

1. **Fold C is far smaller than intended** (18 test-indices, not the ~24
   `docs/DATASET_AUDIT.md` §6.2's 800/200 fit/dev ratio would suggest at this
   corpus size) because RUN-001 itself only covered 72 of 120 tasks. Not a
   protocol deviation — the fold split ran correctly over the tasks that
   exist — but the consequence (near-zero statistical power on Fold C) is
   exactly why the verdict below is REDESIGN and not REJECT.
2. **B7's feature set (`LEARNED_FEATURES`, 18 names) was fixed before fitting**
   and is not itself an ablation search; the feature-ablation table (§7) is a
   per-feature AUC screen, not a search over combiner architectures. A future
   pass restricted to the score-independent subset (deviation-1's follow-up)
   is a new experiment, not a retroactive edit to this one.
3. **Confidence intervals were not computed** (§8), a planned deviation given
   n=18, recorded rather than silently omitted.

## Scope limits, stated plainly

- **This is RUN-001, not RUN-002.** Every number here is from a partial,
  contaminated, single-checkpoint archive.
- **No clean ARC-AGI-2 evidence exists in this experiment.** The mechanism
  test (§7) validates the pipeline, not the ARC-AGI-2 verifier-accuracy claim.
- **Nothing here licenses a `paper/CLAIM_LEDGER.md` claim about verifier
  accuracy.** It licenses spending more compute to find out — see §14.

---

## Verdict: REDESIGN

Per `experiments/EXP002/PLAN.md`'s three-way criteria:

- **Not CONTINUE**: criterion 1 (verifier improves over B0 on untouched
  tasks) fails — no non-oracle method beats B0 at n=94 or n=18.
- **Not REJECT**, on balance, despite matching the letter of "no non-oracle
  method consistently beats the original selector": H1 passed with real
  margin (up to 0.88 AUC on n=487), the failure mode is isolable (score-
  derived features cap at reconstructing B0; the one independent feature is
  underapplied, not absent), and Fold C's n=18 is too small to distinguish
  "no recoverable headroom exists" from "not enough data to see it." Calling
  this REJECT would treat an underpowered measurement as a confirmed null.
- **REDESIGN**, matching the preregistered trigger "structural features add
  no value beyond frequency": true as measured (structural signal is real
  but narrow), with a specific, evidence-backed redesign direction (§14) —
  restrict the combiner to score-independent features, widen structural
  coverage, retest on a complete run.

This is a judgment call between REDESIGN and REJECT, made explicit rather
than smoothed over. A reader who weighs "no method beat B0" more heavily than
the sample-size caveat would reasonably call REJECT instead; both readings
are represented above, and the underlying numbers (not this verdict label)
are what should carry into any future decision.
