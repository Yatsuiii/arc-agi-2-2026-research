# NVARC_LINEAGE

NVARC is not one method. It is two independently trained solvers assembled from
four upstream lineages, with a data pipeline that is the only genuinely new
large component. This document reconstructs where each part came from.

## Ancestry graph

```
                     MindsAI / Cole & Osman 2023
                     "dataset-induced meta-learning", TTFT
                                  │
                                  ▼
     ARChitects 2024 (ARC Prize 2024 winner, 53.5% ARC-AGI-1)
     ├── ArcDataset + D4/colour/example augmentation grammar
     ├── batched DFS over the token tree (cutoff 17%)
     ├── product-of-experts rescoring under augmentations
     └── multi-task LoRA test-time training
                                  │
                                  ▼
     ARChitects 2025 branch A (16.94% ARC-AGI-2)
     ├── per-task TTT instead of multi-task          ────┐
     ├── speculative decoding in DFS (4.7x, cutoff→7%)   │
     └── prefix caching for scoring (5.8x, augs 8→32)    │
                                                         │
     HRM (Wang et al. 2025)                              │
        └── TRM (Jolicoeur-Martineau 2025, MIT) ───┐     │
            ├── recursive (x,y,z) refinement       │     │
            ├── deep supervision, N_sup=16         │     │
            └── per-puzzle embedding table         │     │
                                                   │     │
                                                   ▼     ▼
                              NVARC 2025 (27.64% ARC-AGI-2)
                              ├── branch 1: ARChitects lineage on Qwen3-4B
                              ├── branch 2: TRM lineage
                              └── NEW: SDG pipeline, cut tokenizer, score_agg
                                                   │
                                                   ▼
                       2026 T4x2 baseline notebook (branch 1 only)
```

## Component provenance table

| # | Component | Original source | NVARC's modification | Purpose | Compute cost | Reported contribution | Ablation available | Licence status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `ArcDataset`, augmentation key grammar | ARChitects (Apache-2.0), `pretraining_code/arc_loader.py` | rewritten and simplified; dihedral extended to explicit 8 members incl. flips | task representation, augmentation, submission writing | negligible | not isolated | none | Apache-2.0 at source; **notice stripped in the 2026 notebook** |
| 2 | Batched DFS over the token tree | ARChitects 2024 | reimplemented as a batch algorithm scaling near-linearly with batch size; batch-invariance tested and rejected (17% slower) | candidate generation | dominant inference cost | not isolated | **none**; cutoff never swept | RESEARCH REFERENCE ONLY |
| 3 | Augmentation rescoring | ARChitects 2024 product-of-experts | fixed at m=8 and made **identical across candidates** so scores are comparable | candidate ranking | ~8 forward passes per unique candidate | not isolated | **none** | RESEARCH REFERENCE ONLY |
| 4 | `score_agg` / `score_kgmon` selection rule | **NVARC original** | vote count + mean augmented log-likelihood | final answer choice | negligible | "better method", **no number** | **none**, though the 2026 notebook ships a comparison function | RESEARCH REFERENCE ONLY |
| 5 | Per-task LoRA TTT | MindsAI 2023 → ARChitects 2025 | r=256, alpha=32, bf16, 4-bit and gradient checkpointing removed | per-task adaptation | large; per task | not isolated | **none** | RESEARCH REFERENCE ONLY |
| 6 | 16-token cut tokenizer | **NVARC original** | Qwen3 vocab 151,936 → 16 | removes ~0.78B embedding params; makes 4B trainable on small GPUs | one-off | not isolated, **and not discussed in the paper** | none | artifacts in repo, RESEARCH REFERENCE ONLY |
| 7 | Qwen3-4B-Thinking-2507 base | Alibaba (Apache-2.0) | vocab cut, then SFT | backbone | 4 nodes x 8 H100 x 27 h | 2B→4B: 22.22%→29.72% (Table 2) | **yes**, model-size ablation | base Apache-2.0; **fine-tune published on Kaggle, licence unchecked** |
| 8 | SDG pipeline (4 stages) | **NVARC original**, methodologically indebted to BARC and INSTRUCT-SKILLMIX | LLM summaries → mixing → input programs validated by generated unit tests → output programs validated by cross-sample agreement | training data | very large; gpt-oss-120b at scale | **12.92% → 27.64%** | **yes**, Fig. 1 — the only decisive ablation in the paper | RESEARCH REFERENCE ONLY |
| 9 | H-ARC descriptions | Le-Gris et al., *Scientific Data* 2025 | filtered and reformatted | SDG seed data | negligible | not isolated | none | upstream licence, not fetched |
| 10 | BARC descriptions and data | Li et al. 2024 | 160 descriptions kept; **the BARC dataset itself removed from the final mix** | SDG seed data | — | negatively correlated (Fig. 1) | **yes**, implicitly | upstream, not fetched |
| 11 | RE-ARC | Hodel 2024 | 400 puzzles, 256 aug each, 6-7 pairs sampled | training data, 3.2% | small | not isolated | none | upstream, not fetched |
| 12 | ConceptARC | Moskvichev et al. 2023 | 160 puzzles, 256 aug | training data, 1.3% | small | not isolated | none | upstream, not fetched |
| 13 | MINI-ARC | Kim et al. 2022 | 147 puzzles, 256 aug | training data, 1.2% | small | not isolated | none | upstream, not fetched |
| 14 | ARC-AGI-2 train + **eval** | ARC Prize (Apache-2.0) | 609 puzzles at 256 aug, **plus all 120 eval tasks with test answers at 6 aug** | training data, 4.8% | small | not isolated | none | Apache-2.0 data; **contaminates the eval split** |
| 15 | TRM recursive network | Samsung SAIL (MIT) | batch 3072 (from 768), lr 3e-4 (from 1e-4), 10k epochs (from 100k), 3k synthetic + 1200 real puzzles, 256 aug | branch 2 solver | 8xH100 x 24 h | 2.08% alone → 10.0% tuned | **yes**, epoch count 2k vs 4k | MIT upstream; NVARC's derived scripts ship without the notice |
| 16 | TRM per-puzzle embedding table | Samsung SAIL | resized and mean-initialised at test time | per-puzzle memory | 512 params x n_puzzles | criticised, not ablated | none | MIT |
| 17 | Branch ensembling | **NVARC original** | TRM emits 10 attempts, merged into the ARChitects candidate pool and rescored by Qwen3 | coverage | integration cost only | **2B: 21.53→22.50. 4B: 27.22→27.22 (zero)** | **yes**, §4.4 | RESEARCH REFERENCE ONLY |
| 18 | NeMo-RL / Megatron SFT stack | NVIDIA | config only | training infrastructure | — | n/a | none | upstream |
| 19 | Unsloth + Flash Attention 2 | Unsloth | used as-is; T4 port swaps in xformers | inference and TTT speed | — | n/a | none | upstream |

