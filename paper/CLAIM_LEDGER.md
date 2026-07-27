# CLAIM_LEDGER

Every claim the paper might make, and the exact evidence required to keep it.
A claim without a green evidence row does not appear in the paper.

## Status values

- `PROPOSED` — written down, no evidence yet.
- `SUPPORTED` — required evidence exists and points the right way.
- `WEAKENED` — evidence exists but is narrower than the claim. The claim text
  must shrink to match.
- `REJECTED` — evidence contradicts it. Stays in this file; may appear in the
  paper as a negative result.
- `RETIRED` — no longer relevant to the thesis we chose. Reason recorded.

## Background claims (about the field, not about our contribution)

These are claims we make in related work. Each needs a citation, not an
experiment. They are listed because getting one wrong would undermine the
motivation for our own contribution.

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| B1 | The 2025 ARC-AGI-2 public-leaderboard maximum was ~27.6% during the competition and ~29.7% shortly after. | `references/score_winners/01_nvarc/nvarc_2025.pdf` abstract, §3.5, Table 2 | SUPPORTED |
| B2 | On ARC-AGI-2, the dominant driver of NVARC's score was the synthetic-data mix, not the solver architecture. | `nvarc_2025.pdf` Fig. 1: same pipeline, 12.92% with BARC → 27.64% with more NVARC synthetic data | SUPPORTED |
| B3 | Ensembling a second, architecturally different solver (TRM) on top of the strong Qwen3-4B branch produced no measurable gain. | `nvarc_2025.pdf` §4.4: "using a Qwen3 4B submission that uses 10 hours only, with a score 27.22, adding TRM yields the same 27.22 score" | SUPPORTED |
| B4 | Test-time training is used by every strong 2025 ARC-AGI-2 system for which we have evidence. | NVARC §3.2, §4.2; ARChitects `page.md` (128 TTT steps per task); Barbadillo `docs/05_Solution_Summary.md` | SUPPORTED |
| B5 | Candidate selection, not candidate generation, is a live failure mode: correct candidates are generated and then not chosen. | `nvarc_2025.pdf` §4.4, plus our own EXP001-A: 57 of 400 ARC-AGI-1 evaluation tasks had the correct answer generated and ranked below 2 | SUPPORTED. Measured, not anecdotal, but on ARC-AGI-1. |
| B6 | ARChitects' final 2025 system underperformed its local eval estimate on the leaderboard (26% expected vs 21.67% actual), which they attribute to eval-set overfitting. | `references/score_winners/02_architects/page.md` §Final Submission's Results | SUPPORTED |
| B7 | Published 2025 ARC-AGI-2 public-eval numbers were measured on an evaluation snapshot that differs from the 2026 Kaggle evaluation files on 6 of 120 tasks. | `docs/PROJECT_STATE.md` §5 | SUPPORTED (measured locally) |

## Contribution claims

Populated once a thesis is selected. Placeholder IDs are reserved so EXP001 can
reference them.

