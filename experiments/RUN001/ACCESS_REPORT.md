# RUN-001 — access and environment verification

All findings below were produced by pushing and executing private probe kernels
under the account `redlotusthepotus` on 2026-07-25. Nothing was downloaded
locally; the 6.77 GiB checkpoint was inspected only where it is mounted, inside
Kaggle.

Probe kernels (both private):

- `redlotusthepotus/run001-access-probe` — v1, CPU, no attachments.
- `redlotusthepotus/run001-asset-probe` — v1-v4, GPU, full attachments.

## Evidence table

| # | Question | Finding | Status |
| --- | --- | --- | --- |
| 1 | Source model accessible | Yes. All 10 files present and byte-for-byte equal to the API listing (`model-00001` 4,996,836,472 B; `model-00002` 2,270,397,024 B; `vocab.json` 94 B). | **CONFIRMED** |
| 2 | Model mount path | `/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1`. **The notebook's hardcoded `/kaggle/input/qwen3_4b_grids15_sft139/transformers/bfloat16/1` does not exist.** | **CONFIRMED — EXECUTION-BLOCKING as written** |
| 3 | Dependency notebook accessible | Yes. Mounted at `/kaggle/usr/lib/notebooks/sorokin/pip_install_unsloth_flash_patch` and present on `sys.path` at position 5. | **CONFIRMED** |
| 4 | Checkpoint licence | Not exposed by the Kaggle API for model instances. Its training data (`sorokin/nvarc-*`) is licensed `unknown`. | **UNRESOLVED — PUBLICATION-BLOCKING ONLY** |
| 5 | Kernel creation permission | `kernels push` succeeded, "Kernel version 1 successfully pushed". | **CONFIRMED** |
| 6 | Kernel execution permission | Probe reached `KernelWorkerStatus.COMPLETE`. | **CONFIRMED** |
| 7 | Kernel version creation | Four versions pushed to the same kernel without incident. | **CONFIRMED** |
| 8 | Accelerator settings | `enable_gpu: true` alone yields **1x Tesla P100-PCIE-16GB, sm60**. Adding `"machine_shape": "NvidiaTeslaT4"` yields **2x Tesla T4, 15360 MiB each, sm75**. The CLI honours `machine_shape` on push. | **CONFIRMED** |
| 9 | Two-T4 availability | Yes, with `machine_shape` set. `torch.cuda.device_count() == 2`. | **CONFIRMED** |
| 10 | Competition source attachment | `/kaggle/input/competitions/arc-prize-2026-arc-agi-2` with all six JSON files at the expected sizes. | **CONFIRMED** |
| 11 | Internet-disabled execution | `enable_internet: false` accepted; kernel runs and completes. | **CONFIRMED** |
| 12 | Persona effect on execution | **None observed.** Creation, versioning and execution all succeed. | **CONFIRMED not execution-blocking** |
| 13 | Persona effect on submission | Not tested — RUN-001 does not auto-submit by instruction. | **UNRESOLVED — SUBMISSION-BLOCKING RISK ONLY** |

## Environment, pinned image

Pinning `docker_image` to the reference notebook's digest
(`gcr.io/kaggle-private-byod/python@sha256:320043e14c68293f1c946585b9257123385205a58af4b94b17d31868cae4e868`)
is **required**, not cosmetic.

| Component | Unpinned (default image) | Pinned (reference image) |
| --- | --- | --- |
| Python | 3.12 | **3.11.13** (matches the notebook's `language_info`) |
| GPU (with `machine_shape`) | — | 2x Tesla T4, sm75 |
| `import torch` | **ImportError: Failed to load PyTorch C extensions** | **torch 2.8.0+cu128, cuda True, 2 devices** |

The unpinned failure is the dependency kernel's `--target` installs, built as
`cp311` wheels, shadowing the system `torch` under a `cp312` interpreter. On the
pinned image the ABI matches and the import chain is clean.

Verified inside the pinned image:

| Library | Result |
| --- | --- |
| `torch` | 2.8.0+cu128, CUDA available, 2 devices |
| `xformers` | 0.0.32.post2 — `memory_efficient_attention` **executes successfully on sm75** |
| `bitsandbytes` | 0.48.2 (4-bit NF4 viable on sm75) |
| `unsloth` | 2025.9.7, imports cleanly |
| `/kaggle/working` free | **19.5 GB** |
| `/tmp` free | 1026.7 GB |
| `KAGGLE_IS_COMPETITION_RERUN` | unset in interactive runs, as the notebook expects |

## Two risks recorded, neither fixed (no solver changes permitted)

**R1 — the flash-attention monkeypatch may be vestigial.**
`hasattr(unsloth.models.qwen3, "flash_attn_func")` is **False** in unsloth
2025.9.7. The notebook's

```python
qwen3_module.flash_attn_func = patched_attention
```

therefore creates a new attribute rather than replacing an existing one, so it
may never be called. Combined with `attn_implementation="eager"`, attention very
likely runs eager. This does not stop the run and is not ours to change, but it
means the xformers substitution documented in
`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §2 may not be load-bearing. Recorded for
the record and for later measurement.

**R2 — 19.5 GB of writable space.** The candidate archive must stream and stay
compact. Design consequence: gzip, incremental append, no in-memory
accumulation.

## Conclusion

**No execution blocker remains except the model path (#2), which is an
environment drift, not a solver property.** Everything else needed to run
RUN-001 is confirmed working.
