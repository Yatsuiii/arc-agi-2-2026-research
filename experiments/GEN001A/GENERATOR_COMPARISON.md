# GEN001-A — GENERATOR_COMPARISON

Phase 4: defines the metrics a future NVARC pilot's output will be scored
by, before that output exists. Frozen here so no metric is chosen after
seeing results.

## The central question, restated

Not "does NVARC alone beat CompressARC's selection" — that is contaminated
(`CONTAMINATION_AUDIT.md`) and orthogonal to what EXP002-D found. The
question is whether NVARC's candidate set is complementary to
CompressARC's: does it contain correct grids on test-indices where
CompressARC's candidate set contains none.

## Sets

- **C** = test-indices with a correct candidate in the CompressARC archive
  (`artifacts/ACQ001/shard_{a,b}_output/.../candidates.{A,B}.jsonl.gz`).
  |C| = 42/171 (24.56%, `experiments/EXP002D/RESULTS.md`).
- **N** = test-indices with a correct candidate in the NVARC pilot's
  archive (not yet measured — this phase defines the metric, does not
  compute it).

## Primary metrics (set-complementarity, the actual question)

| Metric | Definition | Why it matters |
| --- | --- | --- |
| NVARC candidate oracle | \|N\| / n_pilot_indices | NVARC's own generation coverage, contamination-labelled |
| CompressARC candidate oracle (pilot subset) | \|C\| / n_pilot_indices | restated on the same 24-index denominator for a fair comparison |
| Union oracle | \|C ∪ N\| / n_pilot_indices | the number that matters — does adding NVARC move the ceiling |
| Incremental NVARC coverage | \|N \ C\| | test-indices only NVARC solves — the complementarity signal |
| Overlap | \|N ∩ C\| | redundant coverage |
| CompressARC-only coverage | \|C \ N\| | what NVARC would need to not regress |
| Jaccard overlap | \|N ∩ C\| / \|N ∪ C\| | one-number summary of redundancy |

## Secondary metrics (diagnostic, not decision-driving)

- Candidate-grid overlap (fraction of NVARC's unique grids that are
  byte-identical, by `grid_sha1`, to a CompressARC candidate on the same
  test-index).
- Candidate-family diversity (structural distance between NVARC's and
  CompressARC's candidate populations — reuses `src/harness/features/structural.py`'s
  pairwise-distance construction from EXP002-D, applied across generators
  rather than within one).
- Task-family breakdown (`size_relation`, `artifacts/data_audit/task_statistics.csv`) of
  where incremental coverage lands.
- Cost per incremental solved test-index (GPU-seconds spent /
  \|N \ C\|, from the pilot's own `runtime_summary.json`).

## Explicitly secondary: selection accuracy

NVARC's own native top-1/top-2 selection accuracy, and any union-corpus
selection baseline, are recorded (they come for free from the archive) but
are **not** the metric that determines whether the pilot was worthwhile.
A generator whose candidate set is complementary but whose own selector
never picks the complementary candidate is still a net positive for this
project, because ACQ-001's harness already separates generation from
selection (`paper/FAILURE_TAXONOMY.md`) — a future selection pass over the
union candidate set is a distinct, later question, not conflated with this
one. Native selection quality must not be allowed to hide generator
complementarity, which is why it is reported only as a secondary,
labelled-separately number.

## No second verifier fit in this pass

Per the acceptance message's Phase 11 instruction, the future analysis
(`src/gen001/analyse_union.py`) computes oracle-union set arithmetic only.
No model is trained on the union candidate set in this phase or the pilot
analysis that follows it.
