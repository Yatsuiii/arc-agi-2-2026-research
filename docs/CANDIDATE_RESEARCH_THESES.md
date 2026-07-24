# CANDIDATE_RESEARCH_THESES

Three candidates, derived from the audit rather than from intuition. Each is
falsifiable, implementable on 2xT4 within a Kaggle 12-hour cap, produces a valid
submission, and is defensible beyond leaderboard tuning.

Common constraint, from `paper/COMPUTE_LEDGER.md`: we can afford roughly two
full baseline runs per week. A thesis whose decisive experiment needs more than
about four is not testable and is rejected on that basis alone.

---

# T1 — Compute-aware routing under a hard wall-clock budget

*(the failure-aware / compute-aware routing thesis)*

## 1. Central claim

Under a fixed total inference budget, allocating per-task compute according to a
cheap pre-solve difficulty estimate and an online progress signal solves
strictly more tasks than the uniform allocation every published system uses.

## 2. Novelty relative to prior work

Every system in `docs/SYSTEM_COMPARISON.md` allocates uniformly, with only
wall-clock guards. NVARC caps at 1200 s/task; the ARChitects run a fixed 128 TTT
steps and 102 refinement steps; CompressARC runs a fixed ~20 min. No system
estimates difficulty, and no published work reports a compute-versus-accuracy
curve on ARC-AGI-2 at all.

Closest prior art: TRM's `q_halt` head, which learns when to stop *within* a
task and is never used to decide *between* tasks. Nobody has repurposed it.

## 3. Theoretical motivation

The budget is a hard constraint, not a soft one, and it binds harder for us than
for anyone published: `docs/NVARC_2026_T4_BASELINE_AUDIT.md` shows the 2xT4 port
has ~1/4 the per-task compute that produced 27.64%, and its time guards will
bind. Under a binding budget, uniform allocation is optimal only if the marginal
return of compute is identical across tasks. It plainly is not: some tasks are
solved in the first beam, some are unsolvable at any budget, and the middle band
is where all the value sits. Identifying that band is the whole problem.

## 4. Baselines

Primary: the 2026 NVARC 2xT4 notebook at uniform allocation (RUN-001).
Ablation baselines: random allocation at matched total budget; oracle allocation
(upper bound); allocation by grid area alone (trivial predictor).

## 5. Minimal implementation

A scheduler wrapping the existing task queue. No model change.
(a) score tasks by deterministic statistics already computed in
`artifacts/data_audit/task_statistics.csv`; (b) run a cheap first pass at
reduced TTT and a tight DFS cutoff; (c) reallocate the remaining budget by
predicted marginal return; (d) second pass on the selected band.

## 6. Cheapest decisive experiment

**An oracle upper bound, CPU only.** Given per-task time and outcome from one
baseline run, compute the best achievable score under perfect foreknowledge at
the same total budget. If the oracle gain is under ~3 tasks out of 120, the
thesis is dead before a scheduler is written. This is part of EXP001.

## 7. Compute

One baseline run for the data (RUN-001, shared). Oracle analysis is CPU-only.
Two further runs to validate the scheduler. **Total ~3 runs.**

## 8. Expected score benefit

Modest and bounded by the oracle. Plausibly 1-4 tasks out of 120.

## 9. Expected universality

**High.** The scheduler is solver-agnostic and can be demonstrated on both the
primary baseline and TRM. It also transfers to ARC-AGI-1.

## 10. Failure risks

- The oracle gap is tiny because task difficulty is bimodal: solved fast, or
  never. This is the most likely failure and EXP001 detects it immediately.
- The difficulty signal does not predict success, so the realised gain is far
  below the oracle.
- Variance: 1-4 tasks out of 120 is inside the noise band of a non-deterministic
  decoder.

## 11. Rubric profile

accuracy weak - universality strong - progress medium - theory medium -
completeness strong - novelty medium.

## 12. Kill criteria

- Oracle gain < 3 tasks at matched budget → kill.
- No pre-solve feature reaches AUC 0.65 for predicting success on held-out
  tasks → kill the predictor arm, keep the online-progress arm.
- Realised gain < half the oracle after two attempts → report as negative.

## 13. Timeline

Week 1 EXP001 oracle (CPU). Week 2 RUN-001 + predictor fitting. Weeks 3-4
scheduler + two validation runs. Week 5 writeup.

## 14. Required figures and ablations

F5 compute-vs-accuracy, uniform / random / routed / oracle. Predictor ROC on
held-out tasks. Per-stratum breakdown by the flags in the dataset audit.
Ablation: each feature removed; online signal removed; pre-solve signal removed.

## 15. Value of a negative result

**High.** "Compute-aware routing does not help on ARC-AGI-2, because per-task
difficulty is near-binary and the marginal band is empty" is a genuinely useful
finding, backed by an oracle bound that nobody has published. It also generalises:
it tells the field to stop looking here.

---

# T2 — Model-independent verification of candidate outputs

*(the verification / candidate-selection thesis)*

## 1. Central claim

