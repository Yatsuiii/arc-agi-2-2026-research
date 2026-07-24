# NVARC_COMPONENT_MAP

Module-level structure and data flow. Diagrams are ASCII so they diff cleanly.

## A. Offline pipeline (everything before the Kaggle notebook)

```
 SEED DATA                    external/ submodules (none fetched locally)
 ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐
 │ H-ARC        │  │ BARC         │  │ RE-ARC   │  │ ConceptARC │  │ MINI-ARC │
 │ 1700+ human  │  │ 160 human    │  │ 400 gen. │  │ 160        │  │ 147      │
 │ descriptions │  │ descriptions │  │ puzzles  │  │            │  │          │
 └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └─────┬──────┘  └────┬─────┘
        │ h_arc_clean.py  │ barc_clean.py │              │              │
        └────────┬────────┘               │              │              │
                 ▼                        │              │              │
      ┌─────────────────────────┐         │              │              │
      │ STAGE 1  summaries      │         │              │              │
      │ prompts/summary_v{1,2}  │◄────────┼──────────────┼──── ARC-AGI-2
      │ claude-opus-4 /         │         │              │     train (1000)
      │ gpt-oss-120b            │         │              │     + EVAL (120)
      │ → 3268 summaries        │         │              │        │
      │   (716x3 + 29 manual    │         │              │        │
      │    + 91 gen + 1000)     │         │              │        │
      └───────────┬─────────────┘         │              │        │
                  ▼                       │              │        │
      ┌─────────────────────────┐         │              │        │
      │ STAGE 2  skill mixing   │         │              │        │
      │ prompts/mix_v{1,2}      │         │              │        │
      │ gpt-oss-120b            │         │              │        │
      │ → 266,593 summaries     │         │              │        │
      └───────────┬─────────────┘         │              │        │
                  ▼                       │              │        │
      ┌─────────────────────────┐         │              │        │
      │ STAGE 3  input programs │         │              │        │
      │ generate_input_grids.py │         │              │        │
      │ VALIDATED BY generated  │         │              │        │
      │ unit tests, >=30 grids  │         │              │        │
      │ → 126,901 programs      │         │              │        │
      └───────────┬─────────────┘         │              │        │
                  ▼                       │              │        │
      ┌─────────────────────────┐         │              │        │
      │ STAGE 4  output programs│         │              │        │
      │ generate_output_grids.py│         │              │        │
      │ VALIDATED BY agreement  │         │              │        │
      │ across ~20 samples      │         │              │        │
      │ make_pairs.py           │         │              │        │
      │ → 103,253 puzzles       │         │              │        │
      └───────────┬─────────────┘         │              │        │
                  ▼                       ▼              ▼        ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │ build_datasets.py  →  data/grids_v15/                            │
      │   arc2_evaluation6  (120 tasks x 6)   ◄── CONTAMINATION          │
      │   rearc             (400 x 256)                                  │
      │   arc2_training     (609 x 256)                                  │
      │   mini              (147 x 256)                                  │
      │   concept           (160 x 256)                                  │
      │   nvarc_training    (47,337 x 24)                                │
      │   nvarc_full        (55,886 x 32)                                │
      │   ────────────────────────────────                               │
      │   3,255,481 augmented samples                                    │
      └──────────────────────────┬───────────────────────────────────────┘
                                 │
        ┌────────────────────────┴────────────────────────┐
        ▼                                                 ▼
 ┌──────────────────────────┐                  ┌──────────────────────────┐
 │ BRANCH 1  ARChitects     │                  │ BRANCH 2  TRM            │
 │ cut_tokenizer.ipynb      │                  │ pretrain-no-eval.py      │
 │   Qwen3 vocab → 16       │                  │   L_layers=2             │
 │ run_sft_4b.sh            │                  │   H_cycles=3 L_cycles=4  │
 │   NeMo-RL + Megatron     │                  │   batch 3072, lr 3e-4    │
 │   4 nodes x 8xH100, 27 h │                  │   8xH100, 24 h           │
 │   TP=8, 12,716 steps     │                  │   10k epochs             │
 │   batch 256, lr 1e-4     │                  │   3k synth + 1.2k real   │
 │   seq packing 256k tok   │                  │   256 aug/puzzle         │
 │ → qwen3_4b_grids15_sft139│                  │ → arc-prize-trm-031      │
 └──────────────────────────┘                  └──────────────────────────┘
```

`sft_mg.yaml` holds the base config; `run_sft_4b.sh` overrides it with the exact
values above and names the experiment `qwen3_4b_grids15_sft139` — the same
string as the Kaggle model the 2026 notebook loads.

## B. Online pipeline, branch 1 (the winning system, and the 2026 baseline)

