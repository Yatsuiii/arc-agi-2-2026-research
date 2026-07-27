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
| F4 | Oracle@k vs realised accuracy@2 as a function of k | `src/analysis/headroom.py` (ARC-AGI-1, done); EXP001-B for ARC-AGI-2 | `artifacts/exp001/headroom.json`; RUN-001 `candidates.jsonl.gz` | C2 | **ARC-AGI-1 AVAILABLE**; ARC-AGI-2 preview available as rank-1 accuracy (`artifacts/EXP002/figures/f1_accuracy_comparison.png`), full k-curve still pending EXP001-B |
| F5 | Compute-vs-accuracy curve, uniform vs routed allocation | `[BLOCKED]` | per-task time and outcome | C3 | BLOCKED — needs EXP003/EXP004, not yet run |
| F6 | Failure-category counts per solver | `[BLOCKED]` | labelled predictions | §8 | **PARTIALLY AVAILABLE** for RUN-001/NVARC only: branch G/S split reported in `experiments/EXP002/ERROR_ANALYSIS.md`; full G1-G6/S1-S4 automatic labeller not yet built |
| F7 | Selection-algorithm ablation | `src/analysis/exp002_figures.py` (`f1`, `f2`, `f6`) | `artifacts/EXP002/exp002_report.json` | §7 | **AVAILABLE** — B0/B1/B2/B5 comparison and per-feature AUC ablation, `experiments/EXP002/RESULTS.md` |
| F8 | Verifier reliability diagram, correct-candidate rank distribution, accuracy by task family, margin vs. correctness | `src/analysis/exp002_figures.py` (`f3`, `f4`, `f5`, `f7`) | `artifacts/EXP002/exp002_report.json` | C2, thesis T2 | **AVAILABLE** |
| F9 | V0-V3 accuracy with bootstrap CIs, selective accuracy vs. coverage | `src/analysis/exp002b_figures.py` (`g1`, `g2`) | `artifacts/EXP002B/exp002b_report.json` | C2 | **AVAILABLE** — the CI-overlap figure is the primary visual evidence for EXP002-B's "acquisition-bound, not rejected" verdict |
| F10 | Score-independent-only feature ablation | `src/analysis/exp002b_figures.py` (`g3`) | same | C2 | **AVAILABLE** — re-run of F7's ablation with score-derived features excluded by construction |
| F11 | Singleton-candidate confidence, before vs. after the Part-1 fix | `src/analysis/exp002b_figures.py` (`g4`) | same | C2-confidence | **AVAILABLE** — the headline evidence for `paper/CLAIM_LEDGER.md`'s new C2-confidence sub-claim |

## EXP002-C / EXP002-C2 / EXP002-C3: no figure

Acquisition-throughput engineering, not a verifier/selection result — the
numeric tables in `experiments/EXP002C/PILOT_RESULTS.md`,
`experiments/EXP002C2/RESULTS.md`/`RESOURCE_ANALYSIS.md`, and
`experiments/EXP002C3/RESULTS.md`/`RESOURCE_ANALYSIS.md`/
`HOST_TOPOLOGY.md` are the full record. No plotting script exists for any
of the three and none is planned; per rule 1, this is stated explicitly
rather than left silent.

## EXP002-D: no figure

Verifier evaluation over ACQ-001's corpus — the numeric tables in
`experiments/EXP002D/RESULTS.md`, `ABLATION_RESULTS.md`, and
`CALIBRATION_RESULTS.md` are the full record (reliability-diagram data is
present in `artifacts/EXP002D/calibration.json`'s `reliability_bins`
field but not yet plotted). No plotting script exists for this pass and
none is planned unless a future pass revisits the negative result with a
different generator/feature family; per rule 1, stated explicitly rather
than left silent.

## Note on F1/F2/T1

These three are producible today, CPU-only, from data already on disk. They are
the only figures this project can currently generate, and they are generated in
Phase 3. Everything else is honestly marked blocked.
