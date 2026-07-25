# EXP002 — PLAN (preregistration)

Preregistered before execution. Not edited after the run; deviations go in
`RESULT.md`. **Not executed.** This file exists to lock the design in before
RUN-001's artifacts are even downloaded, so nothing here can be tuned to a
result that is already known.

## 1. Experiment identifier

`EXP002` — Model-independent candidate verification feasibility.

## 2. Research question

Can transformation-consistency, augmentation agreement, and demonstration-fit
signals rerank an already-generated candidate set better than NVARC's frozen
selector (`score_kgmon`), without generating a single new candidate?

This is thesis T2's cheapest decisive experiment
(`docs/CANDIDATE_RESEARCH_THESES.md` §T2.6), narrowed by EXP001-A's finding
that selection headroom exists on ARC-AGI-1 (`experiments/EXP001/RESULT.md`
§14.3): the open question is no longer *whether* headroom exists but whether a
*model-independent* signal — one that does not know which model generated the
candidates — can capture any of it.

## 3. Falsifiable hypotheses

**H1 (feature signal).** At least one model-independent verifier feature
(§9 below) has AUC > 0.60 for discriminating correct from incorrect candidates
on the fit/dev split, computed per `docs/DATASET_AUDIT.md` §6.2.

**H2 (reranking gain).** A verifier-augmented reranker — the frozen
`score_kgmon` ordering combined with verifier features, still no retraining of
the generator — recovers at least **2 percentage points** of accuracy@2 over
the frozen NVARC selector on the same stored candidate sets, on the held-out
evaluation split.

**H0 (pipeline).** `src.analysis.candidate_headroom` reproduces, from the
archived per-candidate records, the same `realised@2` accuracy NVARC's own
`submission.json` encodes for every task where ground truth is available. This
is a precondition; if it fails, the archive is not being read correctly and H1
and H2 are not trustworthy.

Each hypothesis is falsified by the measurement falling below its threshold.

## 4. Theoretical motivation

Every neural ARC-AGI-2 system in the audit ranks candidates by the generating
model's own likelihood (`docs/SYSTEM_COMPARISON.md`, verification column reads
"none" throughout). A likelihood scorer is confidently wrong exactly where the
model's prior is wrong — which is exactly where it fails. A model-independent
consistency check asks a different question ("is this grid compatible with the
relation the demonstrations exhibit?") whose errors are not correlated with
the generator's. Two signals with uncorrelated errors combine better than one;
that is the whole argument, and it is what H1/H2 test
(`docs/CANDIDATE_RESEARCH_THESES.md` §T2.3).

## 5. Relationship to prior work

- NVARC `nvarc_2025.pdf` §4.4: TRM's uniquely-solved puzzles "were not always
  picked by Qwen3 scoring" — anecdotal, n≈2-3, the direct motivating evidence.
- EXP001-A (`experiments/EXP001/RESULT.md`): 14.25pp of selection headroom
  measured on ARC-AGI-1/CompressARC. Establishes the premise holds somewhere;
  does not establish it on a real LLM decoder's candidate distribution, which
  Stage B (RUN-001) does.
- Program-synthesis verification (SOAR, Barbadillo) executes candidate
  programs against demonstrations directly. Neither scored on ARC-AGI-2, and
  neither transfers to a grid-generating LLM with no program to execute — the
  gap this experiment addresses.
- No published system reports a model-independent verifier result on
  ARC-AGI-2 candidates.

## 6. Exact baseline

RUN-001's archived candidate records (`src/run001/archive.py` schema, joined
by `src.analysis.candidate_headroom.join_candidates_and_selection`):
`candidates.jsonl.gz` (per-candidate `grid`, `beam_score`, `score_aug[8]`,
`score_aug_mean`) and `candidates.ranking.jsonl.gz` (NVARC's own
`rank_after_aggregation` and `selected` flag under `score_kgmon`). Ground truth
from `arc-agi_evaluation_solutions.json` where legally available
(`README.md` "Data policy"). One fixed artifact; not regenerated per
iteration.

## 7. Exact intervention

