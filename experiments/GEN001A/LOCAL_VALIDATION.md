# GEN001-A — LOCAL_VALIDATION

Every stage of the pilot pipeline that does not require GPU inference,
exercised for real, against real data, on this machine. Where GPU
inference would be required, `MockGenerator` (`src/gen001/nvarc_adapter.py`)
stands in — schema-valid output, unmistakably labelled
(`checkpoint_id="MOCK"`), never confused with a real result.

## What was run

```
python3 -m pytest tests/gen001/ -q       # 20 passed
python3 -m pytest -q                     # 256 passed (full repo suite)
python3 -m src.gen001.build_pilot_manifest
python3 -m src.gen001.pilot_runner       # full 24-index mock dry run
```

## Stage-by-stage result

| Stage | Exercised how | Result |
| --- | --- | --- |
| Imports | full `src.gen001` package import via pytest collection | clean, no missing dependency (stdlib + pandas only) |
| Data loading | `pilot_runner.load_manifest`, real `arc-agi_training_challenges.json` | 24/24 rows load, all 24 task IDs resolve |
| Task serialization | `_load_task_input` builds `TaskInput` from real train/test pairs | no ground-truth field constructible on `TaskInput` (structural guarantee, `test_generator_never_receives_ground_truth`) |
| Configuration construction | `FROZEN_PILOT_CONFIG`, `config_hash()` | stable across calls, changes when any field changes (`test_config_hash_stable_and_sensitive_to_changes`) |
| Candidate generation (mocked) | `MockGenerator.generate` | deterministic, schema-valid grids |
| Output parsing / candidate validation | `export_candidate_record` | rejects empty/malformed grids (`test_invalid_grid_rejected`) |
| Duplicate handling | `deduplicate_candidates` | collapses exact-duplicate grids, tracks `multiplicity` |
| Archive writing | `CandidateArchive` (reused verbatim from `src/run001/archive.py`) | full 24-index run: `candidates.pilot.jsonl.gz`, `run_manifest.pilot.json`, `runtime_summary.pilot.json`, `task_summary.pilot.csv`, `completed_indices.json` all written and readable |
| Resume logic | second `run_pilot` call against a completed run_dir | `n_run_this_call == 0`, `n_completed == 24` — no re-generation (`test_resume_skips_completed_indices`) |
| Global runtime guard | `run_pilot(..., global_time_cap_s=0)` | stops immediately, `hit_global_cap == True`, leaves a readable (possibly empty) prefix (`test_global_time_cap_stops_early`, `test_survives_interruption_leaves_readable_prefix`) |
| Union-metric computation | `compute_union_metrics` against synthetic fixtures with known overlap/incremental structure | exact expected values (`tests/gen001/test_analyse_union.py`) |
| Contamination-label propagation | every record from the mock run | 100% carry `contamination_status="SCIENTIFICALLY_CONTAMINATED"` (checked directly on the real archive output, not just the unit test) |
| Checkpoint/config hashing | `config_hash()` | 16-char stable hex digest, `d616af6818bc4d59` for `FROZEN_PILOT_CONFIG` as of this commit |
| No ground-truth access during generation | structural: `TaskInput` has no output/solution field; `Generator.generate` signature takes only `TaskInput` and `PilotConfig` | enforced by type shape, not a runtime check that could be bypassed |

## What was not, and cannot be, validated locally

- Real NVARC inference (checkpoint loading, TTT, DFS decoding, augmented
  rescoring) — requires the actual checkpoint and a GPU. Not attempted, per
  the phase's CPU-only constraint.
- Kaggle-specific runtime behaviour (rank-serialised startup, xformers
  monkeypatch, `mp.spawn` worker split) — only checkable on the Kaggle
  platform itself.
- Kernel packaging end-to-end (`kaggle kernels push` dry run) — not run;
  Phase 9 builds the package but does not push it.

## Test count

20 new tests under `tests/gen001/` (4 manifest, 7 adapter, 6 pilot-runner,
3 union-analysis), full repository suite **256 passed** (236 pre-existing
+ 20 new), 0 failures, 0 skips.
