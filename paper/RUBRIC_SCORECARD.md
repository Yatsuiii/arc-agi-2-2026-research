# RUBRIC_SCORECARD

The ARC Prize paper track scores on accuracy, universality, progress toward
solving ARC, theory, completeness and novelty. This file names, per category,
the concrete artifact our paper must contain. Anything not listed here is not
evidence.

Self-assessment scale: `NONE` / `WEAK` / `ADEQUATE` / `STRONG`. Current column
reflects what exists in this repository today, which at the end of the audit
phase is essentially nothing. That is the point of writing it down early.

## 1. Accuracy

What counts: a number on a split we did not train or select on, with the split
and the snapshot named, and a confidence interval.

| Required artifact | Where it will live | Current |
| --- | --- | --- |
| Kaggle rerun score of the primary baseline, unmodified | `paper/EXPERIMENT_REGISTRY.md` + Kaggle submission id | NONE |
| Kaggle rerun score with our intervention, same seed policy | same | NONE |
| Local score on a split with a documented contamination status | `artifacts/` per experiment | NONE |
| Wilson or bootstrap CI on every accuracy number (n=120 means ±~8pp at 25%) | table generator in `src/` | NONE |
| Explicit statement of which evaluation snapshot produced each number | `docs/PROJECT_STATE.md` §5 already establishes the two snapshots differ | ADEQUATE |

Risk: with 120 public eval tasks, a 3-task swing is ~2.5pp and well inside
noise. **Any claim resting on fewer than roughly 10 tasks of difference on this
split is not defensible.** Design experiments accordingly.

## 2. Universality

What counts: evidence the method is not ARC-AGI-2-public-eval-specific.

| Required artifact | Where it will live | Current |
| --- | --- | --- |
| Same method evaluated on ARC-AGI-1 evaluation as well as ARC-AGI-2 | experiment plan | NONE |
| Method stated without reference to task ids, and code grep proving no task-id branching | `src/` + a test | NONE |
| Performance broken down by task family (see `docs/DATASET_AUDIT.md`) rather than aggregate only | `artifacts/data_audit/` feeds this | NONE |
| Applied across at least two structurally different solvers, not one | ties to C1 | NONE |
| Honest statement of the input assumptions the method needs | paper §limitations | NONE |

The single strongest universality artifact available cheaply: showing the method
works when the underlying solver is swapped. A routing or verification method
that only works for one checkpoint is a tuning result, not a contribution.

## 3. Progress toward solving ARC

What counts: an argument that the bottleneck we address is a real one, plus
evidence about what remains after we address it.

| Required artifact | Where it will live | Current |
| --- | --- | --- |
| Failure taxonomy applied to real predictions, with counts | `paper/FAILURE_TAXONOMY.md` | STRUCTURE ONLY |
| Oracle/ceiling analysis: what score would perfect selection give | EXP001 | NONE |
| Statement of what our method does *not* fix and why that is the next bottleneck | paper §discussion | NONE |
| Compute-versus-accuracy curve, so the result is not just "more compute" | ties to C3 | NONE |

## 4. Theory

What counts: a stated mechanism that predicts the result before it is measured,
and at least one prediction that could have come out wrong.

| Required artifact | Where it will live | Current |
| --- | --- | --- |
| A written mechanism, in the preregistration, before the run | `experiments/*/PLAN.md` field 4 | STRUCTURE ONLY |
| A prediction the mechanism makes that a plausible rival mechanism does not | plan field 3 | NONE |
| Post-hoc check of whether the mechanism, not just the outcome, held | `RESULT.md` field 11 | NONE |

Weakest category by default for competition-derived work. Most ARC solution
reports state what was done, not why it should work. Preregistering the
mechanism is the cheapest way to be genuinely stronger here than the field.

## 5. Completeness

What counts: someone else can rerun it.

| Required artifact | Where it will live | Current |
| --- | --- | --- |
| Every external SHA pinned | `docs/PROJECT_STATE.md` §6 | STRONG |
| Every licence resolved before use | `docs/REFERENCE_LICENSE_AUDIT.md` | ADEQUATE (2 open questions) |
| Seeds, hardware, runtime recorded per run | `paper/REPRODUCIBILITY.md`, `paper/COMPUTE_LEDGER.md` | STRUCTURE ONLY |
| Negative results reported | `paper/EXPERIMENT_REGISTRY.md` rule 3 | STRUCTURE ONLY |
| Ablations for each claimed component | `paper/ABLATION_MATRIX.md` | STRUCTURE ONLY |
| Public repository with a permissive licence | this repo, licence not yet chosen | NONE |

## 6. Novelty

What counts: a related-work search that could have found prior art and did not,
recorded before the claim is made.

| Required artifact | Where it will live | Current |
| --- | --- | --- |
| Related work with per-idea attribution, not per-paper summaries | `paper/RELATED_WORK.md` | ADEQUATE for 2025 systems |
| Explicit "closest prior work" paragraph naming the nearest method and the delta | `paper/RELATED_WORK.md` | NONE |
| Record of the search: what was queried, when, what was found | `paper/RELATED_WORK.md` §search log | NONE |
| Check against the ARChitects' and NVARC's "things that didn't work" lists | see `docs/systems/ARCHITECTS.md` | ADEQUATE |

Note a live novelty hazard: the ARChitects tried and abandoned large-scale
synthetic data, hierarchical architectures, reasoning tokens, Canon layers and
H-Net-style architectures (`references/score_winners/02_architects/page.md`
§Things That Didn't Work). NVARC tried and abandoned TRM ensembling. Proposing
any of these without a specific reason their version failed is not novelty.

## Rollup

| Category | Current | Target at submission |
| --- | --- | --- |
| Accuracy | NONE | ADEQUATE |
| Universality | NONE | STRONG |
| Progress | NONE | ADEQUATE |
| Theory | NONE | STRONG |
| Completeness | ADEQUATE | STRONG |
| Novelty | NONE | ADEQUATE |

Deliberate shape: we are unlikely to win on raw accuracy against teams with
8xH100 clusters. Universality, theory and completeness are the categories where
a careful small-compute project can actually be best in class, so the thesis we
pick should be one that is strong there even if the accuracy delta is modest.
