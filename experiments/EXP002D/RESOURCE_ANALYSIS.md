# EXP002-D — RESOURCE_ANALYSIS

Entirely CPU-only, local machine, no Kaggle, no GPU, per the execution
limits. Wall-clock times measured directly from each pipeline stage's own
run (this session, single-threaded except for numpy/sklearn's internal
BLAS parallelism).

| Stage | Script | Wall-clock | Notes |
| --- | --- | --- | --- |
| Corpus reconciliation | `src/analysis/exp002d/corpus.py` | ~3s | Reads both ACQ-001 archives (73,147 records) |
| Fold assignment | `src/analysis/exp002d/folds.py` | <1s | 160 tasks |
| Feature computation (F0-F5) | `src/analysis/exp002d/features.py` | ~66s | 70,680 candidates x ~20 structural checks each, numpy-vectorised F4 relational features |
| Model fitting + evaluation (V1-V6, 5 folds) | `src/analysis/exp002d/run_eval.py` | ~62s | 5 outer folds x (2 pointwise model types x 2 feature sets + 2 pairwise fits + 1 ensemble grid search) |
| Statistical tests (McNemar, bootstrap) | `src/analysis/exp002d/stats.py` | ~29s | 2000-resample stratified bootstrap x 12 tracks (naive + diverse) |
| Calibration + sufficiency | `src/analysis/exp002d/calibration.py` | ~2s | Per-fold Platt scaling x 6 tracks |
| Ablation matrix (A0-A6) | `src/analysis/exp002d/ablation.py` | ~23s | 7 ablations x 5 folds |
| Error taxonomy | `src/analysis/exp002d/error_taxonomy.py` | ~3s | 171 test-indices |
| **Total** | — | **~3.2 minutes** | Single run, no retries needed |

## Memory

No stage exceeded a few hundred MB resident (largest in-memory object is
the 70,680-row x 34-column feature DataFrame, plus per-fold numpy
pairwise-distance matrices up to 1058x1058 floats — a few MB each,
transient). No out-of-memory event, no swapping observed.

## Disk

`artifacts/EXP002D/` totals 19 MB: 4.7 MB `candidate_features.parquet`,
5.8 MB `canonical_candidate_index.parquet` (grid content included), 7.9 MB
`model_predictions.parquet` (per-fold scored candidates for all 6 score
columns), remainder JSON/CSV summaries.

## Cost relative to ACQ-001

ACQ-001's two shards together cost 37.67 Kaggle-quota GPU-hours. This
entire experiment — corpus reconciliation through the full statistical
analysis, ablation matrix, and error taxonomy — cost **zero GPU-hours and
about 3 minutes of local CPU time**, roughly 750x cheaper in wall-clock
terms than the acquisition that produced its input data. This asymmetry
is the direct motivation for CPU-only verifier research being a cheap,
fast way to test selection-side hypotheses before spending further GPU
budget on generation-side changes — and, per this experiment's own
result, the generation side is where the real ceiling is (`RESULTS.md`,
`docs/POST_ACQ001_STRATEGIC_DECISION.md`).
