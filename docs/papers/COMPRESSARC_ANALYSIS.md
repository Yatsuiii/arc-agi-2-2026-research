# CompressARC — analysis

Paper: `papers/03_compressarc.pdf` — Liao & Gu, *ARC-AGI Without Pretraining*,
arXiv:2512.06104, Carnegie Mellon.
Code: `references/paper_winners/03_compressarc` @ `83a22218024d46273eb32b769a906340202ffb4d`, MIT.

Reported: **20% of ARC-AGI-1 evaluation, 34.75% of ARC-AGI-1 training**, with a
76K-parameter network, **no pretraining and no training set**.

## 1. Central theoretical claim

Minimum Description Length is sufficient to produce ARC-AGI capability. Framed
as code golf: find the shortest self-contained program that outputs the entire
puzzle, with unsolved cells filled arbitrarily. By Occam's razor the shortest
such program fills them correctly.

The engineering move that makes this tractable: rather than searching program
space combinatorially, **overfit a neural network to the puzzle and count the
bit-length of its weights**. The network's parameters are the compressed
program. This converts a combinatorial search into a differentiable
optimisation.

## 2. Architecture

`arc_compressor.py` + `multitensor_systems.py` + `layers.py`. The distinctive
piece is the multitensor system: the model maintains a family of tensors indexed
by which dimensions (examples, colours, x, y, direction) they range over, and
layers move information between members of the family. `initializers.py` handles
equivariance by weight tying, so symmetries are enforced structurally rather than
learned from augmentation.

76K parameters, initialised fresh for every puzzle.

## 3. Training regime

**There is none.** No pretraining, no training corpus, no checkpoint. For each
puzzle, a new model is initialised and trained for 1500-2000 steps by minimising
description length of that puzzle, with the test outputs held out.

This is the strongest data-efficiency claim in the literature: the model is
trained on exactly one puzzle, the one it is being asked to solve, with the
answer removed.

## 4. Inference regime

Training *is* inference. `solution_selection.py` logs candidate solutions
throughout the optimisation and ranks them by accumulated contribution to the
objective, with an EMA over logits. The final prediction is the two
highest-scoring distinct solutions.

## 5. Compute

~20 minutes per task on one RTX 4070. `parallel_train.py` schedules as many
puzzles concurrently as GPU memory allows. For 400 tasks that is roughly 130
GPU-hours on a consumer card — high per task, but on hardware anyone has, and
with no pretraining cost amortised anywhere.

## 6. Reported ARC-AGI-2 performance

**None.** ARC-AGI-1 only. `dataset/` vendors the ARC Prize 2024 competition files
(training = 400 tasks, evaluation = 400 tasks).

Given 20% on ARC-AGI-1 evaluation and the ~3.2x collapse the ARChitects measured
for the same method across benchmarks, a naive extrapolation lands near 6%. That
is a guess, not a result, and must be labelled as such anywhere it appears.

## 7. Universality claim

Unusual and strong in one specific direction: the method has **no priors from
pretraining at all**, so whatever it solves it solves from the puzzle itself.
The paper argues this suggests MDL as an alternative route to capability in
data-limited domains generally, naming drug discovery and protein design.

Weak in another direction: it is one benchmark, and the architecture bakes in
ARC-specific structure (grid dimensions, colour axis, equivariance groups).

## 8. Main novelty

Being the only deep-learning method for ARC-AGI where **all learning happens on
the single inference puzzle**, and getting a non-trivial score anyway. The paper
states it plainly: under these constraints "we do not ordinarily expect any
puzzles to be solvable at all."

## 9. Strongest supporting experiment

34.75% on ARC-AGI-1 training with zero training data. The absolute number is not
competitive; the conditions under which it is achieved are the result. There is
no contamination story available to explain it away, which is rare in this field.

## 10. Weakest unsupported assumption

**That the architecture is not itself the prior.** The equivariance weight-tying
in `initializers.py` and the multitensor decomposition encode substantial
knowledge about what ARC transformations look like: which symmetries matter,
which axes exist, how information should flow between them. That knowledge came
from the authors reading ARC.

