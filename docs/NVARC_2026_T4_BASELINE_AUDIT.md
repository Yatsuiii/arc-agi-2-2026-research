# NVARC 2026 2xT4 baseline — notebook audit

Artifact: `references/2026_baselines/nvarc_t4x2/baseline-nvarc-arc-25-winning-solution-for-t4x2.ipynb`
Kaggle id: `nihilisticneuralnet/baseline-nvarc-arc-25-winning-solution-for-t4x2` (id_no 113828488)
Readable export: `docs/reference_exports/nvarc_t4x2_notebook.py` (1015 lines)

Static analysis only. The notebook was not executed, no checkpoint was
downloaded, and no GPU was touched, per the implementation limits.

## Structure

8 cells, **all code, zero markdown**, zero stored outputs. Cells 2-5 are
`%%writefile` cells that emit four Python modules:

| Cell | Emits | Role |
| --- | --- | --- |
| 0 | — | sets `global_end_time = now + 12h - 1200s` |
| 1 | — | `pip uninstall -y tensorflow` |
| 2 | `arc_loader.py` | `QwenFormatter`, `ArcDataset` |
| 3 | `arc_decoder.py` | two selection algorithms, `ArcDecoder` |
| 4 | `arc_solver.py` | `turbo_dfs`, `calc_scores`, `worker` |
| 5 | `starter.py` | multiprocess launcher |
| 6 | — | runs `starter.py` |
| 7 | — | aggregates results, writes `submission.json` |

## 1. Is it the full NVARC system?

**No. It is branch 1 only, and only in its Qwen3-4B form.**

| NVARC component | In this notebook |
| --- | --- |
| ARChitects branch (Qwen3-4B + TTT + DFS + rescoring) | **yes** |
| TRM branch | **absent** |
| Branch ensembling | **absent** |
| SDG pipeline | absent by construction — its output is baked into the checkpoint |

This is the right choice on the evidence: NVARC §4.4 reports the ensemble added
exactly zero at 4B (27.22 → 27.22). The notebook drops the branch that did not
help.

## 2. What was removed or simplified from 2025

| 2025 (NVARC on 4xL4) | 2026 notebook (2xT4) | Reason |
| --- | --- | --- |
| bfloat16 TTT, 4-bit quantisation **removed** (§3.2) | `load_in_4bit=True`, `dtype=float16`, `fp16=False, bf16=False`, `half_precision_backend="cpu_amp"` | T4 is sm75: no bf16, and 16 GB forces 4-bit |
| Flash Attention 2 via Unsloth | `attn_implementation="eager"`, plus a monkeypatch replacing `unsloth.models.qwen3.flash_attn_func` with xformers `memory_efficient_attention`, manually repeat-interleaving KV heads for GQA | FA2 requires sm80+ |
| 4 workers on 4x L4 | 2 workers on 2x T4, `mp.spawn(nprocs=2)` | hardware |
| `score_agg` described post-deadline | both `score_full_probmul_3` and `score_kgmon` shipped; `score_kgmon` is the default | — |
| gradient checkpointing removed | same (`use_gradient_checkpointing=False`) | — |

Also present: a workaround for Unsloth issue #2435 (`UnslothFixedTrainer` clones
the loss tensor before DDP scaling), and a rank-serialised startup where rank N
waits for `/kaggle/worker{N-1}` to exist before importing Unsloth, to avoid a
patching race.

## 3-5. Checkpoint

`FastLanguageModel.from_pretrained("/kaggle/input/qwen3_4b_grids15_sft139/transformers/bfloat16/1", local_files_only=True)`

Kaggle model source: `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1`
(`kernel-metadata.json:23`).

**How it was trained — fully traceable.** The name is the experiment name in
`references/score_winners/01_nvarc/ARChitects/run_sft_4b.sh:7`:

```
EXP_NAME="qwen3_4b_grids15_sft139"
policy.model_name="/models/Qwen3-4B-Thinking-2507-16t"
cluster.num_nodes=4                       # 4 x 8 H100
policy.megatron_cfg.tensor_model_parallel_size=8
sft.max_num_steps=12716, max_num_epochs=1
policy.train_global_batch_size=256
optimizer.lr=1e-4, min_lr=1e-7, clip_grad=0.5
scheduler.lr_warmup_iters=200, lr_decay_iters=12716
sequence_packing.train_mb_tokens=256000
sft.seed=24
```

Base: Qwen3-4B-Thinking-2507 with the vocabulary cut to 16 tokens.
Data: `data/grids_v15` — the seven subsets written by
`SDG/scripts/build_datasets.py`, 3,255,481 augmented samples.

