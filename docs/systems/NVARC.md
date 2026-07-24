# NVARC — architectural teardown

Source: `references/score_winners/01_nvarc` @ `846d0198efa752534594e321fc3289fc0a06c657`
Paper: `references/score_winners/01_nvarc/nvarc_2025.pdf` (Sorokin & Puget, NVIDIA, Nov 2025)
Licence: **none** — RESEARCH REFERENCE ONLY (`docs/REFERENCE_LICENSE_AUDIT.md` §1)

Result: **27.64%** public LB during ARC Prize 2025 (1st place); **29.72%**
post-deadline. Both on 240 hidden tasks, 12 h, 4x L4.

## 1. Core solver paradigm

Autoregressive transduction with per-task test-time fine-tuning, tree search
over the decoder, and augmentation-consistency rescoring of candidates. Two
independent branches were built; the winning submission used only one.

## 2. Techniques used

| Technique | Present | Evidence |
| --- | --- | --- |
| Test-time training | **yes**, per task, both branches | §3.2, §4.2 |
| Supervised fine-tuning | yes, 4-node 8xH100 x 27 h | §3.1, `ARChitects/run_sft_4b.sh` |
| Synthetic data | **yes, the dominant component** | §2, Fig. 1 |
| Recursive refinement | only in the TRM branch | §4 |
| Diffusion | no | — |
| Program synthesis | only inside the data pipeline, never at solve time | §2.3-2.4 |
| Search | yes, batched DFS over the token tree | §3.3 |
| Ensembling | attempted, **abandoned** | §4.4 |
| Verifier / critic | no. Scoring is the model's own likelihood. | §3.4 |
| Augmentation | yes, D4 x colour permutation x example shuffle | `SDG/scripts/build_datasets.py:12-70` |
| Task-specific adaptation | yes — TTT is the whole adaptation mechanism | §3.2 |

## 3-4. Models and parameter counts

| Branch | Model | Params | Note |
| --- | --- | --- | --- |
| ARChitects branch (winning) | Qwen3-4B-Thinking-2507 | ~4B, **minus ~0.78B of embeddings** | see §5 |
| ARChitects branch (2B variant) | Qwen3-VL-2B-Instruct, LLM part only | ~2B | Table 2: 22.22% LB |
| TRM branch | Tiny Recursive Model | 7M network + a per-puzzle embedding table | §4.1 |

The TRM parameter count is not 7M in practice. NVARC §4.1: "the model contains an
additional puzzle embedding table, with 512 parameters per puzzle. When using
100k puzzles with 1000 augmentations we get an additional 51B parameters."
That is a load-bearing correction to TRM's headline claim and forced NVARC to
shrink both the puzzle count and the augmentation count to fit Kaggle memory.

## 5. Representation and tokenisation — the under-discussed component

Grids are rendered as raw digit strings, one row per line, in a Qwen chat
template:

```
<|im_start|>user\n123\n456<|im_end|><|im_start|>assistant\n78\n90<|im_end|>
```

`nvarc_2025.pdf` §3.1; implemented at `SDG/scripts/build_datasets.py:122-142`
and `docs/reference_exports/nvarc_t4x2_notebook.py:8-16`.

**The tokenizer is cut to 16 tokens.** `ARChitects/qwen3_configs/vocab.json` has
exactly 13 entries — the ten digits, `Ċ` (newline), `user`, `assistant` — plus
`added_tokens.json` giving `<|endoftext|>`=13, `<|im_start|>`=14,
`<|im_end|>`=15. The base model path is `/models/Qwen3-4B-Thinking-2507-16t`.

Consequences, none of which the paper spells out:

- Qwen3's 151,936-entry embedding matrix and lm_head collapse to 16 entries.
  At hidden size 2560 that is roughly **0.78B parameters removed** from a 4B
  model. This is why a "4B" model runs test-time LoRA on a 16 GB T4.