None yet committed to code beyond feature *definitions*. EXP002 computes, per
candidate, a small set of features that require no generator and no retrained
model (§9), then compares five **frozen** rerankings of the identical stored
candidate set:

1. NVARC's own selection (`selected` / `rank_after_aggregation` as archived).
2. Raw `score_kgmon`-equivalent ordering reconstructed from `beam_score` /
   `score_aug` (no verifier features).
3. Majority / duplicate-frequency vote (rank by generation-vote count alone).
4. Augmentation-consensus ordering (rank by cross-augmentation agreement
   alone, §9).
5. Oracle selector (upper bound: picks the correct candidate whenever it was
   generated at all).

A verifier-augmented reranker (features + `score_kgmon`, combined by the
simplest model that fits — logistic regression or a fixed linear combination,
**not** a large model, item 10 below) is fit on the dev partition and
evaluated against these five frozen baselines on held-out.

## 8. Training split

The verifier-augmented reranker's combiner weights are fit on the ARC-AGI-2
training-split fit/dev partition (`docs/DATASET_AUDIT.md` §6.2) — never on the
120-task evaluation split RUN-001 scores. This is the one place EXP002 fits
anything; every frozen baseline in §7 needs no fitting at all.

## 9. Validation split

The same fit/dev partition, used to select which verifier features clear the
H1 AUC threshold before any evaluation-split number is looked at. Candidate
verifier features considered:

- consistency across augmentations (`score_aug` spread — implemented as
  `candidate_headroom.augmentation_agreement`, already available)
- duplicate-support count (generation vote count per unique grid — already
  available as `n_unique_grids` / `n_candidates` per task)
- transformation consistency across demonstration pairs (does the candidate
  obey the input→output relation the demonstrations exhibit under the same
  augmentation)
- output-size consistency (candidate shape vs. the demonstrations' size
  relation)
