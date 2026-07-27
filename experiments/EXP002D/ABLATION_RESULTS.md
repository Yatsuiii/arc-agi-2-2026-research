# EXP002-D — ABLATION_RESULTS

Bounded matrix, `src/analysis/exp002d/ablation.py`, same 5 outer folds.
F2 and F3 are bundled by `structural_features` (cannot be cleanly split
without forking that function — see the module's own docstring), so A1
already represents F2+F3 combined, not F2 alone; recorded as a scoping
decision in the ablation module's docstring, not glossed over.

| Ablation | Features | Model | Top-1 | Top-2 | Oracle-gap recovery | Candidate AUROC | Candidate AUPRC | Brier (rank-1) | ECE (rank-1) | Runtime (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 native only | F0/F1 (5) | none (direct rank by `beam_score_best`) | 11.70% | **13.45%** | 0.0% | 0.956 | 0.255 | 0.089 | 0.089 | ~0 |
| A1 structural | F2+F3 (14) | logreg | 1.75% | 2.92% | -94.7% | 0.793 | low | high | high | see `ablation_results.json` |
| A2 + provenance | F2+F3+F5 (17) | logreg | 1.75% | 2.92% | -94.7% | 0.793 | low | — | — | — |
| A3 + relational | F2+F3+F5+F4 (21) | logreg | 2.34% | 3.51% | -89.5% | 0.770 | low | — | — | — |
| A4 hybrid | F0/F1+F2-F5 (26) | logreg | — | 12.28% | -10.5% | 0.915 | — | — | — | — |
| A5 hybrid (HGB) | same as A4 | HistGradientBoosting | — | 10.53% | -26.3% | 0.935 | — | — | — | — |
| A6 hybrid (HGB) + diverse 2nd pick | same as A5 | HistGradientBoosting, diversity-aware top-2 | — | 10.53% | -26.3% | 0.935 | — | — | — | — |

Exact numbers, including the fields left as "—" above for space, are in
`artifacts/EXP002D/ablation_results.json`.

## Reading the matrix

- **A0 -> A1**: adding score-independent structural/train-consistency
  features *alone* (dropping the native score entirely) collapses top-2
  accuracy from 13.45% to 2.92% — expected, since these features are
  weaker rankers of the ~427-candidate field even though they carry real
  isolated signal (AUROC 0.79, well above chance).
- **A1 -> A2**: adding the thin F5 provenance group changes nothing
  measurable — consistent with `FEATURE_CATALOG.md`'s own note that
  `task_hit_time_guard` has zero variance in this corpus and
  `task_steps_run`/`task_elapsed_s` duplicate the same underlying value.
- **A2 -> A3**: adding F4 relational features (consensus frequency,
  distance from modal) gives a small absolute gain (2.92% -> 3.51%) but
  is still 89.5% below the oracle-gap recovery a working verifier would
  need, and candidate-level AUROC *drops* slightly (0.793 -> 0.770) —
  consensus frequency, on a corpus with 96.6% unique candidates,
  contributes mostly noise.
- **A3 -> A4**: adding the native score back (full hybrid) recovers most
  of the way to native-only performance (12.28% vs. 13.45%) but does not
  exceed it — the independent/relational features add no headroom once
  the native score is present, only a small net drag.
- **A4 -> A5**: swapping logistic regression for `HistGradientBoosting`
  on the identical hybrid feature set makes things *worse* (12.28% ->
  10.53%), despite a higher candidate-level AUROC (0.935 vs. 0.915) —
  the tree model overfits to features that matter locally within a
  fold's training positives (n=22-30) without adding decision-relevant
  signal for the held-out top-2 selection; more instance-level
  discrimination did not translate to correct top-2 slot ordering.
- **A5 -> A6**: the diversity-aware second-pick rule changes nothing on
  this feature/model combination (10.53% -> 10.53%) — the model's own
  top-2 candidates were already sufficiently diverse (distance >= 0.05)
  in every case tested; see `RESULTS.md`'s V6_diverse row for the one
  track where the diversity rule did measurably change the outcome
  (9.94% -> 9.36%, a further small loss, not a gain).

No post-hoc feature fishing was performed; every row above uses exactly
the preregistered feature groups from `FEATURE_CATALOG.md`.