- LoRA can target `embed_tokens` and `lm_head` at r=256 for almost nothing,
  which the 2026 notebook does (`nvarc_t4x2_notebook.py:664`). On a full-vocab
  model that would be prohibitive.
- Exactly one token per cell means grid geometry maps to token positions
  predictably, and `max_new_tokens` is computable in closed form
  (`nvarc_t4x2_notebook.py:82-85`).

## 6-7. How 2D structure is preserved

**It is not, explicitly.** There is no 2D positional encoding, no row/column
embedding, no 2D attention bias. Structure is conveyed only by (a) one token per
cell, (b) a newline token at each row boundary, and (c) the D4 augmentations
forcing the model to learn orientation-invariant rules.

This is the sharpest architectural contrast in the field: the ARChitects' 2025
diffusion branch replaced 1D RoPE with a 2D Golden-Gate RoPE and expanded grids
to a fixed 32x32, and TRM uses a fixed-size grid canvas. NVARC won with none of
it. Puget's own earlier work (`nvarc_2025.pdf` [12], "A 2d ngpt model for arc
prize") was a 2D transformer that he reports did *not* benefit from BARC data
(§3.5) and was not the winning entry.

## 8. Augmentations

One augmentation function, used identically for training, TTT and rescoring:

- **Dihedral**: all 8 of D4, implemented as rot90 k∈{0,1,2,3}, fliplr, flipud,
  transpose, anti-diagonal (`build_datasets.py:12-31`).
- **Colour permutation**: a random permutation of all 10 colours, applied to
  input and output alike. Note colour 0 is **not** held fixed, unlike TRM's
  data pipeline which fixes black.
- **Example shuffling**: demonstration order permuted per sample.
- **Example subsetting**: 5-6 pairs sampled from synthetic puzzles, 6-7 from
  RE-ARC (`build_datasets.py:180,232`).

Validity filter (`build_datasets.py:74-116`) rejects a sampled pair set when all
inputs are not distinct, all outputs are identical, or inputs/outputs are
single-colour and single-shape. A cheap, deterministic quality gate.

## 9. Synthetic data generation — where the score comes from

Four stages (`nvarc_2025.pdf` §2, `SDG/README.md`):

1. **Seed descriptions.** H-ARC (natural-language solution descriptions from
   1700+ humans) + 160 human descriptions from BARC → descriptions for 716
   ARC-AGI-2 training puzzles. Then 29 ARC-AGI-2 **public evaluation** puzzles
   labelled by hand, and summaries for the remaining 91 generated by
   claude-sonnet-4-5 from those examples. Total 3268 puzzle summaries
   (716x3 + 29 + 91 + 1000).
2. **Mixing.** INSTRUCT-SKILLMIX-style: prompt gpt-oss-120b to fuse two
   summaries into one harder puzzle. **266,593 new summaries.**
3. **Input-grid programs.** Generate Python that produces input grids, plus
   generated unit tests. Keep programs producing >= 30 distinct valid inputs
   that pass their tests. **126,901 kept.** Acceptance ~70% for
   training-puzzle mixtures, ~50% for evaluation-puzzle mixtures.
4. **Output-grid programs.** Generate ~20 output programs per input program;
   keep only those where >= some quorum produce identical outputs on all 30
   inputs. **103,253 puzzles kept, ~30 pairs each.**

The validation strategy is the whole trick. Stage 3 validates by *execution*,
stage 4 by *agreement across independent samples*. Compare the ARChitects, who
generated synthetic tasks and filtered by human aesthetic judgement, got ~1 in
50-100 usable, and abandoned the line (`docs/systems/ARCHITECTS.md` §Negative).

**Final training mix** (`nvarc_2025.pdf` Table 1):

