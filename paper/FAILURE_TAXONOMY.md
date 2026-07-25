# FAILURE_TAXONOMY

A task-level failure taxonomy usable across heterogeneous ARC solvers, plus the
protocol that makes labelling reproducible.

## Design constraint

Categories were not invented from intuition. Each is grounded in a failure mode
that a reference system documents about itself, or in a distinction that is
mechanically decidable from artifacts a solver already produces. Categories that
are neither are marked `PROVISIONAL` and must be validated against real
predictions before they are used in the paper.

## The decision that shapes everything: generation vs selection

A solver that produces k candidates and picks 2 has two independent ways to
fail. Splitting them is the first cut, because it is decidable without any
semantic judgement:

```
Was the correct grid anywhere in the candidate set?
├── NO  → GENERATION FAILURE  (branch G)
└── YES → SELECTION FAILURE   (branch S)
```

This split is directly evidenced. NVARC25 §4.4: TRM-solved puzzles "were not
always picked by Qwen3 scoring". ARCH25 measured 30.5% with the true shape given
versus 21.67% realised — a gap that is partly a shape-prediction failure, which
is a specific generation failure (G4 below).

## Branch G: generation failures

The correct grid was never produced.

| ID | Category | Evidence grounding | Automatic rule available |
| --- | --- | --- | --- |
| G1 | Output-size prediction failure | ARCH25 built a dedicated shape model, ~85% accurate; multiplicative with content accuracy | **Yes.** No candidate has the ground-truth shape. |
| G2 | Correct shape, wrong content, small edit distance | ARCH25 "issues with diagonal line predictions" | **Yes.** Best candidate matches shape, Hamming distance ≤ 5% of cells. |
| G3 | Correct shape, wrong content, large edit distance | — | **Yes.** Shape matches, Hamming > 5%. Distinguishes "nearly right rule" from "wrong rule". |
| G4 | Degenerate output (copy of input, constant fill, empty) | — | **Yes.** Best candidate equals an input grid, or is single-coloured. Signals the solver found no rule at all. |
| G5 | No parseable candidate produced | `nvarc_t4x2_notebook.py:88-102` returns `None` on unparseable decodes | **Yes.** Candidate set empty. |
| G6 | Compute exhaustion | Notebook enforces a 1200s per-puzzle and 540s per-DFS cap | **Yes.** Task hit a time or step limit before finishing. Must be logged by the solver. |

G1-G4 are mutually exclusive and jointly exhaustive given a non-empty candidate
set, which is what makes them safe to automate.

### G6 and verifier confidence: a measured interaction

