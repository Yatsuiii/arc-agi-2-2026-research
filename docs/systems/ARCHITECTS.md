# The ARChitects — architectural teardown

Sources:
- `references/score_winners/02_architects` @ `efcadc66a0fcc1ea7eca2c90eac066c54f8fc543`
- Report: `page.md` (CC BY-SA 4.0), code: `pretraining_code/*.py` (Apache-2.0,
  Franzen / Disselhoff / Hartmann)
- 2024 paper: arXiv:2505.07859

Licence: **REUSABLE WITH ATTRIBUTION** — the only score-winning source we may
build on (`docs/REFERENCE_LICENSE_AUDIT.md` §2).

Results: **16.94%** public LB on 2025-08-11 with the autoregressive branch;
**21.67%** with the final masked-diffusion submission. 2024: won ARC Prize with
53.5%, plus an uncounted late submission at 56.5%.

## 1. Core solver paradigm — two, sequentially

The team ran an explicit exploration/exploitation split and shipped the newer,
riskier branch.

**Branch A (exploitation, first half of 2025).** Autoregressive transduction:
Mistral-NeMo-Minitron-8B-Base, per-task LoRA TTT, depth-first search sampling,
product-of-experts selection. This is the 2024 winner, improved.

**Branch B (exploration, final submission).** Recursive masked diffusion:
LLaDA-8B-Base with 2D positional encoding, fine-tuned to de-mask output grids,
plus a second model that predicts output shape, plus recursive latent sampling
at inference.

## 2. Techniques

| Technique | Branch A | Branch B |
| --- | --- | --- |
| Test-time training | yes, per task | yes, 128 steps, LoRA r=32, batch 1 |
| Supervised fine-tuning | yes | yes, 175k steps / 39 h on 8xH100, LoRA r=512 |
| Synthetic data | tried, **abandoned** | tried, **abandoned** |
| Recursive refinement | no | **yes, 102 inference steps** |
| Diffusion | no | **yes, masked discrete diffusion** |
| Program synthesis | no | no |
| Search | yes, DFS + speculative decoding | replaced by recursive sampling |
| Ensembling | no | no (two models, but sequential not ensembled) |
| Verifier | no | no |
| Augmentation | yes, D4 + colour + example order | same pipeline |

## 3-4. Models

| Branch | Model | Params |
| --- | --- | --- |
| A | `nvidia/Mistral-NeMo-Minitron-8B-Base` | 8B |
| B (demasking) | `GSAI-ML/LLaDA-8B-Base`, 2D RoPE, LoRA r=512 | 8B |
| B (shape) | same, further fine-tuned from the demasking model | 8B |

## 5-7. Representation and 2D structure — the substantive contribution

Branch A uses the same flat token-per-cell scheme NVARC inherited.

Branch B changes it materially:

- **Golden Gate RoPE.** Standard 1D RoPE is replaced by an N-dimensional variant
  that encodes many directions rather than only horizontal and vertical. The
  stated rationale: ARC tasks require "looking" across the grid from multiple
  angles.
- **Fixed 32x32 canvas.** Every grid gets a row and column of delimiter symbols
  on its right and bottom edges, then is padded to 32x32 so position ids align
  across grids. **The padding tokens are then deleted after position ids are
  assigned**, preserving the 2D coordinates while paying only for real cells.
  This is the elegant part.
- Delimiter tokens do double duty: in the shape model they are the *only*
  thing predicted, so shape prediction reduces to placing two boundary lines.

Implementation is in `pretraining_code/modeling_llada_gg2m_fast.py` and
`arc_loader.py` (Apache-2.0, readable, usable by us).

## 8. Augmentations

`pretraining_code/arc_loader.py` is the canonical implementation and the direct
ancestor of NVARC's and of the 2026 notebook's loader:
`permute_array` (371), `transform_array` (383), `augment_keys` (532),
`augment` (552), `permute_ex` (519). Augmentation identity is carried in the
task key as a dotted string (`.rot90.transpose.permute0123456789.ex012`), so any
prediction can be inverted back to the original frame.

## 9. Synthetic data — the field's clearest negative result

Fine-tuned Qwen2.5-Coder-32B with GRPO to write generators of Atari-like game
screens, using a vision LLM as reward for "does this look like a game screen".
Generators worked and were steerable.

The failure was not generation but **task definition**: turning a generator into
a *meaningful puzzle* with an inferable rule. Tried using their own predictive
model to reject too-easy and too-hard tasks, and compressibility (LLM-based and
classical) as an ambiguity proxy. Result: "only 1 in about 50 to 100 generations
convinced us to be novel and interesting enough", and a curated 150-task set
"did not yield sufficient performance gains to justify pursuing this direction".

They had ~3 weeks of 8xA100 on this and dropped it.

Read against NVARC's success (`docs/systems/NVARC.md` §9), the distinguishing
variable is **validation method**: NVARC validated by program execution and by
agreement across independently sampled output programs, both machine-checkable.
The ARChitects validated by human and VLM judgement, which does not scale.

## 10. Test-time training

Branch B: per task, 128 training steps, one distinct random augmentation per
step, batch size 1, LoRA rank 32. Initialised from the globally fine-tuned
demasking model. Runs on Kaggle L4s.

Note the asymmetry with NVARC: rank 32 and 128 steps versus rank 256 and one
epoch over 16 augmentations. Nobody has published a comparison.

## 11-13. Candidates, ranking, verification