Ranking transduction candidates by the generating model's own likelihood is a
preference, not a check. Scoring candidates additionally by *model-independent
consistency with the demonstration pairs* recovers a measurable fraction of the
gap between oracle selection and realised accuracy, without task ids and without
public-set patches.

## 2. Novelty relative to prior work

Every neural ARC system in the audit ranks by its own likelihood under
augmentations — NVARC's `score_agg`, the ARChitects' product-of-experts, TRM's
halting head, CompressARC's MDL score. The verification column of
`docs/SYSTEM_COMPARISON.md` reads "none" for every system that scored on
ARC-AGI-2.

Real verification exists only on the program-synthesis side (SOAR, Barbadillo),
where a program can be executed against the demonstrations. Neither scored on
ARC-AGI-2. Nobody has asked whether the *checking* idea transfers without the
*program synthesis* that carried it.

Direct evidence the gap is real: NVARC §4.4 reports that TRM's uniquely-solved
puzzles "were not always picked by Qwen3 scoring" — correct candidates generated,
then discarded at selection.

## 3. Theoretical motivation

A likelihood scorer answers "would this model have written this grid?" It is
confidently wrong exactly where the model's prior is wrong, which is exactly
where it fails. A consistency check answers a different question — "is this grid
compatible with the relation the demonstrations exhibit?" — and its errors are
uncorrelated with the generator's. Two signals with uncorrelated errors combine
better than one, which is the whole argument, and it is testable.

