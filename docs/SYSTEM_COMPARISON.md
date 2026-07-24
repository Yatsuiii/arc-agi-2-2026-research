# SYSTEM_COMPARISON

All six systems for which local evidence exists. MindsAI appears with `UNKNOWN`
throughout because only its idea is attributable; Lonnie is excluded entirely
(`docs/systems/LONNIE.md`).

**Read every score with its benchmark.** ARC-AGI-1 and ARC-AGI-2 numbers are not
comparable — the ARChitects' own lineage went 53.5% → 16.94% across the two.

## Matrix

| Dimension | NVARC | ARChitects A | ARChitects B | TRM | SOAR | CompressARC | Barbadillo | MindsAI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Paradigm** | AR transduction | AR transduction | masked diffusion | recursive supervised | LLM program synthesis | MDL compression | program synthesis (shipped: AR transduction) | UNKNOWN |
| **Architecture** | Qwen3-4B, 16-tok vocab | Mistral-NeMo-Minitron-8B | LLaDA-8B, 2D GG-RoPE | 2-layer recursive net | Qwen 7-72B, Mistral-123B | multitensor, tied-weight equivariant | BARC induction models | UNKNOWN |
| **Params** | **3.63B** (measured) | 8B | 8B x2 (content + shape) | 7M + puzzle table | 7B-123B | **76K** | ~7B | UNKNOWN |
| **Training data** | 3.2M augmented from 104,539 puzzles | ARC1+2, ARC-Heavy, RE-ARC, ConceptARC | same | ~1000 puzzles x 1000 aug | 5M self-generated solutions | **none** | BARC + hindsight | UNKNOWN |
| **Synthetic data** | **yes, decisive** | tried, abandoned | tried, abandoned | no | yes, hindsight relabelling | no | yes, hindsight relabelling | UNKNOWN |
| **Test-time training** | yes, LoRA r=256 | yes, per task | yes, 128 steps, LoRA r=32 | yes, full weights | optional, +3-5% | **the entire method** | yes | **yes (originated it)** |
| **Search** | batched DFS, cutoff 0.20 | DFS + speculative, cutoff 0.07 | replaced by recursion | no | 3k samples + 6k refinements | no | independent samples | UNKNOWN |
| **Recursion** | via TRM branch | no | **102 refinement steps** | **core mechanism** | refinement loop | 1500-2000 opt. steps | attempted | UNKNOWN |
| **Symbolic reasoning** | no | no | no | no | via Python | no | via Python/DSL | UNKNOWN |
| **Program synthesis** | offline only (data) | no | no | no | **yes, at solve time** | no | yes, at solve time | UNKNOWN |
| **Augmentation** | D4 x colour x order | same | same + 32x32 canvas | D4 x colour (0 fixed) | no | **structural equivariance instead** | yes | UNKNOWN |
| **Ensembling** | tried, **zero gain at 4B** | no | no | no | majority vote over programs | 2 top-scoring | no | UNKNOWN |
| **Candidate ranking** | votes + mean aug NLL | product of experts over 32 augs | not documented | halting head | execution filter + majority vote | accumulated MDL | execution filter | UNKNOWN |
| **Verification** | **none** | **none** | **none** | **none** | **execution proof** | **none** | **execution proof** | UNKNOWN |
| **Confidence calibration** | none | none | none | `q_halt` head, used only to stop | vote count | MDL score | none | UNKNOWN |
| **Compute per task** | uniform, capped 1200 s | uniform | uniform | uniform | ~9k LLM generations | ~20 min fixed | uniform | UNKNOWN |
| **GPU requirement** | 4xL4 12 h (2xT4 port) | Kaggle L4 | Kaggle L4 | Kaggle 4xL4 ~2 h | far beyond Kaggle | 1x RTX 4070 | Kaggle | UNKNOWN |
| **Offline training** | 32xH100 x 27 h | not stated | 8xH100 x 39 h | 4xH100 x 3 days | very large | **none** | moderate | UNKNOWN |
| **Reproducible from repo** | no | partial (code, no weights) | partial | **yes** | yes | **yes, fully** | yes (but unlicensed) | no |
| **Licence** | **none** | Apache-2.0 | Apache-2.0 | MIT | MIT | MIT | **all rights reserved** | n/a |
| **Reported score** | **27.64% ARC-AGI-2** (29.72 post-deadline) | 16.94% ARC-AGI-2 | 21.67% ARC-AGI-2 | 8% ARC-AGI-2 / 45% ARC-AGI-1 | **52% ARC-AGI-1**, no ARC-AGI-2 | 20% ARC-AGI-1 eval, no ARC-AGI-2 | ~top-20, and **0 private ARC-AGI-2 tasks** for the research line | UNKNOWN |
| **Hidden-set score** | public LB = half of hidden 240 | same | same | 6.9-10% via NVARC | n/a | n/a | n/a | UNKNOWN |
| **Uniquely solved** | ~2-3/240 unique to TRM vs Qwen3 (§4.4) — the only published measurement | unmeasured | tasks needing global structure change | unmeasured | unmeasured | unmeasured | unmeasured | UNKNOWN |
| **Major weakness** | eval contamination; no verification; uniform compute | too weak on ARC-AGI-2 | shape model costs ~4.5pp multiplicatively | embedding table blows up with data | ARC-AGI-1 only; cost per task | 20% ceiling on the easier benchmark | did not transfer to ARC-AGI-2 | unavailable |
| **Room for improvement** | selection, routing, verification | superseded | recursion never trained for | scaling without the table | transfer to ARC-AGI-2 | MDL as a signal, not a solver | stronger induction model | — |