So "no pretraining" is true and "no priors" is not. The priors moved from
weights into architecture, which is harder to measure and impossible to ablate
by removing a dataset. The paper does not quantify how much of the 20% the
architecture supplies.

Secondary: 20% on ARC-AGI-1 evaluation was already below the 2024
state-of-the-art by a factor of ~2.7, and ARC-AGI-2 is much harder.

## 11. Failure modes

- Per-task cost is fixed and high (~20 min) regardless of difficulty, with no
  mechanism to stop early or to spend more where it would help.
- No transfer whatsoever: solving 399 puzzles teaches nothing about the 400th.
- Architecture is bounded to fixed grid dimensions.
- Absolute accuracy is far below what a competition needs.

## 12. Reproducibility

**The best in the entire audit.** MIT licence, no external checkpoints, no
external datasets beyond the vendored ARC files, exact commands, a Kaggle
notebook template, and — critically — **the authors' own recorded per-task
results shipped in the repository**.

`results_for_the_blog_post/predictions_{training,evaluation}.npz` each contain:

- `solution_contribution_logs`, shape `(400, 2000, 2, 2)` — for each of 400
  tasks, at each of 2000 optimisation steps, the hash and score of the two
  candidate solutions logged at that step;
- `solution_picks_histories`.

`list_solved_puzzles.py` reconstructs from this, for any step budget, **which
tasks were solved and at what guess rank the true solution sat**.

That is a complete compute-versus-accuracy curve and a complete
selection-oracle trace, for a real solver, already computed, MIT-licensed,
readable on CPU in seconds. It is the only such artifact in the workspace and it
is why EXP001 can run without a GPU.

## 13. Relationship to the score-winning systems

None, structurally. No 2025 ARC-AGI-2 score winner uses compression, MDL, or
per-puzzle from-scratch training.

The one shared idea is *per-task adaptation*: CompressARC is the limit case of
test-time training, where the pretraining stage is deleted entirely. Placing it
on the same axis as NVARC and the ARChitects gives a spectrum:

| System | Pretraining | Per-task adaptation |
| --- | --- | --- |
| CompressARC | none | everything (76K params from scratch) |
| TRM | 7M net, 3 days on 4xH100 | full weights + new embedding table |
| NVARC | 4B, 27 h on 32xH100 | LoRA r=256 |
| ARChitects | 8B, 39 h on 8xH100 | LoRA r=32 |

Accuracy rises monotonically with pretraining scale, and the amount of per-task
adaptation falls. Nobody has measured the trade-off curve between those two axes
on ARC-AGI-2.

There is also a thematic link to the ARChitects' abandoned synthetic-data work:
they tried "measuring the compressibility (both using LLM or classic compression
algorithms) of the input to output mappings, since 'less' compressible games
contain more independent noise, thus cannot be inferred unambiguously"
(`page.md`). That is CompressARC's objective repurposed as a **task-difficulty
and ambiguity estimator**. They dropped the line for unrelated reasons and never
reported whether the compressibility signal worked.

## 14. Concepts that could support a new paper

1. **Description length as a task-level difficulty and ambiguity signal.** Two
   independent teams reached for it — CompressARC as an objective, the
   ARChitects as an ambiguity filter — and nobody has published whether a cheap
   compressibility estimate predicts solver success. A signal computable
   *before* running an expensive solver is exactly what compute-aware routing
   needs, and unlike a learned predictor it needs no training data and cannot
   leak.
2. **MDL as a verifier.** Every transduction system ranks candidates by the
   model's own likelihood, which is a preference. Description length of the
   `(demonstrations + candidate)` set is a different, model-independent quantity
   and could break ties the likelihood scorer gets wrong.
3. **The pretraining-versus-adaptation trade-off curve**, using the spectrum in
   §13 as the axis.

## 15. Ideas already absorbed elsewhere

- Per-task training → universal, via TTT, though nobody goes as far as deleting
  pretraining.
- Equivariance by weight tying → **not absorbed.** Every other system gets
  invariance by augmenting the data instead, which costs compute at both
  training and inference time. Structural equivariance is free at inference.
  Genuinely unexploited.
- MDL objective → not absorbed by anyone.
- Compressibility as an ambiguity signal → tried and unreported by the
  ARChitects. Open.