Checks that need no program synthesiser: does the candidate obey the input→output
size relation the demonstrations establish? the colour-mapping pattern? the
symmetry group the demonstration outputs exhibit? does a model run in the inverse
direction reproduce the input? is the description length of
`demonstrations + candidate` lower than for rival candidates (CompressARC's
objective, and the ARChitects' abandoned ambiguity signal)?

## 4. Baselines

`score_kgmon` (the notebook default), `score_full_probmul_3` (ARChitects 2024),
first-beam, vote-only, and the oracle. All five evaluated on **identical stored
candidate sets**, so the comparison is exact.

## 5. Minimal implementation

A pure function `(demonstrations, candidate) -> features`, plus a combiner over
the existing `beam_score` and `score_aug` fields. **No GPU, no model, no
retraining.** It is a re-ranking of records already on disk.

## 6. Cheapest decisive experiment

Compute oracle@k versus realised accuracy@2 on stored candidate sets. If the
oracle gap is small, selection is not a bottleneck and the thesis dies. Part of
EXP001, and validatable *today* against CompressARC's recorded ranks
(`docs/papers/COMPRESSARC_ANALYSIS.md` §12) before any GPU run.

## 7. Compute

**One baseline run, shared with T1.** Everything after that is CPU. This is by a
wide margin the cheapest of the three theses, and every ablation is rerunnable
in seconds.

## 8. Expected score benefit

Bounded by the oracle gap. If NVARC's anecdote generalises, several tasks.

## 9. Expected universality

**Highest of the three.** The verifier is defined over `(demonstrations,
candidate grid)` and knows nothing about the generator, so it applies unchanged
to NVARC, TRM, a diffusion model, or CompressARC. Demonstrating it across two
structurally different solvers is the single strongest universality artifact
available to us (`paper/RUBRIC_SCORECARD.md` §2).

## 10. Failure risks

- The oracle gap is small: the model rarely generates the right answer and then
  discards it, so there is nothing to recover.
- The consistency features are already implicit in the likelihood score, so they
  add nothing.
- Overfitting the combiner on 120 tasks. Mitigation: fit on the training-split
  fit/dev partition (`docs/DATASET_AUDIT.md` §6.2), never on evaluation.

## 11. Rubric profile

accuracy medium - universality **strong** - progress strong - theory strong -
completeness strong - novelty **strong**.

## 12. Kill criteria

- oracle@10 minus accuracy@2 < 4 tasks out of 120 → kill.
- No consistency feature has AUC > 0.6 for discriminating correct from incorrect
  candidates → kill.
- Verifier-augmented selection does not beat `score_kgmon` on the dev split →
  report as negative and stop.

## 13. Timeline

Week 1 EXP001 on CompressARC records (CPU, validates the pipeline). Week 2
RUN-001. Weeks 2-3 feature development and dev-split fitting, all CPU. Week 4
one confirmation submission. Week 5 writeup.

## 14. Required figures and ablations

F4 oracle@k versus realised. Per-feature AUC. F7 selection-algorithm ablation
across five rankers on identical candidate sets. Cross-solver transfer table
(fit on solver 1, applied to solver 2). Failure-category breakdown of what the
verifier fixes and what it does not.

## 15. Value of a negative result

**High.** "Selection is not the bottleneck on ARC-AGI-2; the correct candidate is
usually absent, not misranked" is a clean, quantified, useful claim, and it
redirects the field toward generation. It also directly quantifies an assertion
NVARC made from a sample of 2-3 tasks.

---

# T3 — The pretraining-versus-adaptation trade-off, and equivariance as free invariance

*(the third direction, from the paper-system audit)*

## 1. Central claim

Across published ARC systems, accuracy rises with pretraining scale while
per-task adaptation shrinks, and the field has never measured the trade-off. We
claim the exchange rate is measurable, and that a large part of what pretraining
buys is **invariance that can be obtained structurally for free** rather than
purchased with 8-32x inference-time augmentation.

## 2. Novelty relative to prior work

The spectrum is real and nobody has drawn it
(`docs/papers/COMPRESSARC_ANALYSIS.md` §13):

| System | Pretraining | Per-task adaptation | Score |
| --- | --- | --- | --- |
| CompressARC | none | 76K params from scratch | 20% ARC-AGI-1 |
| TRM | 7M, 3 days x 4 H100 | full weights + new embeddings | 8% ARC-AGI-2 |
| NVARC | 4B, 27 h x 32 H100 | LoRA r=256 | 27.6% ARC-AGI-2 |
| ARChitects | 8B, 39 h x 8 H100 | LoRA r=32 | 21.7% ARC-AGI-2 |

The second half is sharper. CompressARC enforces D4 and colour equivariance
**structurally, by weight tying** (`initializers.py`). Every other system buys
the same invariance by augmenting data at training time and by scoring under
8-32 augmentations at inference time. Structural equivariance is free at
inference; augmentation is not. **Nobody has tried structural equivariance in a
pretrained transduction model.**

## 3. Theoretical motivation

Augmentation teaches invariance approximately, from data, at cost proportional
to the group size. Weight tying imposes it exactly, at zero cost. If a
meaningful share of NVARC's 8-way rescoring budget exists only to compensate for
invariance the architecture does not have, then imposing it structurally frees
that compute for search — a strictly better trade under a binding budget.

## 4. Baselines

The four systems above for the trade-off curve. For the equivariance arm: the
primary baseline at m ∈ {1,2,4,8} rescoring augmentations, versus a variant with
structurally imposed invariance at m=1.

## 5. Minimal implementation

Trade-off arm: measurement only, from published numbers plus our own runs.
Equivariance arm: modify the candidate scorer so identical-under-the-group
candidates are collapsed exactly rather than scored independently, and measure
what the augmentation budget was buying.

## 6. Cheapest decisive experiment

Sweep m ∈ {1,2,4,8} on **stored** `score_aug` values. CPU only, seconds,
zero GPU. If accuracy is flat in m, augmentation rescoring is not buying
invariance and the equivariance arm is pointless.

## 7. Compute

Trade-off arm: no new compute for the published rows; one TRM run for a matched
row. Equivariance arm: CPU for the sweep, one run to confirm.
**Total ~2 runs.**

## 8. Expected score benefit

Low directly. The value is in what it explains, not what it scores.

## 9. Expected universality

**High** for the trade-off curve — it spans four systems and two benchmarks by
construction. Medium for the equivariance arm.

## 10. Failure risks

- The published numbers are too heterogeneous to place on one axis: different
  benchmarks, different evaluation snapshots, different contamination status.
  This is a serious threat and `docs/PROJECT_STATE.md` §5 already documents part
  of it.
- Reviewers read a measurement paper as a survey.
- Structural equivariance in a pretrained model may be impossible to add without
  retraining, which we cannot afford.

## 11. Rubric profile

accuracy weak - universality strong - progress **strong** - theory strong -
completeness strong - novelty medium.

## 12. Kill criteria

- Accuracy flat in m over {1,2,4,8} → kill the equivariance arm.
- More than two of the four systems cannot be placed on a common axis with
  honest error bars → kill the trade-off arm.

## 13. Timeline

Weeks 1-2 published-number consolidation and the m-sweep (CPU). Weeks 3-4 TRM
run and equivariance prototype. Week 5 writeup.

## 14. Required figures and ablations

Pretraining-FLOPs versus accuracy, with adaptation size as point size and
contamination status marked. Accuracy versus m. Per-augmentation score
correlation matrix.

## 15. Value of a negative result

Medium. "Augmentation rescoring is not buying invariance" is useful; the
trade-off curve is descriptive either way.

---

## Ranking, and what is not yet decided

| | Cost to decide | Evidence the gap is real | Universality | Novelty | Testable on our compute |
| --- | --- | --- | --- | --- | --- |
| T2 verification | **lowest** (CPU on stored data) | direct but thin — NVARC §4.4 | **highest** | **highest** | yes, easily |
| T1 routing | low (same stored data) | indirect — nobody has tried | high | medium | yes |
| T3 trade-off | low | strong but descriptive | high | medium | yes |

**T2 is the leading candidate** on novelty, universality, decisiveness and cost.
**T1 is the strongest complement**, and shares its decisive experiment with T2 —
both are settled by the same oracle analysis on the same stored artifact, which
is why EXP001 tests both at once.

**No thesis is selected yet.** The evidence for T2 rests on one sentence in one
paper describing 2-3 tasks, and the evidence for T1 is an absence rather than a
measurement. `paper/CLAIM_LEDGER.md` A2 forbids claiming novelty before the
related-work search is logged, and honest practice forbids committing to a
thesis whose central premise is unmeasured.

EXP001 measures both premises. See `experiments/EXP001/PLAN.md`.
