# FIGURE_REGISTRY

Every figure and table the paper may contain, the script that generates it, and
the artifact it reads. A figure with no generating script does not go in the
paper.

## Rules

1. One script, one figure, deterministic given its input artifact.
2. Scripts read from `artifacts/`, write to `paper/artifacts/`. No figure is
   hand-drawn or hand-edited.
3. Every figure caption states the split and the evaluation snapshot.

## Registry

| ID | Title | Generator | Input artifact | Supports | Status |
| --- | --- | --- | --- | --- | --- |
| F1 | ARC-AGI-2 task statistics: grid sizes, demo counts, colour usage, input→output size relation | `src/data_audit/task_statistics.py` | `competition_2026/extracted/*.json` | §5.1, universality breakdown | **AVAILABLE** |
| F2 | Train vs eval distribution shift across the same statistics | same | same | §5.1 | **AVAILABLE** |
| T1 | Dataset and split table with contamination status per split | `src/data_audit/schema_report.py` | same | §5.2 | **AVAILABLE** |
| T2 | Cross-system comparison matrix | hand-assembled from `docs/SYSTEM_COMPARISON.md`, cited not generated | audit docs | §3 | AVAILABLE (prose table) |
| F3 | Solve-set overlap between solvers (upset or Venn) | `[BLOCKED]` EXP001 | per-task solve vectors | C1 | BLOCKED |
| F4 | Oracle@k vs realised accuracy@2 as a function of k | `src/analysis/headroom.py` (ARC-AGI-1, done); EXP001-B for ARC-AGI-2 | `artifacts/exp001/headroom.json`; RUN-001 `candidates.jsonl.gz` | C2 | **ARC-AGI-1 AVAILABLE**, ARC-AGI-2 pending RUN-001 |
| F5 | Compute-vs-accuracy curve, uniform vs routed allocation | `[BLOCKED]` | per-task time and outcome | C3 | BLOCKED |
| F6 | Failure-category counts per solver | `[BLOCKED]` | labelled predictions | §8 | BLOCKED |
| F7 | Selection-algorithm ablation | `[BLOCKED]` AB-S1 | RUN-001 `candidates.jsonl.gz` (`beam_score` + `score_aug[8]` per candidate) | §7 | **UNBLOCKED once RUN-001 lands** |

## Note on F1/F2/T1

These three are producible today, CPU-only, from data already on disk. They are
the only figures this project can currently generate, and they are generated in
Phase 3. Everything else is honestly marked blocked.
