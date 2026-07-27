# EXP002-D — CORPUS_RECONCILIATION

Built by `src/analysis/exp002d/corpus.py`, reading only ACQ-001's immutable
archives (`artifacts/ACQ001/shard_{a,b}_output/.../archive/candidates.{A,B}.jsonl.gz`).
No ACQ-001 artifact is modified.

## Canonical candidate table

One row per unique `(task_id, test_index, grid_sha1)`, built by grouping the
raw archive's `candidate` records (which include duplicate discoveries of
the same grid). Each row carries: `shard`, `family` (`size_relation`, from
`artifacts/data_audit/task_statistics.csv`, which already covers all 160
corpus tasks), `multiplicity` (duplicate count), `beam_score_{best,mean,min}`
(duplicate occurrences of the same grid can carry different `beam_score`
values from different beam-search paths — all three are kept rather than
collapsed), `first_discovery_order` (earliest position in the archive's own
file order for that `(task_id, test_index)`, which is exactly CompressARC's
beam-search discovery order — confirmed from `acquire_shard.py::_ingest_one_task`'s
own iteration order: `for test_index in range(n_test): for candidate in
result["candidates"]:`, so archive file order **is** discovery order,
no separate per-task JSON re-parse needed), `native_selected`/`native_rank`
(joined from the archive's own `selection` records), and `is_correct`
(joined from `arc-agi_training_solutions.json` **last**, after grouping and
discovery-order computation are already complete and independent of ground
truth).

## Test-index summary

One row per `(task_id, test_index)`: `n_unique_candidates`,
`n_candidates_total`, `n_correct_unique`, `oracle_hit`, `native_top1_hit`,
`native_top2_hit`, `family`, `shard`.

## Verification against `experiments/ACQ001/FINAL_CORPUS_REPORT.md`

| Check | ACQ-001 report | EXP002-D reconstruction | Match |
| --- | --- | --- | --- |
| Tasks | 160 | 160 | Y |
| Test-indices | 171 | 171 | Y |
| Raw candidate records | 73,147 | 73,147 | Y |
| Unique candidates | 70,680 | 70,680 | Y |
| Unique-candidate fraction | 96.63% | 96.63% | Y |
| Full-candidate-set oracle coverage | 24.56% | 24.56% | Y |
| Native top-2 accuracy | 13.45% | 13.45% | Y |

**Exact agreement on every figure.** No malformed grids were encountered
(every `grid` field parsed as a rectangular list of small integers by
construction of `read_records`/`grid_digest`), no candidate is missing
(both shards' full task lists are present, `n_unique_candidates` sums to
70,680 across all 171 test-indices), no duplicate correctness labels exist
(`is_correct` is a deterministic function of `(task_id, test_index,
grid_sha1)`, computed once per unique group), and no cross-task
contamination is possible (`is_correct` looks up
`solutions[task_id][test_index]`, keyed by the row's own `task_id`, never
a different task's).

## Artifacts

- `artifacts/EXP002D/canonical_candidate_index.parquet` (70,680 rows)
- `artifacts/EXP002D/test_index_summary.parquet` (171 rows)