## 1. Components used by nearly every strong system

| Component | Systems |
| --- | --- |
| Per-task test-time adaptation | **all seven**. The only universal. |
| D4 + colour-permutation augmentation | NVARC, both ARChitects branches, TRM, Barbadillo. Only CompressARC (structural equivariance) and SOAR (programs) abstain. |
| Multiple candidates + a selection step | all except CompressARC, which produces them incidentally |
| Pretraining on augmented ARC-like corpora | all except CompressARC |
| Flat token-per-cell grid encoding | NVARC, ARChitects A, TRM |

## 2. Components unique to one system

| Component | System | Notes |
| --- | --- | --- |
| LLM-generated, execution-validated synthetic puzzles at scale | NVARC | the only decisively ablated score driver in the field |
| 16-token cut vocabulary | NVARC | undocumented in the paper; removes 0.39B of 4.02B params and enables 4B TTT on small GPUs |
| Masked diffusion + recursive latent sampling | ARChitects B | |
| 2D Golden Gate RoPE + padded-then-stripped 32x32 canvas | ARChitects B | |
| Deep supervision over refinement steps | TRM | third-party-validated as HRM's real driver |
| Learned halting head | TRM | **exists, used only to stop, never as a confidence signal** |
| Hindsight relabelling at scale | SOAR (and Barbadillo) | |
| MDL objective, zero pretraining | CompressARC | |
| Equivariance by weight tying | CompressARC | **free invariance at inference; nobody else has it** |

## 3. Components with strong evidence of contribution

Only three claims in the entire field are backed by a real ablation:

1. **Synthetic data quality and quantity.** NVARC Fig. 1: 12.92% → 27.64%,
   architecture and inference held fixed. The strongest result anywhere here.
2. **Deep supervision over recursive hierarchy.** ARC Prize Foundation's HRM
   ablation, 19% → 39% from deep supervision versus 35.7% → 39.0% from hierarchy.
   Third-party, which makes it credible.
3. **Model scale within the same recipe.** NVARC Table 2: 2B → 4B gives
   22.22% → 29.72%.

Everything else is asserted.

## 4. Components with weak or missing ablations

| Component | Status |
| --- | --- |
| `score_agg` vs product-of-experts | called "better", **no number**, both implementations ship side by side |
| Number of scoring augmentations | 8 (NVARC) vs 32 (ARChitects), no curve from either |
| DFS cutoff | 0.17 → 0.07 → 0.20 across three systems, never swept |
| TTT rank and step count | r=256/128 steps vs r=32/128 steps, never compared |
| 2D positional encoding | ARChitects B's central architectural claim, asserted not measured |
| Recursion depth | 102 steps, unjustified |
| TTT on vs off at fixed data | **never reported by anyone** |
| Per-task solve sets across solvers | one sentence, 2-3 tasks, no list |

## 5. Repeated failure modes across systems

1. **Output-size prediction.** ARChitects B needed a whole second model and got
   ~85%, costing ~4.5pp multiplicatively. Our dataset audit finds 6.7% of
   evaluation tasks have an output-size rule that is inconsistent across
   demonstrations, versus 1.1% in training.
2. **Selection loses correct candidates.** NVARC §4.4 states TRM's unique solves
   "were not always picked by Qwen3 scoring". Every neural ranker in the table
   is a likelihood preference with no consistency check.
3. **Evaluation-set overfitting.** ARChitects expected 26%, scored 21.67%, and
   diagnosed it themselves. Both they and NVARC had the eval set in their
   pretraining mix.