`experiments/EXP002B/ERROR_ANALYSIS.md` found that G6 (compute exhaustion) has
a specific, measurable failure signature at the candidate-set level: a task
that hits its time guard early enough sometimes yields exactly one unique
candidate (9.6% of RUN-001's 94 test-indices). A verifier that naively
softmaxes over whatever candidates exist reports maximal confidence on
exactly these cases — 100% "confidence," 77.8% actually wrong, measured
directly (`experiments/EXP002B/CONFIDENCE_SEMANTICS.md`). This is a G6
symptom wearing a selection-confidence costume, the same pattern S3/S4 were
defined to keep separate from genuine selection failure: **a verifier cannot
rerank its way out of a task that only generated one candidate**, and
reporting high confidence there is a bug in the verifier, not evidence about
the task. `VerificationResult.abstain`/`candidate_set_sufficiency`
(`src/harness/schemas.py`) is the fix, and it is now the automatable rule for
detecting this specific G6/confidence interaction: `abstain=True` and
`n_unique_candidates <= 1` together are sufficient to flag it in any future
per-task labelling pass.

## Branch S: selection failures

The correct grid was generated and not chosen.

| ID | Category | Distinguishing rule |
| --- | --- | --- |
| S1 | Correct candidate ranked 3rd or lower | rank(correct) > 2 |
| S2 | Correct candidate ranked 3rd only (near miss) | rank(correct) == 3 |
| S3 | Scorer preferred a candidate the augmented views disagree on | variance of `score_aug` for the chosen candidate exceeds that of the correct one |
| S4 | Tie / non-determinism | correct and chosen candidates score within float tolerance; ties to the batched-DFS non-determinism NVARC25 §3.3 documents |

S1-S2 are decidable from the candidate list. S3-S4 need the per-augmentation
scores, which the 2026 notebook already persists (`score_aug` in the bz2
pickles) — so they are cheap for any solver we control, and unavailable for
solvers we do not.

## Branch T: task-property labels (orthogonal, multi-label)

These are properties of the *task*, not of a failure, and a task may carry
several. They exist so that failure counts can be conditioned on task type,
which is what the universality rubric needs. They are `PROVISIONAL` until
computed over the real corpus by `src/data_audit/`.

| ID | Property | How derived |
| --- | --- | --- |
| T1 | Output shape differs from input shape | deterministic, from grids |
| T2 | Output shape varies across demonstration pairs | deterministic |
| T3 | Colour palette changes between input and output | deterministic |
| T4 | Object count changes | needs a connected-component definition; fix one and state it |
| T5 | Demonstrations are ambiguous (more than one simple rule fits) | **not automatable**; human review only |
| T6 | Few demonstrations (n ≤ 2) | deterministic |
| T7 | Large grids (any dimension > 20) | deterministic |
| T8 | Multi-step composition | human review; `PROVISIONAL` |

## Explicitly rejected categories

Named so they do not creep back in. Each was in the candidate list in the task
brief and is rejected for a stated reason:

| Rejected | Reason |
| --- | --- |
| "object extraction failure", "object correspondence failure" | Not decidable from a solver's output. They describe an internal state that neural transduction solvers do not expose. Usable only for a solver with an explicit object representation, which none of our references has. |
| "incorrect transformation hypothesis" | Not distinguishable from G3 without reading the solver's mind. G3 is the observable version. |
| "counting failure", "symmetry failure", "topology failure" | These are *task* properties (branch T), not failure modes. Recording them as failures conflates what the task needed with what the solver did. |
| "test-time overfitting", "augmentation inconsistency", "verifier failure" | These are *hypotheses about causes*. They must be earned by an experiment, not assigned by a labeller. S3 is the observable proxy for the last two. |

This is the main methodological point of this file: **label what is observable,
infer causes with experiments.** A taxonomy whose categories are causal
hypotheses cannot be used to test causal hypotheses.

## Labelling protocol

### Automatic (G1-G6, S1-S4, T1-T3, T6-T7)

Deterministic functions of `(task, candidate_set, ranked_output, ground_truth)`.
Implemented once, versioned, applied identically to every solver. Requires each
solver to emit a common record:

```
{task_id, test_index, candidates: [grid], scores: [float],
 aug_scores: [[float]], ranked: [grid], time_s, hit_limit: bool}
```

Solvers we do not control (published `.npz` predictions, e.g. CompressARC's)
supply only `ranked`, so only G1/G4 and the T-labels are computable for them.
That asymmetry is recorded per solver, never papered over.

### Human review (T5, T8, and adjudication)

- Two independent labellers, blind to which solver produced the failure.
- Report Cohen's kappa. Below 0.6, the category definition is the problem and
  gets rewritten, not the labels.
- Disagreements go to `UNCERTAIN`, which is a real value that appears in tables.
  A category whose `UNCERTAIN` rate exceeds 20% is not reported.
- Multi-label is allowed in branch T and forbidden in branches G and S, which
  are constructed to be exclusive.

### Versioning

The labelling code is pinned by commit SHA in every `RESULT.md`. If a category
definition changes, every affected table is regenerated or explicitly marked as
produced under the old definition. No silent relabelling.

## EXP002-C3: no taxonomy entries added

`experiments/EXP002C3/RESULTS.md` (the vCPU-aware CompressARC throughput
pilot) produced 0 OOMs, 0 archive corruption, and 0 hard failures across
all 10 task-processes it ran. It is an acquisition-orchestration
experiment, not a candidate-generation or selection result, so it has no
G-branch or S-branch failures to categorise — every task in every
configuration completed and produced a valid, non-empty candidate set
(none hit G5/G6 in this taxonomy's sense; the per-task 2400s budget was
reached, i.e. `timed_out: true`, in every run, which is the pre-existing,
expected CompressARC behaviour already noted elsewhere, not a new failure
mode). Recorded here, per this project's discipline of stating explicitly
when an experiment does not change a given document rather than leaving
the omission unexplained.

## Cross-solver comparability

The taxonomy's purpose is comparing *where* different solvers fail, which is the
evidence base for routing (C1) and verification (C3) claims. Two guards:

1. Categories are defined only over artifacts, never over architecture, so a
   diffusion solver and a program-synthesis solver get labelled by the same
   rules.
2. When a solver cannot supply the artifacts a category needs, that category is
   reported as `N/A` for that solver rather than imputed.
