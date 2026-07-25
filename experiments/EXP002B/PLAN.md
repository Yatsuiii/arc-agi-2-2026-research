# EXP002-B — PLAN (preregistration)

Preregistered before this pass's implementation began. Follows directly from
`experiments/EXP002/RESULTS.md`'s verdict (**REDESIGN**) and the user's
explicit acceptance of it. Not a restart: it inherits EXP002's H0/H1
machinery and corpus, and narrows the question.

## 1. Experiment identifier

`EXP002-B` — Score-independent verification and confidence repair.

## 2. Research question

Can evidence independent of NVARC's native score identify trustworthy
candidates and produce calibrated confidence suitable for later stopping and
compute allocation?

This narrows EXP002's question in two ways EXP002's own results demanded:
(1) "independent" is now enforced, not just intended — EXP002's strongest
features turned out to be paraphrases of the frozen selector's own formula
(`paper/CLAIM_LEDGER.md` C2's updated entry); (2) "confidence suitable for
... allocation" is now a real question, not an assumption — EXP002's error
analysis found the confidence signal itself was broken on singleton candidate
sets.

## 3. Falsifiable hypotheses

Same three-part structure as EXP002, re-scoped:

**H0 (pipeline, inherited).** `assign_folds`, `feature_auc_table`, and the
V0-V3 evaluation reproduce EXP002's own H0 check (30/94 oracle, 23/94
selected, 7.45pp) exactly, since this pass reuses the same RUN-001 archive.
Precondition; failure stops everything below.

**H1 (independent signal).** At least one feature in
`features.independence.INDEPENDENT_FEATURES` — evaluated alone, with every
`SCORE_DERIVED_FEATURES` name excluded by construction — has AUC > 0.60 on
Fold A+B. This is a re-test of EXP002's H1 under the exclusion EXP002 did not
enforce: EXP002's top features were score-derived, so this asks whether
anything survives once they are removed.

**H2 (recoverable gain, re-scoped).** V2 (score-independent, heuristic or
learned) recovers >= 2pp of selection accuracy over V0 on Fold C. Same
threshold as EXP002's H2; the change is which features may produce it.

**H3 (confidence validity, new).** On singleton candidate sets specifically,
`correctness_confidence` is closer to the corpus's measured base rate than
the pre-fix `probability_correct` was (which was always exactly 1.0). This is
a mechanical check on the Part-1 fix, not a claim requiring new data.

## 4. Theoretical motivation

Unchanged from `experiments/EXP002/PLAN.md` §4 for the verification question;
extended for confidence: an allocator (EXP003+, still gated) that reads
`uncertainty`/`probability_correct` as a stopping signal needs those numbers
to mean the same thing across every candidate-set shape it will encounter,
including the shape (singleton) that occurs on 9 of 94 RUN-001 test-indices —
9.6% of the corpus, not a corner case.

## 5. Relationship to prior work

`experiments/EXP002/RESULTS.md` is the direct antecedent; every number and
finding cited above traces to it. No new external reference material.

## 6. Exact baseline

Same RUN-001 archive as EXP002 (`artifacts/run001/run001/`), same
COMPETITION-ENGINEERING/CONTAMINATED/PARTIAL status
(`experiments/RUN001/RESULTS.md`). No new candidates generated — the corpus
is unchanged; only the verifier and confidence code under test changed.

## 7. Exact intervention

Four V0-V3 tracks (`src/harness/verifier/independent.py`), the confidence
fields fix (`src/harness/verifier/base.py`), and
`features.independence.assert_score_independent` enforcement. Fold protocol
(stratify-by-`size_relation`, seed `20260725`) unchanged from EXP002 so
results are directly comparable.

## 8-10. Training / validation / held-out splits

Identical to `experiments/EXP002/PLAN.md` §§8-10: Fold A fit, Fold B
calibration, Fold C untouched final eval. Unchanged fold assignment (same
seed, same stratification) so V0-V3's Fold C numbers are the same 18
test-indices EXP002's B0-B8 were scored on — a same-corpus, same-split
re-evaluation is precisely what makes "did fixing the bug and restricting the
features change the answer" a fair question.

## 11. Leakage risks

Identical to `experiments/EXP002/PLAN.md` §11, plus: the independence
enforcement itself is a leakage-adjacent risk — `assert_score_independent`
checks feature *names*, not feature *values*, so a new feature that is
numerically correlated with score without being named similarly would not be
caught. Recorded as a known limitation of the check, not silently assumed
away.

## 12. Compute budget

CPU only, no GPU, no network — identical to EXP002 (`experiments/EXP002/RESULTS.md`
§5, 2.05s). No new candidates generated, per this session's explicit scope.

## 13. Success criterion

`experiments/EXP002B/RESULTS.md`'s own criteria (verbatim from the user's
instructions): V2 beats V0 on Fold C; the gain does not depend on
score-reconstruction (enforced structurally, not just checked post hoc);
correctness confidence is calibrated enough for selective stopping; singleton
sets are not falsely confident; selective accuracy rises as V2 abstains;
gains survive feature ablation; runtime stays negligible.

## 14. Kill criterion

REDESIGN again if structural evidence shows signal but the corpus remains
underpowered (the most likely outcome given `CORPUS_REQUIREMENTS.md`'s own
power analysis says Fold C needs >=100 test-indices and RUN-001 provides 18).
REJECT if V2 cannot beat V0 on a sufficiently large clean corpus, calibrated
confidence does not correlate with correctness, or gains vanish under
family-held-out evaluation on real data (not just this underpowered pass).

## 15. Intended paper claim

Same target as EXP002 (`paper/CLAIM_LEDGER.md` C2), narrowed: this pass can
at most extend or further qualify C2's "recoverable half... NOT YET SHOWN"
entry; it cannot resolve it, because the corpus has not changed size.

## 16. Possible negative interpretation

Most likely, and explicitly expected going in (this is why Part 4 exists):
V2 shows H1 signal (independent features do carry information) but H2 still
fails on Fold C's 18 test-indices, for the same statistical-power reason as
EXP002 — in which case this pass's contribution is the confidence fix and the
independence enforcement (real, structural, reusable), not a resolved
verifier-accuracy claim, and the honest next step is acquisition
(`CORPUS_REQUIREMENTS.md`), not another redesign of the same undersized
corpus.

---

## Execution

```
python -m src.analysis.exp002b_verifier_eval
python -m src.analysis.exp002b_figures
```

Not executed until this file is committed, per `paper/EXPERIMENT_REGISTRY.md`
rule 1.