4. **Global structural transformations.** ARChitects: "tasks like this one
   (which we haven't seen being solved at all, yet) [...] where the model must
   understand and alter the global structure of the solution." Their entire
   diffusion pivot was a response to this.
5. **Uniform compute.** Every system spends the same budget on a task solved in
   the first beam and on one that needs exhaustive search.
6. **Synthetic data is easy to generate and hard to validate.** ARChitects
   failed on validation, not generation. NVARC succeeded by making validation
   machine-checkable.

## 6. Complementary solver behaviours

Weakly evidenced, and the honest summary is that **nobody has measured this
properly**.

- NVARC measured TRM vs Qwen3-4B: 2-3 unique tasks out of 240, ensembling gain
  exactly zero at 4B. That is a *negative* result about complementarity between
  those two solvers.
- The ARChitects moved from AR to diffusion specifically because AR could not
  handle global-structure tasks, implying the two paradigms have different
  competence sets — but they never ran both and compared.
- CompressARC solves puzzles with no priors at all, so its solve set has no
  reason to correlate with a pretrained model's. Untested, and on a different
  benchmark.

## 7. Opportunities for conditional routing

The prerequisite is a task-level difficulty or success signal computable
cheaply. What exists:

- TRM's `q_halt` head — a trained halting probability, currently discarded.
- DFS candidate-set size and score spread — available mid-run, before the
  expensive rescoring stage.
- Deterministic task statistics (`artifacts/data_audit/task_statistics.csv`) —
  grid area, object count, demonstration count, size-relation consistency. Free,
  leak-proof, computed before anything runs.
- Compressibility of the demonstration set — the ARChitects' abandoned
  ambiguity signal, and CompressARC's objective.

What is missing: **any published evidence that any of these predicts solver
success.** That is a gap, and also a warning that the routing thesis could fail
at its first step.

## 8. Opportunities for better verification

The sharpest structural gap in the field.

Every transduction system ranks candidates by *the model's own likelihood under
augmentations*. That is a preference. SOAR and Barbadillo have real verification
— a program either reproduces the demonstrations or it does not — but neither
scored on ARC-AGI-2.

Nobody has asked: given a candidate output grid produced by a transduction
model, can we check it against the demonstration pairs by any means independent
of that model? Candidate checks include cheap invariants (does the candidate
respect the size relation the demonstrations establish? the colour-mapping
pattern? the symmetry the demonstrations exhibit?), consistency of an
inverse-direction prediction, or description length of
`demonstrations + candidate`.

None of these needs a program synthesiser. All are model-independent. This is
the least-explored high-value direction in the audit.

## 9. Opportunities for compute-aware allocation

Structurally easy in the NVARC pipeline and completely untouched:

- Per-task time is already tracked and capped.
- Cost is driven by output area and candidate breadth, both partly observable
  before the expensive stage.
- The T4x2 port has ~1/4 the per-task compute of the original, so allocation
  matters *more* for us than it did for NVARC.
- The 12-hour cap means compute spent on an already-solved task is compute
  denied to an unsolved one.

The honest counter-argument: if the marginal task is simply unsolvable at any
budget, reallocation buys nothing. That is what an oracle analysis must
establish before the thesis is worth pursuing.

## 10. Opportunities that are scientifically novel rather than ensembling

Ranked by (evidence that the gap is real) x (testability on our compute):

1. **Verification independent of the generating model.** Gap is structural and
   universal; every system lacks it. Testable on stored candidate sets, CPU
   only. Prior art: SOAR and Barbadillo, both on the program side, neither on
   ARC-AGI-2.
2. **Training the refinement operator on its own recursive passes.** Explicitly
   named as unattempted by the ARChitects, and the same idea as TRM's
   deep supervision applied to a different model class. Highest theory score,
   highest compute cost.
3. **Compressibility / description length as a pre-solve difficulty and
   ambiguity signal.** Two independent teams reached for it, neither reported
   whether it works. Cheap, model-free, no leakage surface.
4. **The pretraining-versus-adaptation trade-off curve** (CompressARC → TRM →
   NVARC → ARChitects). A measurement paper, weak on accuracy, strong on
   universality and progress.
5. **Structural equivariance instead of augmentation.** CompressARC gets for
   free what everyone else buys with 8-32x the inference compute. Nobody has
   tried it in a pretrained transduction model.

Explicitly **not** on this list: combining NVARC with TRM, or any other
"ensemble the winners" plan. NVARC ran that experiment and got zero
(`docs/NVARC_LINEAGE.md`), and `paper/CLAIM_LEDGER.md` A3 forbids it.