```
                        arc-agi_test_challenges.json
                                    │
                    ┌───────────────┴───────────────┐
                    │  task queue (mp.Manager)      │
                    └───┬───────────────────────┬───┘
                        │                       │
                 ┌──────▼──────┐         ┌──────▼──────┐
                 │  rank 0     │         │  rank 1     │   (4 on L4, 2 on T4)
                 │  GPU 0      │         │  GPU 1      │
                 └──────┬──────┘         └──────┬──────┘
                        │                       │
        ┌───────────────▼───────────────────────▼──────────────┐
        │  per task, identical in each worker:                  │
        │                                                       │
        │  1. reset LoRA to the pretrained state                │
        │                                                       │
        │  2. TEST-TIME TRAINING                                │
        │     augment(n=16): D4 x colour perm x example shuffle │
        │     cut_to_len(8192)  ◄── DROPS demonstration pairs   │
        │     1 epoch, LoRA r=256 (attn+MLP+embed+lm_head)      │
        │     lr 5e-5, cosine, adamw_8bit                       │
        │                                                       │
        │  3. CANDIDATE GENERATION                              │
        │     augment(n=2) → 16 views per test input            │
        │     grouped into 8 batches of 4                       │
        │     turbo_dfs, cutoff -log(0.2), depth-first over     │
        │       the token tree with shared KV cache             │
        │     → many candidate grids per view                   │
        │     invert_mod: map each candidate back to the        │
        │       original frame using its augmentation key       │
        │                                                       │
        │  4. CANDIDATE RESCORING                               │
        │     for each unique candidate grid:                   │
        │       build 8 fixed augmented (query, answer) pairs   │
        │       calc_scores → 8 negative log-likelihoods        │
        │     (memoised per (task, grid))                       │
        │                                                       │
        │  5. persist {beam_score, score_aug[8], solution}      │
        │     as bz2 pickle, one file per augmented subkey      │
        └───────────────────────┬───────────────────────────────┘
                                ▼
                  ┌───────────────────────────────┐
                  │ ArcDecoder                    │
                  │  load all pickles per task    │
                  │  group identical grids        │
                  │  score_kgmon:                 │
                  │    n_generations              │
                  │    - mean(mean(score_aug))    │
                  │  take top 2                   │
                  └───────────────┬───────────────┘
                                  ▼
                          submission.json
```

## C. Where each of the 30 teardown answers lives

| Question | File |
| --- | --- |
| tokenisation, vocabulary | `ARChitects/qwen3_configs/vocab.json`, `added_tokens.json` |
| grid ↔ string | `SDG/scripts/build_datasets.py:122`, notebook cell 2 |
| augmentation | `SDG/scripts/build_datasets.py:12-70`, notebook `ArcDataset.augment` |
| SFT hyperparameters | `ARChitects/run_sft_4b.sh`, `ARChitects/sft_mg.yaml` |
| TTT hyperparameters | notebook `worker()`, `peft_params` / `train_args` |
| DFS | notebook `turbo_dfs`, `inference_turbo_dfs` |
| rescoring | notebook `calc_scores` |
| selection | notebook `arc_decoder.py`, `score_kgmon` / `score_full_probmul_3` |
| TRM training | `TRM/README.md`, `TRM/pretrain-no-eval.py` |
| TRM evaluation | `TRM/eval-arc-k-10.py` |
| synthetic data | `SDG/README.md`, `SDG/scripts/`, `SDG/prompts/` |

## D. Cost profile per task, branch 1

| Stage | Cost | Scales with |
| --- | --- | --- |
| LoRA reset | negligible | — |
| TTT | ~16 forward+backward over the full formatted task | grid area, demo count |
| DFS | dominant; 8 batches x tree depth ~ output cells | **output area**, candidate breadth, cutoff |
| Rescoring | 8 forward passes per **unique** candidate | number of distinct candidates |
| Selection | negligible, CPU | — |

Two consequences the audit turns on:

1. Cost is driven by output grid area and by how many distinct candidates the
   DFS finds. Both are observable *before* the expensive part finishes, which is
   what makes compute-aware routing mechanically possible.
2. Rescoring is memoised per unique grid, so a task whose DFS converges on few
   distinct candidates is cheap and a task with many is expensive — and the
   expensive case is also the case where selection matters most.

## E. Persisted intermediate artifact

The per-task bz2 pickles written in step 5 contain, for every candidate:
`beam_score`, the eight `score_aug` values, and the grid. Once written, **every
selection question becomes a CPU-only reanalysis of stored data**: alternative
scorers, augmentation-count sweeps, oracle@k, calibration.

This is the single most useful structural fact in the whole audit and it shapes
`paper/ABLATION_MATRIX.md` (AB-S1, AB-S2) and `experiments/EXP001/PLAN.md`.