**Branch A generation.** DFS over the token tree with a probability cutoff,
plus two speedups that are the actual 2025 contribution:
- *Speculative decoding inside DFS*: guess 16-32 tokens ahead with a simple
  heuristic instead of one token per step. **4.7x faster**, which let them drop
  the cutoff from 17% (2024) to **7%**, producing far more candidates.
- *Prefix caching for scoring*: reuse the KV cache of the examples and challenge
  input across augmentations. **5.8x faster**, which let them raise scoring
  augmentations from 8 to **32**.

**Branch A ranking.** Product of Experts: re-apply the augmentations to each
candidate and aggregate the product of negative log-likelihoods across views.
The stated intuition is that the model already estimates candidate correctness;
aggregating over views stabilises it.

**Branch B generation.** Recursive latent sampling. Rather than sampling hard
tokens, mix *soft combinations of token embeddings* and feed the model its own
logits, iterating. 102 inference steps, structured as 2 rounds of 51 with a cold
restart between them.

**Verification: none in either branch.**

### The load-bearing admission

> "the recursive sampling method that we found in the final 5 days of the
> competition was not reinforced in a proper training objective; the model never
> learned to use its own logits, yet we used it in that way anyways."

They name the fix — one or more extra recursive forward passes inside the
training loop — and state they had no time. **This is an explicitly published,
explicitly unattempted improvement to the strongest architectural idea in the
2025 field.** It is the highest-value item in the entire audit for anyone looking
for a defensible research direction.

## 14. Compute allocation

Uniform per task, as with NVARC. No difficulty estimation, no routing.

## 15-19. Requirements

- Pretraining: 175,000 steps, effective batch 8, **39 h on 8xH100**.
- Data: RE-ARC, ARC-GEN-100K, ARC1 + ARC2 training **and evaluation** sets,
  ARC-Heavy, ConceptARC. Note the evaluation sets are in the pretraining mix
  here too — the same contamination position as NVARC.
- Development budget: 1-3 GH200 machines for the season, 2 weeks of 16xH100 at
  the end, ~3 weeks of 8xA100 on the abandoned synthetic-data line.
- Inference: Kaggle L4s within the 12 h cap.

## 20. Kaggle-offline deployment

Not documented in this repository; the submission notebooks are not published
here. Only `pretraining_code/` is released.

## 21. What generates the score

Branch B decomposes multiplicatively and they say so:

| Component | Measured |
| --- | --- |
| Demasking model, **true output shape given** | ~30.5% ± 1% on public eval |
| Shape model accuracy | ~85% ± 2% |
| Expected combined | ~26% |
| **Actual public LB** | **21.67%** |

Two readable facts. First, **shape prediction alone costs ~4.5 points**, which
is why output-size failure is category G1 in `paper/FAILURE_TAXONOMY.md`.
Second, the 26% → 21.67% shortfall is attributed by the authors to "some
overfitting towards the evaluation set" — and per `docs/DATASET_AUDIT.md` §2
that evaluation set was in their pretraining mix, so the diagnosis is almost
certainly right.

Branch A's history gives a clean progression: 2024 winner at 53.5% on ARC-AGI-1,
the same lineage at **16.94%** on ARC-AGI-2. The benchmark change, not the
method, accounts for the collapse.

## 22-23. Inheritance and redundancy

Branch A inherits from their own 2024 system, which in turn took per-task TTT
from MindsAI's 2023 approach. Branch B shares only the data pipeline and
augmentation code with Branch A; the model, objective, sampler and selection are
new.

**Redundant**: the separate shape model. They say so — "a combined model would
most likely have helped to improve the score further" — and explain it existed
only because of Kaggle memory and speed limits.

## 24. Public-set patches

None found. The team explicitly guarded against leaderboard overfitting: 60
submissions total across the season, only 17 using the diffusion approach, and a
stated bias "towards more parameter free methods".

## 25. Hidden-set failure modes

1. Multiplicative shape-model error, ~15% of tasks lost before content is
   considered.
2. Eval-set overfitting, self-diagnosed, ~4.3 points.
3. Recursive sampling used out of distribution with respect to its training
   objective; they report instability for longer recursions and difficulty
   normalising logits.
4. Higher variance than Branch A because two models compose.

## 26-27. Ablations

**Reported:** speculative decoding speedup (4.7x) and its effect on the feasible
DFS cutoff (17% → 7%); prefix caching speedup (5.8x) and its effect on scoring
augmentations (8 → 32); masking one output grid versus several; known-shape
accuracy versus end-to-end accuracy.

**Missing:** the 2D Golden Gate RoPE versus 1D RoPE, which is their central
architectural claim and is asserted rather than measured; LoRA rank; TTT step
count; recursion depth (102 steps is stated, not justified); diffusion versus
autoregressive at matched compute.

## 28-30. Reproducibility

**Partially reproducible.** `pretraining_code/` contains a real, readable,
Apache-2.0 training pipeline: `arc_loader.py` (607 lines), `model_tools.py`
(330), `modeling_llada_gg2m_fast.py` (the 2D-RoPE LLaDA), and two finetune
scripts differing in scale.

Available: the model architecture, the data loading and augmentation, the
training loop, the hyperparameters in the filenames
(`lr45-mt20-keep1-gg2m-cyc85-r512`).

**Unavailable**: the fine-tuned checkpoints, the inference and sampling code
(the recursive latent sampler is described in prose only), the shape model, the
submission notebook, and 39 h of 8xH100.

**We could plausibly reimplement Branch B's training** from what is here. We
could not reimplement its sampler without inventing the details.