| ID | Claim | Required evidence | Status |
| --- | --- | --- | --- |
| C1 | Independent ARC-AGI-2 solvers have materially non-overlapping solve sets, so per-task routing has real headroom. | Per-task solve vectors for >= 2 solvers on a common split; Jaccard and unique-solve counts with CIs | PROPOSED |
| C2 | A large fraction of the gap between a solver's oracle-selection accuracy and its actual accuracy is recoverable, i.e. selection is a bottleneck distinct from generation. | Candidate sets with ground-truth membership flags; oracle@k vs realised accuracy | **SUPPORTED on ARC-AGI-1** (EXP001-A: 14.25pp). **ARC-AGI-2 PREVIEW** (RUN-001: 30 generated vs 23 selected over 94 test-inputs = 7.4pp; contaminated + partial, so directional not confirmatory). EXP001-B to confirm. **"Recoverable" half STILL NOT SHOWN on ARC-AGI-2** (EXP002-B: with score-derived features excluded by enforced construction, only 1 of 14 independent features clears the AUC>0.60 signal threshold, and no V2 track's accuracy CI excludes V0's at n=18/n=94, `experiments/EXP002B/RESULTS.md`). Not rejected either — the bootstrap intervals are too wide to distinguish "no recoverable headroom" from "insufficient data," which is itself now a quantified statement, not a qualitative caveat. Resolution requires the acquisition plan in `experiments/EXP002B/CORPUS_REQUIREMENTS.md`, whose cost is now measured rather than estimated (`experiments/EXP002C2/SCALING_PROJECTION.md`: the 500-test-index target is 112-334 Kaggle quota GPU-hours via oversubscribed CompressARC acquisition, down from the pre-measurement 454-675 serial-GPU-hour figure; the 170-test-index power floor is payable in ~38 GPU-hours). `experiments/EXP002C3/RESULTS.md` tested whether CPU-orchestration tuning (thread caps, vCPU-derived concurrency) could improve on this further — it could not (verdict KEEP FROZEN C3); the ~38/112-334 GPU-hour figures are therefore the stable planning basis, not a placeholder pending further throughput engineering. **Acquisition is now COMPLETE**: ACQ-001 (`experiments/ACQ001/FINAL_CORPUS_REPORT.md`) acquired both shards of the 171-index clean TEST corpus under identical frozen C3, 0 leakage, 73,489 combined archive records, disjoint task-ID sets whose union matches the frozen TEST corpus exactly. Combined offline oracle analysis (n=171, now meeting the pre-registered power floor) found 24.56% full-candidate-set oracle coverage vs. 13.45% top-2 selection accuracy — an 11.1pp gap in the same direction as the RUN-001 preview and both shards individually, consistent with but still not confirmatory of C2's "recoverable" half (this combined measurement itself is not a verifier-training result — it only shows correct answers exist in the beam more often than CompressARC's own heuristic selects them). **EXP002-D (`experiments/EXP002D/RESULTS.md`) then ran exactly that verifier-evaluation pass and found the "recoverable" half NOT SUPPORTED**: 6 verifier tracks (score-independent pointwise/pairwise, hybrid pointwise/pairwise, rule ensemble) were fit under preregistered task-grouped 5-fold CV at n=171 (meeting the pre-registered power floor). Every non-trivial track scored *below* the frozen native baseline (13.45% top-2), most by a statistically significant margin (McNemar p<0.05 for 4 of 5 tracks); oracle-gap recovery was negative for every track. This closes the "insufficient data" ambiguity EXP002-B left open — at the pre-registered power floor, with real feature engineering (structural/train-consistency/relational groups) and model families (logistic regression, gradient-boosted trees, linear pairwise ranking) tried, no tested approach recovered any of the 11.1pp gap. **Verdict: FREEZE VERIFIER RESEARCH.** Orthogonally, and regardless of C2's status: 75.44% of held-out test-indices have no correct candidate in the archive at all, a generation-side ceiling that bounds any selection mechanism's maximum possible value (`docs/POST_ACQ001_STRATEGIC_DECISION.md`). **GEN001-A** (`experiments/GEN001A/PLAN.md`) is CPU-only preflight for the generation-side follow-on this points at: a possible NVARC-lineage generator pilot testing whether a second, architecturally distinct generator produces correct candidates on the 129 test-indices CompressARC does not. No pilot has run — this phase built and locally validated (never launched) a 24-index pilot kernel restricted to a checkpoint independently found **SCIENTIFICALLY CONTAMINATED** against all 160/160 ACQ-001 tasks (`experiments/GEN001A/CONTAMINATION_AUDIT.md`); no accuracy or coverage number from it may ever enter this ledger as clean evidence, and any future pilot result is permanently contamination-labelled and barred from the EXP002-D clean-verifier corpus. |
| C2-confidence | A verifier's reported confidence can be repaired to reflect genuine uncertainty (not merely relative ranking) even without a resolved verification-accuracy result. | Before/after measurement of false-confidence rate on a known failure mode | **SUPPORTED** (EXP002-B Part 1: singleton-candidate false-confidence rate measured at 77.8% pre-fix, undefined/absent post-fix, `experiments/EXP002B/CONFIDENCE_SEMANTICS.md`). New sub-claim, split from C2 because it does not depend on C2's own resolution. |
| C3 | Task-level features computable before running an expensive solver predict that solver's success well enough to reallocate compute profitably. | Predictive AUC on held-out tasks + a compute-vs-accuracy curve beating uniform allocation | **HEADROOM SUPPORTED on ARC-AGI-1** (EXP001-A: oracle allocation matches full-budget accuracy at 1/8 the compute). The predictor half is still PROPOSED. |

## Anti-claims

Things we will explicitly not claim, recorded so we do not drift into them.

| ID | Anti-claim | Reason |
| --- | --- | --- |
| A1 | We will not claim state-of-the-art on ARC-AGI-2 without a rerun-mode Kaggle score. | Local eval on the 120-task public set is contaminated for any NVARC-derived checkpoint (`docs/REFERENCE_LICENSE_AUDIT.md` §1) and differs from the semi-private set. |
| A2 | We will not claim novelty for any component before `paper/RELATED_WORK.md` records a search for it. | Phase 11 precondition. |
| A3 | We will not present a "combine everything" ensemble as a scientific contribution. | B3 shows naive ensembling did not even help the people who tried it, and component contributions would not be separable. |
| A4 | We will not report improvements tuned against the Kaggle public leaderboard. | Public LB is half the hidden set; tuning on it is the exact overfitting mode B6 documents. |

## New claim from EXP001-A

| ID | Claim | Required evidence | Status |
| --- | --- | --- | --- |
| C4 | Running a per-task solver to its full budget can *lose* correct answers it had already ranked into the top 2, so knowing when to stop is a distinct lever from knowing how to rank. | Per-task rank trajectories over the compute budget | **SUPPORTED on ARC-AGI-1** (EXP001-A: 10 of 400 evaluation tasks, 2.5pp, an eighth of the solver's score). Unplanned finding; needs replication on ARC-AGI-2. |
| C5 | A bounded typed object-centric program synthesizer provides clean incremental candidate coverage on CompressARC's ARC-AGI-2 generation failures. | Candidate oracle union on a frozen clean pilot, with generation isolated from ground-truth analysis | **REJECTED for GEN002-A's frozen DSL/search configuration**: 0/12 Group-A rescues, 0 candidates emitted across 24/24 completed pilot indices (`experiments/GEN002A/RESULTS.md`). This does not reject program synthesis as a family; broader language/search variants require a new preregistration and sample. |
