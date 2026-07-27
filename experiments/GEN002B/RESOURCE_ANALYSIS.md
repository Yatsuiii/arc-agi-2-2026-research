# GEN002-B — RESOURCE_ANALYSIS

GEN002-B remained CPU-only throughout. No Kaggle session, no GPU quota, no
paid API, and no network service were used.

## Measured work

| Stage | Measured work |
| --- | ---: |
| Fixed 50/25 TRAIN/DEV benchmark | 28.8313s |
| TRAIN/DEV benchmark states explored | 518,001 |
| TRAIN/DEV benchmark peak RAM | 191.473 MB |
| Fresh 24-index validation generation | 6.937s |
| Fresh validation states explored | 168,000 |
| Fresh validation peak RAM | 136.105 MB |

## Interpretation

The redesign stayed cheap enough to test, which was one of GEN002-B's
stated goals. The negative result is therefore not a budget-exhaustion
artifact: even at low CPU cost, the frozen language/search configuration
failed to emit any candidate on the fresh held-out pilot.