| Source | Unique puzzles | Aug/puzzle | Samples | Share |
| --- | --- | --- | --- | --- |
| MINI-ARC | 147 | 256 | 37,632 | 1.2% |
| ConceptARC | 160 | 256 | 40,960 | 1.3% |
| RE-ARC | 400 | 256 | 102,392 | 3.2% |
| ARC-AGI-2 | 609 | 256 | 155,904 | 4.8% |
| NVARC training | 47,337 | 24 | 1,132,633 | 34.8% |
| NVARC full | 55,886 | 32 | 1,785,960 | 54.9% |
| **total** | 104,539 | | **3,255,481** | |

`build_datasets.py:243-275` writes exactly these seven subsets into
`data/grids_v15`, and the checkpoint the 2026 baseline loads is named
`qwen3_4b_grids15_sft139` (`ARChitects/run_sft_4b.sh:7`). The lineage from this
script to that checkpoint is direct and named.

### The contamination is worse than the paper states

The paper discloses leaking evaluation *descriptions* into the synthetic data.
The code does more than that:

```python
ds = convert_arc_to_messages("external/ARC-AGI-2/data/evaluation/*.json", num_samples=6)
ds.save_to_disk(f"{output_path}/arc2_evaluation6")
```
`SDG/scripts/build_datasets.py:245-246`

and `convert_arc_to_messages` builds its message list from
`pairs = data["train"] + data["test"]` (`build_datasets.py:158`), where the
GitHub task files carry test **outputs** inline.

**So the SFT dataset `grids_v15` contains all 120 public evaluation tasks,
including their test-pair ground-truth grids, at 6 augmented copies each.** This
is direct supervision on the answers, not description leakage.

`ARChitects/README.md` confirms `arc2_evaluation6` is one of the seven subsets
fed to `run_sft_4b.sh`.

**Consequence: the 120-task public evaluation set measures nothing about
generalisation for `qwen3_4b_grids15_sft139` or any sibling checkpoint.** This is
the single most important finding of the whole audit and it governs
`docs/DATASET_AUDIT.md` §6 and `docs/BASELINE_SELECTION.md`.

It also reframes NVARC's own Table 2. "Evaluation score (120 puzzles) = 30" for
Qwen3-4B-Thinking-2507 against a 29.72% LB is not a validated correlation
between a held-out set and the leaderboard — it is a memorisation-capable model
scoring 25% on data it was trained on. The near-agreement with the LB is
coincidence, or evidence that the model failed to memorise, which would be
stranger still.

## 10. Test-time training

| Parameter | ARChitects branch | TRM branch |
| --- | --- | --- |
| Scope | one LoRA per puzzle, reset between puzzles | full weights per puzzle |
| Adapter | LoRA r=256, alpha=32 | n/a |
| Precision | bfloat16, 4-bit quantisation removed, no gradient checkpointing | — |
| Data | the puzzle's own demonstration pairs, augmented | same |
| Steps | 1 epoch over the augmented set | 2000 epochs, 200 warmup |
| Time | within a 12 h budget for 240 tasks | ~2 h for 240 tasks |
| Framework | Unsloth + Flash Attention 2 | modified TRM `pretrain.py` |

TRM detail worth recording: the pretrained puzzle embeddings are **not
reusable** because the test puzzles are different puzzles. TRM's codebase
resizes the embedding table and initialises new rows with the mean of the
pretrained embeddings (§4.2). The recursive network transfers; the per-puzzle
memory does not.

## 11-13. Candidates, ranking, verification

**Generation.** Batched depth-first search over the token tree, keeping every
path whose cumulative NLL stays under a threshold. Scales near-linearly with
batch size. Batching makes it **non-deterministic** (§3.3, citing Thinking
Machines Lab); a batch-invariant version was implemented, improved local
precision, ran 17% slower, and was dropped.

**Ranking.** `nvarc_2025.pdf` §3.4:

```
score_agg(s) = Σ_{c ∈ C_p} [c = s]  +  (1/m) Σ_{j=1..m} log P̂_j(s),   m = 8
```

Vote count across DFS generations, plus mean log-likelihood under 8
augmentations. Implemented as `score_kgmon` in
`docs/reference_exports/nvarc_t4x2_notebook.py:330-336`.

