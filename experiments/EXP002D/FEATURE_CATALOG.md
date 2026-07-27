# EXP002-D — FEATURE_CATALOG

Built by `src/analysis/exp002d/features.py`. 34-column
`artifacts/EXP002D/candidate_features.parquet`, one row per unique
`(task_id, test_index, grid_sha1)` (70,680 rows). Every feature name below
is classified in `features.py`'s `SCORE_DERIVED_FEATURES`/
`INDEPENDENT_FEATURES` frozensets, checked by `assert_score_independent`
before it can reach a V2/V3 model — no unclassified column exists (verified
programmatically after Phase 4 ran).

## F0/F1 — native, score-derived

Identical in this corpus (see `PLAN.md`'s "what is different" section —
CompressARC's archive carries no separate aggregation formula to
reconstruct).

| Feature | Definition | Candidate/task | Score-dependent | Leakage risk | Cost |
| --- | --- | --- | --- | --- | --- |
| `beam_score_best` | max `accumulated_score` across duplicate discoveries of this grid | candidate | yes | none (ground truth not read) | O(1) |
| `beam_score_mean` | mean `accumulated_score` across duplicates | candidate | yes | none | O(1) |
| `beam_score_min` | min `accumulated_score` across duplicates | candidate | yes | none | O(1) |
| `beam_score_percentile` | rank of `beam_score_best` within the test-index, as a percentile | candidate | yes | none | O(k log k) |
| `native_rank_or_zero` | CompressARC's own selection rank (1, 2, or 0 if not selected) | candidate | yes | none | O(1) |

## F2+F3 — score-independent grid + train-example consistency

Computed by `src/harness/features/structural.py::structural_features`
(candidate grid vs. test input vs. demonstration pairs only — never reads
`beam_score`, archive order, or ground truth).

| Feature | Definition | Candidate/task | Score-dependent | Leakage risk | Cost |
| --- | --- | --- | --- | --- | --- |
| `output_size_matches_expected` | candidate shape == shape inferred from demo `size_relation` | candidate | no | none | O(cells) |
| `n_colours_introduced_by_candidate` | colours in candidate not in test input | candidate | no | none | O(cells) |
| `n_colours_removed_by_candidate` | test-input colours absent from candidate | candidate | no | none | O(cells) |
| `introduced_colours_seen_in_demos` | candidate's new colours are a subset of colours demos ever introduce | candidate | no | none | O(cells) |
| `removed_colours_seen_in_demos` | analogous for removed colours | candidate | no | none | O(cells) |
| `symmetry_agreement_with_demo_outputs` | fraction of {h,v,rot180,diag} symmetries matching demo-output pattern | candidate | no | none | O(cells) |
| `object_count` | 4-connected component count | candidate | no | none | O(cells) |
| `object_count_consistent_with_demo_pattern` | matches the input->output object-count delta demos show, when that delta is consistent | candidate | no | none | O(cells) |
| `tiling_pattern_consistent_with_demos` | periodic-tiling flag matches demo-output pattern | candidate | no | none | O(cells^1.5) |
| `is_degenerate_input_copy` | candidate == test input | candidate | no | none | O(cells) |
| `is_degenerate_constant_fill` | candidate uses <=1 colour | candidate | no | none | O(cells) |
| `is_valid_grid` | rectangular, colours 0-9, dims <=30 | candidate | no | none | O(cells) |
| `grid_complexity` | connected components / area | candidate | no | none | O(cells) |
| `contradiction_count` | how many of the above checks resolved and disagreed with the demo pattern | candidate | no | none | O(1) given the above |

## F4 — candidate-set relational (within one test-index's own set only)

Preregistered deviation (`LEAKAGE_AUDIT.md` §3): classified `SCORE_DERIVED`
for this experiment, not `INDEPENDENT` — revisit frequency in a beam
search is itself a search-behaviour signal, not a pure grid property.
Available to hybrid tracks (V4/V5/V6) only.

| Feature | Definition | Candidate/task | Score-dependent | Leakage risk | Cost |
| --- | --- | --- | --- | --- | --- |
| `consensus_frequency` | duplicate multiplicity / total candidates in the test-index | candidate | yes (search-behaviour) | none | O(1) |
| `distance_from_modal` | pixel-mismatch fraction vs. the highest-multiplicity candidate (same-shape only; 1.0 if shapes differ) | candidate | yes | none | O(k) amortised, numpy-vectorised per shape bucket |
| `mean_distance_from_set` | mean pixel-mismatch fraction vs. every other candidate in the set | candidate | yes | none | O(k) amortised, numpy-vectorised |
| `discovery_order_frac` | earliest beam-search discovery position, normalised 0-1 by the test-index's max position | candidate | yes | none | O(1) |

Not computed (do not exist in this corpus, see `PLAN.md`): rank agreement
across augmentations, provenance diversity, phase diversity, stability
under inverse augmentation, number of independent generation paths — this
corpus is one CompressARC process per task, no augmentation ensemble, no
multi-seed diversity.

## F5 — provenance (thin)

| Feature | Definition | Candidate/task | Score-dependent | Leakage risk | Cost |
| --- | --- | --- | --- | --- | --- |
| `task_steps_run` | task-level solve wall-clock (proxy; `solve_seconds` from `task_summary.{A,B}.csv`, `steps_run` itself was not carried into the flushed archive) | task-constant | no | none | O(1), precomputed |
| `task_elapsed_s` | same value as `task_steps_run` in this corpus (both sourced from `solve_seconds`) | task-constant | no | none | O(1) |
| `task_hit_time_guard` | 1.0 for every task in this corpus (100% of tasks hit the 2400s guard, per `experiments/ACQ001/SHARD_A_RESULTS.md`/`SHARD_B_RESULTS.md`) | task-constant | no | none, but zero-variance | O(1) |

`task_hit_time_guard` has **zero variance across the entire corpus**
(every ACQ-001 task hit the time guard) — retained for completeness and
audit transparency, not because it carries any signal; any model
including it will assign it zero weight or the fitting procedure will
warn/ignore it.

## F6 — hybrid

Union of F0/F1 and F2-F5. Used only by V4/V5/V6.

## Positive prevalence (diagnostic, not a leakage check)

42 of 70,680 unique candidates are correct (0.059%) — exactly one
per test-index where the oracle indicator is true (42/171 = 24.56%,
matching `CORPUS_RECONCILIATION.md`). Extreme class imbalance; addressed
in Phase 6 (`RESULTS.md`'s class-imbalance section).