**Including `arc2_evaluation6`: all 120 ARC-AGI-2 public evaluation tasks, with
their test-pair ground-truth outputs, at 6 augmented copies each**
(`build_datasets.py:158,245-246`). See `docs/systems/NVARC.md` §9.

## 6. Dependency notebook

`sorokin/pip-install-unsloth-flash-patch` (kernel source, id 272622465). Supplies
offline pip wheels for Unsloth and the flash-attention patch. Not present
locally; contents unaudited.

## 7. Internet

Disabled. `kernel-metadata.json:11 "enable_internet": false` and notebook
metadata `"isInternetEnabled": false`.

## 8. Use of two T4 GPUs

`starter.py` builds an `mp.Manager().Queue()` of task ids, pushes two `None`
sentinels, and `mp.spawn(local_worker, nprocs=2)`. Each child sets
`CUDA_VISIBLE_DEVICES=str(rank)` **before importing torch CUDA**, then loads its
own model copy and pulls tasks off the shared queue until empty or out of time.

This is dynamic load balancing, not a static split — a task that finishes early
frees its worker. Sensible given the highly variable per-task cost documented in
`docs/NVARC_COMPONENT_MAP.md` §D.

## 9. Expected VRAM per GPU

Not measurable without running. From the configuration: Qwen3-4B in 4-bit NF4 is
~2.3 GB of weights, minus the ~0.78B embedding parameters the cut tokenizer
removes, so closer to ~1.8 GB. LoRA r=256 over 7 projection modules plus
`embed_tokens` and `lm_head` adds roughly 0.4-0.6 GB in fp16 plus optimizer
state under adamw_8bit. Activations at `max_seq_length=8192` with batch 1 and
**gradient checkpointing off** are the dominant and least predictable term.

The notebook instruments this itself (`torch.cuda.max_memory_allocated()`,
printed separately for training and inference), which is the right design and
means a single short run would answer the question empirically.

**Estimate: 8-14 GB of the 16 GB, with activations the risk.** Recorded as an
estimate, not a measurement.

## 10-11. Runtime and task count

- Global budget: `12*3600 - 1200` = **11 h 40 min** from cell 0.
- Per task: inference abandoned after **1200 s**.
- Per DFS batch: abandoned after **540 s**.
- Rerun mode processes every task in `arc-agi_test_challenges.json`.

Sanity check: 240 tasks / 2 workers x 1200 s worst case = 40 h against an 11 h 40
budget. So the time guards *will* bind, and tasks late in the sorted order may
receive little or no compute. NVARC's own 2025 run used 4 GPUs for the same 12 h,
so the T4x2 port has **roughly a quarter of the compute per task** even before
accounting for T4 being slower than L4.

**This is the central risk of the baseline and it is not documented anywhere in
the notebook.** Expect a materially lower score than 27.64%.

## 12. Test-time training iterations

```
train_ds = puzzle_ds.augment(n=16, shfl_keys=True, seed=1)
train_ds = train_ds.cut_to_len(formatter, name="text", max_len=8192)
num_train_epochs=1, per_device_train_batch_size=1, gradient_accumulation_steps=1
lr=5e-5, cosine, warmup_ratio=0.1, adamw_8bit, max_grad_norm=1.0
LoRA r=256, alpha=32, dropout 0, rslora, seed 42
target_modules = q,k,v,o,gate,up,down + embed_tokens + lm_head
```

`augment(n=16)` composes: keep original, add transpose, add 3 rot90 (stacked,
keep=True), then 16 random colour permutations, then shuffle example order.
The multiplication gives 8 orientations x 16 permutations = **128 training
samples**, one epoch, batch 1 → **~128 optimizer steps per task**.

That happens to match the ARChitects' 128 TTT steps, though by a different
route.

## 13. Candidates per task

Per test input, `augment(n=2, seed=2)` yields 16 views, grouped into 8 batches
of 4 by a hand-written index schedule (offsets 0/4, 2/6, 8/12, 10/14) that pairs
each orientation with its 180-degree rotation in the same batch.

Each batch runs `turbo_dfs` with `max_score = -log(0.2)`, i.e. keep any path
whose cumulative NLL stays under 1.609 nats. Candidate count is therefore
data-dependent and unbounded, not a fixed k.

Note the cutoff is **0.20**, against the ARChitects' 0.07 in 2025 and 0.17 in
2024. Less search, consistent with a T4 budget.

Each unique candidate is then rescored under 8 fixed augmentations
(`aug_dataset.augment(seed=hash(bk) % 1024**2)`), memoised by
`(base_key, grid)`.

## 14. Candidate selection

`ArcDecoder.run_selection_algo()` defaults to `score_kgmon`:

