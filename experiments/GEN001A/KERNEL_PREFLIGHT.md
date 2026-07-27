# GEN001-A — KERNEL_PREFLIGHT

The built (not launched) Kaggle 2xT4 pilot kernel package.
`kaggle/gen001_nvarc_pilot/`. Checksums: `ARTIFACT_MANIFEST.tsv`.

## What was built

`src/gen001/build_pilot_notebook.py` patches RUN-001's already-frozen,
already-validated instrumented notebook
(`kaggle/run001_nvarc_frozen/run001_instrumented.ipynb`) with 8 anchored
patches, each asserted to match exactly once:

| # | Cell | Change |
| --- | --- | --- |
| 1 | 0 | Pilot budget (5h cap vs. RUN-001's 11h40m) and pinned provenance (`GEN001A_CHECKPOINT_ID`, `GEN001A_CONFIG_HASH`, `GEN001A_CONTAMINATION_STATUS`, `GEN001A_PILOT_TASK_IDS`) |
| 2 | 5 | Worker's own dataset load switched to the ACQ-001 training-split source (was hardcoded to the evaluation split) |
| 3 | 5 | Every candidate record stamped with `checkpoint_id`, `config_hash`, `contamination_status` |
| 4 | 6 | Task queue restricted to exactly the 24 frozen pilot task IDs, training-split source, resume-skip against `checkpoint_state.json` |
| 5 | 8 | Aggregation cell's data source switched to training split; solutions-loading call removed entirely |
| 6 | 8 | Interactive self-scoring block (`validate_submission` against ground truth) removed entirely |
| 7 | 8 | `checkpoint_state.json` and `completed_indices.json` written from the merged task summary |
| 8 | 8 | Selection records stamped with the same three provenance fields as candidates |

RUN-001's own two sanctioned changes (debug-filter removal, behaviour-neutral
candidate archiving) are inherited unchanged — this pilot adds provenance
and corpus-restriction patches on top, not a re-derivation of archiving
logic that is already tested.

## Required outputs, verified present in the build's output contract

| Required output | Where it comes from |
| --- | --- |
| `candidates.jsonl.gz` | aggregation cell concatenates per-worker `candidates.w*.jsonl.gz` (inherited from RUN-001) |
| `task_summary.csv` | aggregation cell concatenates per-worker summaries (inherited) |
| `runtime_summary.json` | aggregation cell (inherited) |
| `errors.jsonl` | aggregation cell concatenates per-worker error logs (inherited) |
| `run_manifest.json` | written by `CandidateArchive.write_manifest` at worker startup (inherited) |
| `completed_indices.json` | **new**, patch 7 |
| `checkpoint_state.json` | **new**, patch 7 |

## Runtime and interruption guards

- Global: `global_end_time = time.time() + 18000` (5h), cell 0.
- Per-task: unchanged from RUN-001, 1200s (`hit_time_guard=bool(spend_time > 1200)`).
- Per-DFS-batch: unchanged from RUN-001, 540s (inherited from the reference
  notebook's `turbo_dfs`, not itself patched).
- Resume: cell 6's queue construction skips any task ID already present in
  `checkpoint_state.json`'s `completed_task_ids`, so a re-launch of the same
  kernel after an interruption only processes what remains.

## Static validation performed

`python3 -m src.gen001.validate_pilot_notebook`:

```
[PASS] check_parses
[PASS] check_no_evaluation_split_loaded
[PASS] check_no_solutions_file_loaded
[PASS] check_training_split_used
[PASS] check_provenance_fields_stamped
All checks passed.
```

These are the same category of check `src/run001/validate_notebook.py`
already applies to RUN-001's notebook (frozen-solver diff, no-ground-truth,
metadata correctness), applied to this pilot's specific new risks: wrong
data split, residual self-scoring, missing provenance stamps.

## What was not done, deliberately

- `kaggle kernels push` was **not called**. No kernel exists on Kaggle under
  `redlotusthepotus/gen001a-nvarc-pilot` as a result of this phase.
- No GPU quota was consumed.
- No checkpoint was downloaded.

## Exact future launch command (not run by this phase)

```
~/arc-agi-2-2026/.tools/kaggle-venv/bin/kaggle kernels push -p kaggle/gen001_nvarc_pilot
```

Gated by `PILOT_PROTOCOL.md`'s launch condition and `QUOTA_PROJECTION.md`'s
minimum-remaining-quota check (recommended: >=8h remaining), both of which
require a human to manually confirm live Kaggle quota before running this
command — this phase does not and must not run it.