## What is actually original to NVARC

Four things, in descending order of demonstrated value:

1. **The SDG pipeline** (#8). The only component with a decisive published
   ablation, and it more than doubled the score. Its real innovation is the
   *validation* strategy: executable unit tests for input programs, cross-sample
   agreement for output programs. Both are machine-checkable, which is why it
   scaled where the ARChitects' human-judged pipeline did not.
2. **The 16-token cut tokenizer** (#6). Not mentioned in the paper at all;
   recoverable only from `ARChitects/qwen3_configs/vocab.json` and the
   `-16t` model path. It is what makes a 4B model test-time trainable inside a
   Kaggle GPU budget, and therefore what makes the whole approach feasible.
3. **`score_agg`** (#4). One line of arithmetic, claimed to be an improvement,
   never measured.
4. **The batched-DFS engineering and its batch-invariance analysis** (#2).

Everything else is inherited.

## Does the score come from solver quality or ensemble coverage?

**Solver quality, decisively — and the ensemble contributed nothing at the
winning configuration.**

Evidence, `nvarc_2025.pdf` §4.4: at the 2B scale, adding TRM moved 21.53 → 22.50
(+0.97). At the 4B scale, "when using a Qwen3 4B submission that uses 10 hours
only, with a score 27.22, adding TRM yields the same 27.22 score." The final
submission used Qwen3-4B alone.

The authors also record *why* the ensemble failed to help: "about 2 or 3 puzzles
solved by TRM were not solved by Qwen3. Unfortunately, these were not always
picked by Qwen3 scoring."

Read carefully, that sentence contains two separable failures:

1. **Coverage is small.** Only 2-3 of 240 tasks were TRM-unique. So the routing
   headroom between these two specific solvers is about 1%.
2. **Even that coverage was lost at selection.** The correct candidates existed
   in the pool and the Qwen3 scorer did not rank them into the top 2.

Failure 2 is the more interesting one, because it is a *selection* failure on
candidates that were successfully generated, and it is exactly branch S of
`paper/FAILURE_TAXONOMY.md`. It is also reported with no numbers, on a sample of
2-3 tasks, in a paper written after the deadline.

**This single sentence is the entire public empirical basis for the routing and
verification hypotheses.** It is far too thin to build on without measuring it
ourselves, which is the reason EXP001 exists.

## What the 2026 baseline inherits

Only branch 1. Components #1-#7 and #14, with the TRM lineage (#15-#17) absent
entirely. See `docs/NVARC_2026_T4_BASELINE_AUDIT.md`.