The one deliberate change from the ARChitects' product-of-experts: **the same 8
augmentations are used for every candidate**, so scores are comparable across
candidates rather than each candidate being scored under its own random views.

**Verification: none.** Nothing in NVARC checks whether a candidate is
consistent with the demonstration pairs. Every score is a preference derived
from the model's own likelihood. Compare SOAR, where a program either reproduces
the demonstrations or is discarded.

## 14. Compute allocation per task

Uniform. Every puzzle gets the same TTT recipe and the same DFS budget, with
only wall-clock guards. In the 2026 notebook: a global end time, a 1200 s
per-puzzle cap, and a 540 s per-DFS cap (`nvarc_t4x2_notebook.py:539, 852`).

There is no signal of difficulty, no early exit on confidence, no reallocation
from easy tasks to hard ones. **The entire compute-routing question is
untouched by the strongest public system.**

## 15-16. Global versus per-task components

| Trained globally, offline | Adapted per task, online |
| --- | --- |
| Qwen3-4B SFT on 3.2M samples | LoRA r=256 adapter |
| TRM recursive network | TRM puzzle embeddings + full weights |
| Cut tokenizer | — |

## 17-19. Requirements

- **Data**: 3.2M augmented samples derived from 104,539 puzzles, of which 103k
  are LLM-generated. Reproducing them needs gpt-oss-120b inference at scale plus
  claude-opus-4 and claude-sonnet-4-5 API access.
- **Checkpoints**: `qwen3_4b_grids15_sft139` (Kaggle), TRM `arc-prize-trm-031`.
- **Offline training**: 4x8 H100 for 27 h (Qwen3-4B), 8xH100 for 24 h (TRM).
- **Inference**: Kaggle 12 h, 4x L4. The 2026 port targets 2x T4.

## 20. Kaggle-offline deployment

Internet disabled. Model attached as a Kaggle model source, pip wheels supplied
by a companion notebook (`sorokin/pip-install-unsloth-flash-patch`). One worker
process per GPU, each pinned via `CUDA_VISIBLE_DEVICES`, pulling task ids from a
shared `mp.Manager().Queue()`. Per-task results written as bz2 pickles to disk,
then a final cell aggregates and writes `submission.json`.

## 21. What generates most of the score

Unambiguous, from the paper's own Figure 1 — same architecture, same inference
code, only the data mix varied:

| Data mix | Public LB |
| --- | --- |
| + BARC | 12.92% |
| + NVARC synthetic (three runs) | 17.50% / 13.75% / 15.83% |
| no BARC, + more NVARC synthetic | **27.64%** |

**Synthetic data more than doubled the score.** No architectural change in the
paper comes close. The candidate-selection improvement (§3.4) was found after
the deadline and is reported with no isolated number at all.

## 22. Inherited components

| Component | Origin |
| --- | --- |
| `ArcDataset`, augmentation grammar, submission writer | ARChitects 2024/2025 (Apache-2.0) |
| DFS over the token tree | ARChitects 2024 |
| Product-of-experts rescoring | ARChitects 2024 |
| Per-task TTT | ARChitects 2025, itself from MindsAI 2023 |
| Recursive network + deep supervision | TRM (Samsung SAIL), itself simplifying HRM |
| RE-ARC, ConceptARC, MINI-ARC, H-ARC, BARC corpora | third parties |
| Unsloth, NeMo-RL, Megatron | NVIDIA / Unsloth |

**Original to NVARC**: the SDG pipeline and its execution-plus-agreement
validation; the 16-token cut tokenizer; the `score_agg` selection rule; the
batched DFS implementation; the batch-invariance analysis. See
`docs/NVARC_LINEAGE.md`.

## 23. Redundant components

- **The TRM branch.** §4.4: "when using a Qwen3 4B submission that uses 10 hours
  only, with a score 27.22, adding TRM yields the same 27.22 score." It helped
  the weaker 2B configuration (21.53 → 22.50) and contributed nothing at 4B.
