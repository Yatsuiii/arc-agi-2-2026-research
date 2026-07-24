# RELATED_WORK

Citation-oriented. Organised by *idea*, not by paper, so that novelty claims can
be checked against the specific prior art for the specific component.

Every entry names a local evidence path. Numbers are quoted with the split and
snapshot they were measured on, because those differ across sources
(`docs/PROJECT_STATE.md` §5).

## Reference keys

| Key | Work | Local evidence |
| --- | --- | --- |
| NVARC25 | Sorokin & Puget, *NVARC solution to ARC-AGI-2 2025*, Nov 2025 | `references/score_winners/01_nvarc/nvarc_2025.pdf` |
| ARCH24 | Franzen, Disselhoff, Hartmann, *Product of Experts with LLMs* (ARC Prize 2024), arXiv:2505.07859 | cited by NVARC25 [4]; report at `references/score_winners/02_architects/` |
| ARCH25 | The ARChitects, *ARC Prize 2025 Solution Summary* | `references/score_winners/02_architects/page.md` |
| TRM | Jolicoeur-Martineau, *Less is More: Recursive Reasoning with Tiny Networks*, arXiv:2510.04871 | `papers/01_tiny_recursive_models.pdf` |
| HRM | Wang et al., *Hierarchical Reasoning Model*, 2025 | via TRM §2 |
| SOAR | Pourcel, Colas, Oudeyer, *Self-Improving Language Models for Evolutionary Program Synthesis*, ICML 2025, arXiv:2507.14172 | `papers/02_soar.pdf` |
| CMPRS | Liao & Gu, *ARC-AGI Without Pretraining*, arXiv:2512.06104 | `papers/03_compressarc.pdf` |
| BARB25 | Barbadillo, *Exploring the combination of search and learn for ARC25* | `references/score_winners/05_barbadillo/docs/05_Solution_Summary.md` |
| BARC | Li et al., *Combining Induction and Transduction for Abstract Reasoning*, 2024 | NVARC25 [9] |
| RE-ARC | Hodel, *Re-ARC*, 2024 | NVARC25 [5] |
| MINDSAI | Cole & Osman, *Dataset-induced meta-learning*, 2023 | NVARC25 [2]; **no code locally** |
| ARC2TR | ARC Prize Foundation, ARC-AGI-2 technical report | `papers/00_arc_agi_2_technical_report.pdf` |
| ARC25TR | ARC Prize Foundation, ARC Prize 2025 technical report | `papers/00_arc_prize_2025_technical_report.pdf` |

## Idea 1: Test-time training (TTT) on the demonstration pairs