```python
def getter_kgmon(guesses):
    inf_score = len(guesses)                              # generation vote count
    aug_score = np.mean([np.mean(g["score_aug"]) for g in guesses])
    return inf_score - aug_score                          # votes minus mean NLL
```

This is `nvarc_2025.pdf` §3.4's `score_agg`. The alternative
`score_full_probmul_3` (the ARChitects 2024 product-of-experts, baseline 3) is
present and unused.

Identical grids from different augmented views are grouped first, so the vote
count is over distinct generations of the same answer. Top 2 become `attempt_1`
and `attempt_2`.

## 15. Submission writing

`ArcDataset.get_submission` pre-fills every task and test index with
`{"attempt_1": [[0]], "attempt_2": [[0]]}`, then `fill_submission` overwrites
with whatever was decoded. **A task that times out still emits a valid
`[[0]]` entry**, so the submission is always well-formed. Good defensive design.

## 16. Claimed public score

**None.** No markdown cells, no comments, no metadata field stating a score. The
title claims lineage ("NVARC ARC'25 Winning Solution") and nothing about
performance on ARC-AGI-2 2026.

## 17. Reproducible without undocumented assets?

**No.** It requires:

1. The Kaggle model `sorokin/qwen3_4b_grids15_sft139` — ~2-8 GB, licence
   unchecked, needs Kaggle credentials we do not have.
2. The Kaggle notebook `sorokin/pip-install-unsloth-flash-patch` for offline
   wheels — contents unknown.
3. The pinned Kaggle docker image
   `gcr.io/kaggle-private-byod/python@sha256:320043e1...`.

Given all three, the notebook itself is self-contained: it writes its own
modules and has no other hidden dependency.

## 18. Does the checkpoint licence permit our use?

**Unknown.** Not checked, because checking requires loading the Kaggle model
page. The base model (Qwen3-4B-Thinking-2507) is Apache-2.0, but a fine-tune may
be published under different terms, and the Kaggle model page licence is
authoritative. Recorded as an open item in
`docs/REFERENCE_LICENSE_AUDIT.md` §9.

## 19. Public-task-specific patches?

**One hardcoded task-id list**, at `nvarc_t4x2_notebook.py:971-975`:

```python
for key in sorted(data.keys()):
    if not rerun_mode:
        if key not in ["0934a4d8", "36a08778", "981571dc", "aa4ec2a5"]:
            continue
    queue.put(key)
```

Assessment: **this is a debug filter, not a cheat.** It is guarded by
`not rerun_mode`, so under `KAGGLE_IS_COMPETITION_RERUN` every task is queued.
The four ids are evaluation tasks, used to make an interactive run finish in
minutes instead of hours. It contains no answers and no task-specific logic.

Two real consequences anyway:

1. In interactive mode the notebook reads
   `arc-agi_evaluation_challenges.json` and **loads its solutions**
   (`nvarc_t4x2_notebook.py:1000`) to self-score. That is fine as instrumentation
   and dangerous as a habit; it must not survive into anything we submit.
2. An interactive run produces a submission covering 4 tasks. Anyone reading a
   score from such a run would be reading noise.

**No other task-id branching exists anywhere in the notebook.**

## 20. Is any public score consistent with the implemented system?

There is no claimed score to check. What can be said:

- The implemented system is a faithful port of NVARC's branch 1.
- It runs on roughly a quarter of the per-task compute NVARC used, with a looser
  DFS cutoff (0.20 vs 0.07-0.17), so **it should score below 27.64%**.
- Any evaluation-set number it produces is meaningless as generalisation
  evidence, because that split is in the checkpoint's training data.

## Verdict

A clean, honest, well-engineered T4 port of the single strongest public
ARC-AGI-2 branch. It is the best available starting point in the workspace and
it carries four caveats that must travel with it:

1. Its checkpoint is trained on the public evaluation answers.
2. Its ARChitects-derived loader has had the Apache-2.0 notice stripped; if we
   reuse that code we take it from the ARChitects repository and restore the
   notice.
3. Its compute budget is a quarter of what produced 27.64%, and the time guards
   will bind.
4. Its checkpoint licence is unverified.

## What to change first, when we do run it

Not the model. Add **persistence of the per-candidate records** that already
exist in memory. The bz2 pickles written at
`nvarc_t4x2_notebook.py:909-910` already contain `beam_score`, `score_aug[8]` and
the grid per candidate — but they are written to `/kaggle/inference_outputs` and
discarded when the notebook ends. Emitting them as a notebook output artifact
turns one 12-hour GPU run into a permanent CPU-reanalysable dataset supporting
every selection ablation in `paper/ABLATION_MATRIX.md`.

That is a five-line change and it is the highest-leverage modification available.
