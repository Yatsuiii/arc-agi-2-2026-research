# RUN-001 — frozen baseline specification

Everything below is read out of the frozen notebook, not from memory.

## Provenance

| Item | Value |
| --- | --- |
| Kaggle source | `nihilisticneuralnet/baseline-nvarc-arc-25-winning-solution-for-t4x2` (id_no 113828488) |
| Source sha256 | `452dbb1fc050bad9cbba38a6802231bff91cc2970899eabb8c74e5f34f322a6c` |
| Local reference | `~/arc-agi-2-2026/references/2026_baselines/nvarc_t4x2/...ipynb` — **byte-identical to live Kaggle** |
| Frozen copy | `kaggle/run001_nvarc_frozen/reference_source.ipynb`, same sha256 |
| Instrumented | `kaggle/run001_nvarc_frozen/run001_instrumented.ipynb` sha256 `70a1f5898505cd692aaeccea6f646a7b67cb5933db4646703b360b8fdde6028d` |

## Attached assets

| Kind | Identifier |
| --- | --- |
| Model | `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1` |
| Model mount | `/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1` |
| Model weights | 2 shards, 7,267,233,496 B = **3.63B bf16 params** |
| Dependency kernel | `sorokin/pip-install-unsloth-flash-patch` (id_no 97546973) |
| Competition | `arc-prize-2026-arc-agi-2` |
| Docker image | `gcr.io/kaggle-private-byod/python@sha256:320043e14c68293f1c946585b9257123385205a58af4b94b17d31868cae4e868` |
| Accelerator | `machine_shape: NvidiaTeslaT4` → **2x Tesla T4, 15360 MiB, sm75** |
| Internet | disabled |

Runtime measured inside the pinned image: Python 3.11.13, torch 2.8.0+cu128,
xformers 0.0.32.post2, bitsandbytes 0.48.2, unsloth 2025.9.7, 19.5 GB writable.

## Model loading

```python
FastLanguageModel.from_pretrained(
    model_name=<resolved checkpoint dir>,
    full_finetuning=False, load_in_4bit=True, local_files_only=True,
    use_gradient_checkpointing=False, max_seq_length=8192,
    dtype=torch.float16, attn_implementation="eager")
```

Attention patch: `unsloth.models.qwen3.flash_attn_func` is assigned an xformers
`memory_efficient_attention` wrapper that repeat-interleaves KV heads for GQA.
**Note:** that attribute does not exist in unsloth 2025.9.7, so the assignment
may be inert and eager attention may run instead
(`ACCESS_REPORT.md` R1). Left exactly as the reference has it.

## Test-time training

| Setting | Value |
| --- | --- |
| Adapter | LoRA r=256, alpha=32, dropout 0.0, bias none, rslora |
| Target modules | q,k,v,o,gate,up,down + `embed_tokens` + `lm_head` |
| Augmentation | `augment(n=16, shfl_keys=True, seed=1)` → 8 orientations x 16 colour permutations = **128 samples** |
| Truncation | `cut_to_len(name="text", max_len=8192)` — drops demonstration pairs when over budget |
| Epochs / batch | 1 epoch, per-device batch 1, grad accumulation 1 → ~128 steps |
| Optimizer | adamw_8bit, lr 5e-5, cosine, warmup_ratio 0.1, max_grad_norm 1.0 |
| Precision | `fp16=False, bf16=False`, `half_precision_backend="cpu_amp"` |
| Grad checkpointing | off |
| Reset | LoRA restored to pretrained state before every task |

## Candidate generation

| Setting | Value |
| --- | --- |
| Eval augmentation | `augment(n=2, seed=2)` → 16 views per test input |
| Batching | 8 batches of 4, fixed offsets `[0,4]`, `[2,6]`, `[8,12]`, `[10,14]` |
| Search | `turbo_dfs`, depth-first over the token tree, shared KV cache |
| Cutoff | `max_score = -np.log(0.2)` = 1.6094 nats |
| Max new tokens | `formatter.max_new_tokens()` (30x30 grid + 1) |
| Inversion | `invert_mod(array, subkey, inv_perm=True)` |

## Candidate scoring and ranking

- Rescoring: 8 fixed augmentations per **unique** grid, memoised on
  `(base_key, grid)`; `aug_dataset.augment(seed=hash(bk) % 1024**2)`.
- Selection: `score_kgmon` = `len(guesses) - mean(mean(score_aug))`, i.e.
  generation vote count minus mean augmented NLL. This is `score_agg` from
  `nvarc_2025.pdf` §3.4.
- `score_full_probmul_3` (ARChitects 2024 product-of-experts) is present and
  unused.
- Top 2 become `attempt_1` / `attempt_2`.

**`hash(bk)` is not stable across processes unless `PYTHONHASHSEED` is fixed.**
The notebook does not fix it. Recorded as a reproducibility caveat, not changed.

## Seeds

| Seed | Value |
| --- | --- |
| TTT augmentation | 1 |
| Eval augmentation | 2 |
| LoRA init / trainer | 42 |
| Rescoring augmentation | `hash(base_key) % 1024**2` (process-dependent) |

## Runtime guards

| Guard | Value |
| --- | --- |
| Global | `time.time() + 12*3600 - 1200` = 11 h 40 min |
| Per task | abandon inference after 1200 s |
| Per DFS batch | abandon after 540 s |

## Parallelism

`mp.spawn(local_worker, nprocs=2)`; each child sets
`CUDA_VISIBLE_DEVICES=str(rank)` before importing torch CUDA and pulls task ids
from a shared `mp.Manager().Queue()`. Tasks are queued in `sorted(data.keys())`
order. Dynamic load balancing.

## Submission behaviour

`get_submission` pre-fills every task and test index with
`{"attempt_1": [[0]], "attempt_2": [[0]]}`, then `fill_submission` overwrites
what was decoded. A timed-out task still emits a valid entry, so the submission
is always well-formed.

## Split selection

```python
rerun_mode = os.getenv("KAGGLE_IS_COMPETITION_RERUN")
test_path = ".../arc-agi_test_challenges.json" if rerun_mode
            else ".../arc-agi_evaluation_challenges.json"
```

**RUN-001 runs interactively, so `rerun_mode` is unset and the notebook scores
the 120-task public evaluation split** — which is exactly the split the
checkpoint was trained on (`docs/systems/NVARC.md` §9). Any accuracy it prints
is contaminated and is recorded as such.