Originates with MINDSAI in ARC Prize 2023 (NVARC25 cites it as [2], "TTFT was
used by the winners of a similar challenge run two years ago"). Universal among
2025 systems.

| Work | Granularity | Adapter | Steps / augmentations | Local evidence |
| --- | --- | --- | --- | --- |
| ARCH24 | multi-task (fine-tune on many tasks at once) | LoRA | — | ARCH25 §"Meanwhile, Back at ARC Prize 2025" states 2024 used multi-task |
| ARCH25 (AR branch) | **per task** | LoRA | 128 steps, one random augmentation per step, batch 1, rank 32 | `page.md` §Model & Training Process |
| NVARC25 (ARChitects branch) | per task | LoRA r=256, alpha=32 | bfloat16, no gradient checkpointing, no 4-bit | `nvarc_2025.pdf` §3.2 |
| NVARC25 (TRM branch) | per task | full weights, embeddings re-initialised to mean of pretrained | 2000 epochs, 200 warmup, ~2h on Kaggle | `nvarc_2025.pdf` §4.2 |
| 2026 T4x2 baseline | per task | LoRA r=256 on attention+MLP+`embed_tokens`+`lm_head`, rslora | 1 epoch over 16 augmentations, lr 5e-5, adamw_8bit | `docs/reference_exports/nvarc_t4x2_notebook.py:662-772` |
| CMPRS | per task, **and nothing else** | full 76K-param model trained from scratch | 1500-2000 steps, ~20 min on one RTX 4070 | `papers/03_compressarc.pdf` abstract |

The move from multi-task to per-task TTT between 2024 and 2025 is documented as
a deliberate improvement (ARCH25). CMPRS is the limit case: per-task training
*is* the entire method, with no pretraining at all.

## Idea 2: Augmentation as both training signal and inference-time ensemble

The D4 dihedral group (transpose + rot90) combined with colour permutation and
example reordering. Identical in kind across ARCH24, ARCH25, NVARC25 and TRM.

Two distinct uses, worth separating because our contribution may touch only one:

- **Training-time augmentation**: expands the ~4 demonstration pairs into
  hundreds of training examples. Used by every system above.
- **Inference-time augmentation as an ensemble over "views"**: solve or score
  the same task under k augmentations and aggregate. This is ARCH24's
  product-of-experts idea (`page.md` §Previously on ARC Prize 2024, point 3).

ARCH25 raised scoring augmentations from 8 to 32 after a 5.8x prefix-caching
speedup. NVARC25 §3.4 went the other way, to exactly 8, but made the
augmentation set **identical across candidates** so their scores are comparable
— a small change with a clear rationale, and the kind of detail a verification
contribution has to respect.

## Idea 3: Search over the decoder rather than sampling

ARCH24 introduced batched depth-first search over the token tree with a
probability cutoff, caching KV state so many candidates cost little more than
one. ARCH25 added speculative decoding (16-32 token guesses, 4.7x speedup),
which let them drop the DFS cutoff from 17% to 7% and thus produce many more
candidates.

NVARC25 §3.3 reimplemented DFS as a batched algorithm scaling "almost linearly
with batch size", and noted that batching makes inference **non-deterministic**
(citing Thinking Machines Lab on batch-invariant ops). They tested a
batch-invariant version, got better local precision, and dropped it because it
was 17% slower.

The 2026 T4x2 notebook's `turbo_dfs`
(`docs/reference_exports/nvarc_t4x2_notebook.py:516-583`) is this algorithm with
cutoff `max_score = -log(0.2)`, i.e. a 20% per-token probability floor — notably
*less* aggressive than ARCH25's 7%, presumably a T4 compute concession.

**Non-determinism is a documented, unresolved property of the strongest public
decoder.** Anything we build on top of candidate sets must either be robust to
it or measure it.

## Idea 4: Candidate selection / scoring

The component with the most divergence and the least ablation.

| Method | Formula | Source |
| --- | --- | --- |
| Product of Experts (ARCH24) | aggregate product of negative log-likelihoods of the candidate under k augmentations | ARCH25 §Previously, point 3 |
| `score_full_probmul_3` | `sum over generations (3 - beam_score) + mean over generations (sum over augs (3 - score_aug))` | `nvarc_t4x2_notebook.py:322-328` — this is ARCH24's scorer as implemented in the 2026 notebook |
| NVARC `score_agg` | `sum_{c in C_p} [c = s] + (1/m) sum_j log P̂_j(s)`, m = 8 | `nvarc_2025.pdf` §3.4 |
| `score_kgmon` | `len(guesses) - mean(mean(score_aug))` | `nvarc_t4x2_notebook.py:330-336` — the implementation of `score_agg`: vote count minus mean augmented NLL |
| CMPRS | rank by accumulated MDL/KL during the single training run | `papers/03_compressarc.pdf`; `solution_selection.py` |
| SOAR | execution-verified: a program either reproduces the demonstration outputs or it does not, then majority vote over surviving programs | `papers/02_soar.pdf` Fig. 1 |

NVARC25 says the switch to `score_agg` was found **after the competition
deadline** and calls it "the better method to select the right candidate", but
reports **no ablation isolating it**. The two scorers ship side by side in the
2026 notebook with a `benchmark_selection_algos` function that compares them —
an explicit invitation to measure the difference, which nobody has published.

SOAR's execution check is the only *verification* in the group: it can prove a
candidate consistent with the demonstrations. Every neural scorer above is a
*preference*, not a proof. That gap is the clearest opening in the literature.

## Idea 5: Synthetic data generation

The largest single reported score driver, and simultaneously the clearest
negative result.

- **NVARC25 (positive).** Four-stage LLM pipeline: collect descriptions from
  H-ARC (1700+ human solvers' natural-language descriptions) and BARC → generate
  puzzle summaries → INSTRUCT-SKILLMIX-style mixing of summary pairs into harder
  puzzles → generate input-grid Python programs (validated by generated unit
  tests) → generate output-grid programs (validated by consistency across 20
  samples). Yields 126,901 input programs, 103,253 puzzles, 3.2M augmented
  samples. Fig. 1: 12.92% (with BARC) → 27.64% (BARC removed, more NVARC data),
  **same architecture and same inference code**.
- **ARCH25 (negative).** Fine-tuned Qwen2.5-Coder-32B with GRPO to emit
  Atari-like game-screen generators, using a vision LLM as reward. "Only 1 in
  about 50 to 100 generations convinced us to be novel and interesting enough,"
  and a curated 150-task synthetic set "did not yield sufficient performance
  gains to justify pursuing this direction."
- **BARC (mixed).** NVARC25 §3.5: "in last year's competition, we found that
  BARC was not useful for the 2D transformer we developed". Removed from the
  final mix.

The difference between NVARC's success and ARCH25's failure is *validation*:
NVARC filtered programs by executable unit tests and by consistency across
repeated generations. ARCH25 filtered by aesthetic judgement. That is a
mechanism-level distinction worth citing precisely.

## Idea 6: Recursion and iterative refinement

Three independent lines converge here.

- **TRM**: a 7M-parameter, 2-layer network recursing on `(x, y, z)`; up to
  N_sup = 16 deep-supervision improvement steps, n latent updates per step.
  Reports 45% ARC-AGI-1 and 8% ARC-AGI-2. TRM §2.2 quotes an ARC Prize
  Foundation ablation of the predecessor HRM finding that **deep supervision, not
  hierarchical recursion, is the driver** (19%→39% from deep supervision;
  35.7%→39.0% from recursive hierarchy).
- **ARCH25 recursive masked diffusion**: LLaDA-8B-Base with 2D "Golden Gate"
  RoPE, LoRA r=512, trained to de-mask output grids; inference does 102
  recursive refinement steps as 2 rounds of 51 with a cold restart. Reports
  ~30.5% ± 1% on public eval **given the true output shape**, times ~85% ± 2%
  shape accuracy from a second model, ⇒ ~26% expected, 21.67% actual on the LB.
- **SOAR refinement**: LLM edits a failing program given execution feedback.

ARCH25 explicitly connects their recursion to TRM's: "both rely on recursion
between input and output, but the embedding design and task representations are
radically different, and that difference seems to matter a lot."

**A published, load-bearing weakness in ARCH25's recursion**: the model "never
learned to use its own logits" — recursive latent sampling was applied at
inference without a matching training objective. They name the fix (extra
recursive forward passes in the training loop) and did not have time to try it.

## Idea 7: Program synthesis vs transduction

- **SOAR**: LLM samples ~3k programs and refines ~6k per task, majority vote
  over executing programs; hindsight relabelling turns failed programs into
  correct programs for synthetic tasks, which then fine-tune the sampler and
  refiner. 52% on the ARC-AGI-1 public test set with open-weight LLMs.
  **ARC-AGI-1 only — no ARC-AGI-2 number is reported.**
- **BARB25**: pursued search-and-learn with hindsight relabelling for ARC-AGI-2
  all year. Abstract: "it does not yet solve any of the private test tasks from
  ARC-AGI-2." His leaderboard result came from "minor adaptations of last year's
  transduction with test-time training approach."

Taken together: **program synthesis that works on ARC-AGI-1 has not been shown
to transfer to ARC-AGI-2 by anyone in the local evidence.** That is a strong,
specific, citable gap, and it means "do SOAR on ARC-AGI-2" is a high-risk thesis
rather than an obvious one.

## Idea 8: Compression / MDL as the objective

CMPRS: 76K parameters, no pretraining, no training set. Minimises description
length of the target puzzle at inference. 20% of ARC-AGI-1 evaluation, 34.75% of
ARC-AGI-1 training. ~20 min per task on one RTX 4070.

Uniquely valuable properties for our purposes: zero contamination (the method
cannot have seen any eval task), full determinism of provenance, MIT licence,
and **recorded per-task predictions shipped in the repository**
(`results_for_the_blog_post/predictions_{training,evaluation}.npz`).

No ARC-AGI-2 number is reported.

## Search log

Record what was searched, when, and what was found. Novelty claims cite rows
here. Empty until a thesis is chosen, because searching before knowing the claim
produces a search that cannot fail.

| Date | Query / venue | Scope | Result |
| --- | --- | --- | --- |
| — | — | — | — |

## Closest-prior-work statement

To be written once a thesis is selected. Must name the single nearest published
method and state the delta in one sentence. Currently blocked on Phase 11 → 12.