- colour-preservation statistics (candidate's colour multiset vs. the
  demonstrations' colour-mapping pattern)
- geometric invariants (symmetry group of demonstration outputs vs. candidate)
- candidate-score calibration (`score_aug_mean` reliability against realised
  correctness on fit/dev)
- rank stability across scoring variants (does the candidate's rank move
  under `score_full_probmul_3` vs. `score_kgmon`; both are computable from
  archived `beam_score`/`score_aug`)

**Agreement across TTT seeds is listed as a candidate feature in the broader
research program but is not computable from the RUN-001 artifact**: the frozen
baseline uses a single fixed TTT seed (`BASELINE_SPEC.md` "Seeds", seed=1), so
there is only one seed's worth of adapted weights to agree with. It is
recorded here as infeasible with this artifact, not silently dropped —
revisiting it would need a second TTT run with a different seed, which is a
GPU cost this experiment does not spend.

## 10. Held-out evaluation split

RUN-001's 120-task ARC-AGI-2 evaluation split, touched once, after every
feature and the combiner are frozen on fit/dev. Reported as **CONTAMINATED**
for the checkpoint's own accuracy (`RUN001/PLAN.md` §5) — but H1/H2 are about
*relative* reranking gains over the same contaminated candidate set NVARC
itself scored, so the contamination affects all five §7 baselines identically
and does not favor the verifier.

## 11. Leakage risks

| Risk | Assessment |
| --- | --- |
| Checkpoint trained on the eval split | Inherited from RUN-001; affects generation, not this experiment's relative comparison (all baselines share the same candidate set) |
| Combiner overfits the evaluation split | Mitigated structurally: weights are fit only on fit/dev (`docs/DATASET_AUDIT.md` §6.2); evaluation is touched once |
| Verifier features leak the answer (e.g. using ground truth to build a feature) | Every feature in §9 is a pure function of `(demonstrations, candidate grid)` and archived scores — never of the solutions file. Enforced the same way `src/run001/archive.py` enforces no-ground-truth archiving: a static check on the feature functions' argument lists before Stage 1 execution |
| Reusing RUN-001's own selection to build a feature that just reproduces `score_kgmon` | Feature §9's "rank stability" uses `score_kgmon` as an *input* to test disagreement, not as a label; H1/H2 explicitly compare against it as a baseline, not fold it invisibly into the verifier |

## 12. Compute budget

**CPU only, entirely on RUN-001's already-spent GPU artifact.** No GPU, no
network, no new Kaggle run. Expected wall-clock: seconds to low minutes,
consistent with EXP001 Stage A (19.8s) and `AB-S1`/`AB-S2`
(`paper/ABLATION_MATRIX.md`), which read the same kind of archived per-candidate
records.

## 13. Success criterion

- H0: `candidate_headroom`'s reconstructed `realised@2` matches
  `submission.json`'s actual attempt_1/attempt_2 identities for every task with
  available ground truth, exactly.
- H1: >= 1 feature with AUC > 0.60 on fit/dev.
- H2: verifier-augmented reranker >= frozen `score_kgmon` + 2pp accuracy@2 on
  held-out evaluation.

## 14. Kill criterion

- H0 fails -> stop; the join between `candidates.jsonl.gz`,
  `candidates.ranking.jsonl.gz` and `submission.json` is wrong and nothing
  downstream is valid.
- No feature clears AUC > 0.60 on fit/dev -> H1 killed; do not proceed to
  fitting a combiner (§14 of `docs/CANDIDATE_RESEARCH_THESES.md` §T2.12,
  restated here as the local kill gate).
- Verifier-augmented reranker does not beat frozen `score_kgmon` by >= 2pp on
  held-out -> H2 killed; report as negative
  (`docs/CANDIDATE_RESEARCH_THESES.md` §T2.15 — a clean negative result in its
  own right, since it would mean selection headroom exists but is not
  recoverable without the generator's own likelihood).

## 15. Intended paper claim

Targets `paper/CLAIM_LEDGER.md` C2 (selection is a bottleneck distinct from
generation) extended from ARC-AGI-1 to ARC-AGI-2, and is the decisive
experiment for thesis T2. Feeds figure F7 (selection-algorithm ablation,
`paper/FIGURE_REGISTRY.md`) and is the natural home for a new feature-AUC
figure once features are implemented.

## 16. Possible negative interpretation

The most likely negative outcome, symmetric to EXP001-A's preregistered one:
selection headroom exists (oracle@k exceeds realised@2, as EXP001-A already
found on ARC-AGI-1) but none of the model-independent features in §9
correlate with correctness above chance-plus-a-hair on this checkpoint's
candidate distribution — i.e. whatever makes a candidate wrong is not visible
without the generator's own likelihood, so `score_kgmon` is already capturing
what can cheaply be captured, and the headroom is only recoverable by a signal
that models the generator (defeating the "model-independent" premise). That
would kill T2 as scoped and redirect toward T1 (compute-aware routing) or a
generator-aware verifier, which is a different, more expensive thesis.

A weaker negative: features clear the AUC bar (H1 holds) but the combiner does
not beat `score_kgmon` by the 2pp threshold on held-out (H2 fails) — signal
exists but is already subsumed by what NVARC's own selector captures. Also
worth reporting; it bounds how much more selection alone can buy.

---

## Execution

**Not executed. Blocked on RUN-001.**

Preconditions, all must hold before any code in this plan runs:

1. RUN-001's Kaggle kernel has reached a terminal state (`KernelWorkerStatus`
   `COMPLETE`, not `RUNNING` or `QUEUED`) — checked read-only via
   `src/run001/download_outputs.kernel_status`.
2. Outputs downloaded and checksummed via `src/run001/download_outputs.ingest`.
3. `src/run001/validate_outputs.validate` reports `"ok": true` (or, at minimum,
   a classification of `COMPLETE` or `PARTIAL` with `problems == []` — a
   `FAILED` or `TIMED_OUT`-with-hard-problems classification blocks EXP002
   until the cause is understood and recorded).
4. `experiments/RUN001/RESULT.md` exists, recording what actually happened.

Once unblocked, Stage 1 (H0 pipeline check + feature computation on fit/dev)
runs as:

```
python -m src.analysis.candidate_headroom artifacts/run001 --split evaluation
```

Stage 2 (combiner fitting and the H1/H2 measurement) is not yet implemented;
its module and exact command will be added in the commit that executes this
plan, not before, per `paper/EXPERIMENT_REGISTRY.md` rule 1.
