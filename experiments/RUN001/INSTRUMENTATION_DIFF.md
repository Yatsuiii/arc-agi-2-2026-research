# RUN-001 — exact notebook diff

Reference `kaggle/run001_nvarc_frozen/reference_source.ipynb`
sha256 `452dbb1fc050bad9cbba38a6802231bff91cc2970899eabb8c74e5f34f322a6c`
(byte-identical to the live Kaggle notebook, verified by `kernels pull`).

Instrumented `kaggle/run001_nvarc_frozen/run001_instrumented.ipynb`
sha256 `70a1f5898505cd692aaeccea6f646a7b67cb5933db4646703b360b8fdde6028d`

The instrumented notebook is **generated, never hand-edited**
(`python -m src.run001.build_notebook`). Every patch declares an anchor that must
match exactly once in its cell; a mismatch aborts the build. That is how the
"account for every changed line" requirement is enforced mechanically rather
than by inspection.

## Line accounting

| Instrumented cell | Reference cell | Lines added | Lines removed | Purpose |
| --- | --- | --- | --- | --- |
| 2 | — (new) | 222 | 0 | `%%writefile arc_archive.py` |
| 5 | 4 | 88 | 1 | model-path resolver + archive calls in `arc_solver.py` |
| 6 | 5 | 0 | 3 | remove the debug filter in `starter.py` |
| 8 | 7 | 56 | 0 | selection records + artifact collection |
| **total** | | **366** | **4** | |

The single removed line in cell 5 is the hardcoded model path, replaced by
`model_name=RUN001_MODEL_DIR`. The three removed lines in cell 6 are the debug
filter. **No other reference line is deleted or altered anywhere.**

## Change 1 (sanctioned) — remove the four-task debug filter

`starter.py`, 3 lines removed:

```python
        if not rerun_mode:
            if key not in ["0934a4d8", "36a08778", "981571dc", "aa4ec2a5"]:
                continue
```

Every task in the loaded challenge file is now queued. In rerun mode the filter
was already bypassed, so this changes interactive behaviour only — which is
exactly the mode RUN-001 runs in.

## Change 2 (sanctioned) — behaviour-neutral candidate archiving

Four insertion points, all **additive**; no existing statement is modified,
reordered or wrapped.

1. **After `logging.disable(logging.WARNING)`** — import `CandidateArchive`,
   `grid_digest`, `to_grid`.
2. **After `os.makedirs(dir_outputs, exist_ok=True)`** — construct the
   per-worker archive and install an `excepthook` that records the exception and
   then delegates to the previous hook, so a crash still propagates exactly as
   before.
3. **After the solver's own `decoded_result.append({...})`** — record the
   candidate. Placed after the append so the solver's list is already final.
   Wrapped in `try/except: pass` so instrumentation can never take down a run.
4. **After `print(f"[Rank {rank}] finished {key} ...")`** — flush that task's
   buffer and write one summary row.
5. **After the decoder writes `submission.json`** — write ranking/selection
   records and collect shards into the canonical artifact names.

Neutrality properties, each enforced by a test or a static check:

| Property | Enforced by |
| --- | --- |
| No RNG consumed | `validate_notebook.check_no_rng_in_archive`, `test_archive_never_touches_global_rng` |
| Identical outputs, scores, ordering, RNG state | `test_logging_is_behaviour_neutral` (25 mock tasks) |
| No argument mutated | archive only reads and serialises |
| Bounded memory | at most one task buffered; `flush_task` clears |
| Crash-safe | one gzip member per flush; `test_flush_per_task_creates_readable_prefix` |
| No hidden answers archived | `check_no_ground_truth_archived`, `test_no_ground_truth_field_names_leak` |
| Embedded module matches source | `check_archive_module_matches` |

## Change 3 — NOT SANCTIONED, and why it was still necessary

**The model mount path.** This exceeds the "exactly two changes" mandate and is
flagged rather than buried.

The reference notebook hardcodes:

```python
model_name="/kaggle/input/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
```

Probe kernel `run001-asset-probe` v3 established that this path **does not
exist**. The checkpoint mounts at:

```
/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1
```

Kaggle's model mount layout drifted after the notebook was written. Without a
fix the notebook raises before loading any weights and there is no run at all.

The replacement tries the reference path **first**:

```python
RUN001_MODEL_CANDIDATES = [
    "/kaggle/input/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
    "/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
]
```

so if Kaggle ever restores the old layout, behaviour is byte-identical to the
reference. Either way it resolves to the same checkpoint — same 10 files, same
7,267,233,496 bytes of weights.

**It is an environment fix, not a solver change.** It touches no property on the
prohibited list: checkpoint identity, tokenizer, quantization, training, TTT,
augmentations, DFS, decoding, generation, scoring, aggregation, ranking, output,
seeds, batching, task order and time allocation are all untouched, and
`check_frozen_solver` verifies all twenty of those settings survive verbatim.

## Explicitly unchanged

Verified line-present in the instrumented notebook by
`validate_notebook.check_frozen_solver`:

```
r=256,                                    lora_alpha=32,
use_rslora=True,                          lr_scheduler_type="cosine",
learning_rate=5e-5,                       optim="adamw_8bit",
num_train_epochs=1,                       max_seq_length = 8192
max_score = -np.log(0.2)                  augment(n=16, shfl_keys=True, seed=1)
augment(n=2, seed=2)                      seed=42,
load_in_4bit=True,                        attn_implementation="eager",
mp.spawn(..., nprocs=2)                   global_end_time = time.time() + 12*3600 - 1200
if spend_time > 1200 ...                  while time.time() - start_time < 540 ...
score_kgmon                               n_guesses=2
```
