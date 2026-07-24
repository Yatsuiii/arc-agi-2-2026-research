# Tiny Recursive Models — analysis

Paper: `papers/01_tiny_recursive_models.pdf` — Jolicoeur-Martineau, *Less is
More: Recursive Reasoning with Tiny Networks*, arXiv:2510.04871, Samsung SAIL
Montréal.
Code: `references/paper_winners/01_tiny_recursive_models` @ `c01103738605ba39d1430519b1ee0c62f4c707f8`, MIT.

Reported: **45% ARC-AGI-1, 8% ARC-AGI-2**, with a 7M-parameter network. Also
87% Sudoku-Extreme (from 55%) and 85% Maze-Hard (from 75%).

## 1. Central theoretical claim

Recursive reasoning with a single tiny network generalises better than either a
large autoregressive model or the two-network hierarchical scheme it replaces.
The scaling intuition of the field is inverted: parameter count is not the
binding constraint on this class of problem, and a small model recursing on its
own answer avoids the overfitting a large one incurs on ~1000 training examples.

The paper is explicitly a *simplification* argument. HRM justified two networks
recursing at different frequencies with biological analogy and a fixed-point
theorem; TRM removes the hierarchy, the biology and the theorem, uses one
2-layer network, and does better.

## 2. Architecture

State is a triple `(x, y, z)`: embedded question, current answer, latent
reasoning. One network with 2 layers, self-attention + MLP, RMSNorm, no bias,
rotary embeddings, SwiGLU.

Per improvement step:
1. update `z` n times given `(x, y, z)` — recursive reasoning;
2. update `y` once given `(y, z)` — answer improvement.

Up to `N_sup = 16` deep-supervision steps, each carrying `(y, z)` forward
detached so gradients do not propagate across steps. NVARC's configuration used
`L_layers=2, H_cycles=3, L_cycles=4` at training and `H_cycles=4,
halt_max_steps=10` at test time (`references/score_winners/01_nvarc/TRM/README.md`).

A learned halting head (`q_halt`) decides when to stop.

## 3. Training regime

Supervised, from scratch, on ~1000 examples per benchmark expanded by 1000
augmentations. For ARC: `dataset/build_arc_dataset.py --subsets training2
evaluation2 concept --test-set-name evaluation2` — dihedral transforms,
transpose, and colour permutations with **0 held fixed as black**. Original TRM
trains 100k epochs, 3 days on 4xH100.

The README carries a warning that matters for us: *"You cannot train on both
ARC-AGI-1 and ARC-AGI-2 and evaluate them both because ARC-AGI-2 training data
contains some ARC-AGI-1 eval data."* We confirmed the 2025 Kaggle bundle carried
nine ARC-AGI-1 tasks that the 2026 bundle dropped
(`docs/DATASET_AUDIT.md` §2).

## 4. Inference regime

Recursive refinement with learned halting. NVARC extended it to emit 10 attempts
per puzzle instead of 2 for ensembling (`nvarc_2025.pdf` §4.4).

## 5. Compute

| Stage | Hardware | Time |
| --- | --- | --- |
| Original ARC pretraining | 4xH100 | 3 days, 100k epochs |
| NVARC's retuned pretraining | 8xH100, batch 3072, lr 3e-4 | 24 h, 10k epochs |
| NVARC test-time fine-tuning | Kaggle 4xL4 | ~2 h for 240 tasks |
| Sudoku-Extreme (smallest experiment) | 1x L40S 48 GB | ~18 h |

## 6. Reported ARC-AGI-2 performance, and what it becomes in practice

| Setting | Score | Source |
| --- | --- | --- |
| Paper headline | 8% | `papers/01_tiny_recursive_models.pdf` abstract |
| ARC Prize Foundation, 4 nodes x 8 H100 | 6.9% | `nvarc_2025.pdf` §4 |
| NVARC, retuned pretraining, no TTT tuning | 2.08% | §4.1 |
| NVARC, + test-time fine-tuning, 2k epochs | 7.5% | §4.3 |
| NVARC, 4k epochs, <4 h on Kaggle | **10.0%** | §4.3 |
| NVARC local pass@2 on 120 eval, model not trained on eval | 9.44% | §4.3 |
| NVARC local eval statistics dump | pass@2 = 10.14%, pass@1 = 7.64% | `TRM/README.md` |