- **Batch-invariant decoding.** Better precision, 17% slower, dropped.
- **BARC data.** Removed from the final mix; correlated with the worst run.

## 24. Likely public-set patches

**None found.** No task-id branching anywhere in the repository or the 2026
notebook. The one hardcoded id list in the notebook
(`nvarc_t4x2_notebook.py:973`) restricts *interactive* runs to four evaluation
tasks for debugging and is bypassed under `KAGGLE_IS_COMPETITION_RERUN`.

The eval-set contamination in §9 is a *training-data* problem, not a
public-set patch, and it does not transfer to the hidden set.

## 25. Likely hidden-set failure modes

1. **Sequence-length truncation.** `cut_to_len` silently drops demonstration
   pairs when the formatted task exceeds 8192 tokens. Per
   `docs/DATASET_AUDIT.md` §4, evaluation-distribution tasks are 3.3x larger by
   area than training-distribution ones, so this fires far more on hard tasks —
   removing evidence exactly where it is most needed. Unmeasured by anyone.
2. **No verification.** Selection is a likelihood preference. A confidently wrong
   candidate beats a correct one that the model finds surprising.
3. **Uniform compute.** A task needing 3x the search gets the same budget as one
   solved in the first beam.
4. **No 2D inductive bias.** The ARChitects independently concluded their
   autoregressive model could not handle tasks requiring global structural
   change, which motivated their entire diffusion pivot.
5. **Non-determinism.** Batched DFS gives different candidate sets run to run,
   so the reported score has run-to-run variance the paper acknowledges as
   "1-2 points" (§3.5).

## 26-27. Ablations reported and missing

**Reported:** data-mix ablation (Fig. 1); model size 2B vs 4B (Table 2);
TRM-with vs TRM-without at two budgets (§4.4); TRM epoch count 2k vs 4k (§4.3).

**Missing, and cheap:**

- `score_agg` versus the 2024 product-of-experts scorer. Called "better" with no
  number, while both ship side by side in the 2026 notebook with a comparison
  function already written.
- Number of rescoring augmentations (fixed at 8, ARChitects used 32).
- DFS cutoff threshold.
- TTT step and augmentation count.
- TTT on versus off, at fixed data.
- Per-task solve sets for the two branches. §4.4 says "about 2 or 3 puzzles
  solved by TRM were not solved by Qwen3" — a count with no task list, and the
  entire empirical basis for anyone's routing hypothesis.

## 28-30. Reproducibility

**Not reproducible from the repository.** The repo contains configs, prompts and
launcher scripts; it does not contain the generated data, the checkpoints, or
the submission notebooks.

| Step | Command / file | Available |
| --- | --- | --- |
| Fetch corpora | `git submodule update --init` | **no**, 7 submodules empty locally |
| Generate synthetic puzzles | `SDG/scripts/*.py` + NeMo-Skills + gpt-oss-120b | **no**, needs cluster-scale LLM inference |
| Build training subsets | `SDG/scripts/build_datasets.py` | script yes, inputs no |
| SFT | `ARChitects/run_sft_4b.sh` on Slurm, 4x8 H100 | script yes, compute no |
| Inference | Kaggle `sorokin/arc2-qwen3-unsloth-flash-lora-batch4-queue` | **not in the repo** |
| TRM pretrain | `TRM/pretrain-no-eval.py` | script yes, 8xH100 and datasets no |
| TRM inference | Kaggle `cpmpml/arc2-trm-v31` | **not in the repo** |

The shortcut the authors intend is downloading their published Kaggle datasets
and checkpoints, which requires Kaggle credentials we do not have
(`metadata/KAGGLE_DOWNLOAD_PENDING.txt`).

**Remains permanently unavailable to us**: the 27 h x 32 H100 SFT run and the
LLM inference behind 126,901 generated programs.
