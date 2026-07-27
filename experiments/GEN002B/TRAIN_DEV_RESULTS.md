# GEN002-B — TRAIN_DEV_RESULTS

Frozen benchmark: `50` training tasks + `25` development tasks, selected
deterministically and written into `artifacts/GEN002B/frozen_config.json`.

## Aggregate results

| Metric | Result |
| --- | ---: |
| Tasks | 75 |
| Held-out test indices | 95 |
| Tasks with at least one exact demonstration-consistent program | 2/75 (**2.67%**) |
| Held-out test-index accuracy | 2/95 (**2.11%**) |
| States explored | 518,001 |
| Runtime | 28.8313s |
| Peak RAM | 191.473 MB |

## Failure breakdown

| Category | Count |
| --- | ---: |
| Success | 2 |
| Generalization failure | 0 |
| Search failure | 8 |
| Missing language | 85 |
| Representation failure | 0 |

Split detail:

- TRAIN held-out indices: 54 total, 2 successes, 5 search failures, 47
  missing-language.
- DEV held-out indices: 41 total, 0 successes, 3 search failures, 38
  missing-language.

## Template usage

- `uniform_scale`: 1 exact hit (`c59eb873`, TRAIN)
- `legacy_s1` fallback: 1 exact hit (`f25fbde4`, TRAIN)

No other template family produced an exact held-out success on the frozen
benchmark subset. This was already below any plausible success threshold,
but the frozen configuration was still carried forward exactly once to the
fresh 24-index validation pilot as required.