So the honest range on ARC-AGI-2 is **7-10%**, and reaching it inside Kaggle
took a retuned pretraining recipe plus per-task fine-tuning that the original
paper does not describe.

## 7. Universality claim

Strong on its face: one architecture, four benchmarks (Sudoku-Extreme,
Maze-Hard, ARC-AGI-1, ARC-AGI-2), improving all four. This is the best
universality story of the three paper-track systems.

The caveat is that all four are fixed-canvas grid puzzles with a supervised
train/test split of the same task distribution. That is narrower than the
universality rubric wants.

## 8. Main novelty

Removing structure and getting a better result: one network instead of two, no
hierarchy, no fixed-point theorem, 2 layers instead of 4, 7M parameters instead
of 27M.

## 9. Strongest supporting experiment

The paper cites an independent ARC Prize Foundation ablation of HRM (TRM §2):
deep supervision alone takes accuracy 19% → 39%, while the hierarchical recursion
adds only 35.7% → 39.0%. That is third-party evidence that the component TRM
keeps is the one that mattered and the component it deletes is the one that did
not. Using someone else's ablation to justify your simplification is unusually
disciplined.

## 10. Weakest unsupported assumption

**The 7M parameter count.** NVARC §4.1 states it plainly:

> "TRM is claimed to be tiny because it contains 7M parameters. This is
> misleading because the model contains an additional puzzle embedding table,
> with 512 parameters per puzzle. When using 100k puzzles with 1000
> augmentations we get an additional 51B parameters, which is way too large for
> a Kaggle submission."

The per-puzzle embedding is a learned memory whose size scales with the dataset,
and it is excluded from the headline. It also does not transfer: at test time
the table must be resized and re-initialised (§4.2), so the "tiny model" arrives
at each new puzzle with no memory of anything.

Under a fair accounting, TRM is a tiny *recursive core* attached to a very large
per-puzzle lookup table. The paper's framing — "less is more", "you don't need
massive foundational models" — rests on the number that omits the table.

## 11. Failure modes

- Scales badly with data because of the embedding table, which is precisely
  backwards from what a general method should do. NVARC tried to feed it all
  their synthetic data and reports "That did not work at all."
- The 8% ARC-AGI-2 result is 3.4x lower than the 2025 winning system, on a
  benchmark where every point is hard-won.
- Fixed canvas: the whole design assumes a bounded grid.

## 12. Reproducibility

**Best of the three paper systems.** MIT licence, complete dataset builders,
complete training code, exact commands in the README, a `kaggle/` directory, and
an exact-version requirements file. NVARC reproduced and extended it, which is
itself the strongest possible reproducibility evidence.

Caveats: the repository is archived (read-only) upstream; NVARC pinned a
different revision (`e7b6871`) than the one we hold (`c011037`); and 3 days on
4xH100 is out of our reach, so we would depend on published checkpoints.

## 13. Relationship to the score-winning systems

Direct and documented. NVARC built one of its two branches on TRM, retuned it to
fit Kaggle, and reports every step. The ARChitects looked at TRM, credited it
with validating small models on ARC, and noted the convergence:

> "both rely on recursion between input and output, but the embedding design and
> task representations are radically different, and that difference seems to
> matter a lot."

That sentence is the crux. Two independent teams arrived at recursive refinement
from opposite directions — one from tiny supervised networks, one from 8B masked
diffusion — and both attribute the remaining gap to representation.

## 14. Concepts that could support a new paper

1. **Deep supervision as the load-bearing mechanism.** Third-party-validated,
   and it is a *training-objective* idea, not an architecture idea, so it
   transfers. The ARChitects' unattempted fix — putting recursive forward passes
   inside the training loop — is the same idea applied to their model.
2. **Learned halting as a compute-allocation signal.** TRM already has a
   `q_halt` head that decides when a task is done. Nobody has asked whether that
   signal predicts *correctness*, or whether it could allocate budget across
   tasks. It is the only per-task confidence signal that exists natively in any
   reference system.
3. **The embedding-table critique as a positive research question.** If the
   per-puzzle memory is what makes TRM work and also what stops it scaling, a
   method that gets the benefit without the table is a real contribution.

## 15. Ideas already absorbed elsewhere

- Recursive refinement → NVARC's TRM branch, ARChitects' recursive latent
  sampling.
- Deep supervision → not absorbed by anyone. Still open.
- Dihedral + colour-permutation augmentation → universal, predates TRM.
- Halting head → **not used by anyone for anything but stopping.** Open.
