# GEN001-A — QUOTA_PROJECTION

Projects the 24-index pilot's GPU runtime and Kaggle quota consumption from
RUN-001's own measurements. This phase does not query or assume the user's
live remaining quota — that check is deferred to the human confirming
launch (`PILOT_PROTOCOL.md`'s launch gate).

## RUN-001 reference numbers used

| Quantity | Value | Source |
| --- | --- | --- |
| Tasks reached | 77/120 | `experiments/RUN001/RESULTS.md` |
| Wall-clock budget consumed reaching them | 11h43m (42,180s), 2 workers | same |
| Tasks that hit the per-task 1200s time guard | 41/77 (53%) | `docs/NVARC_SCORE_GAP.md` |
| Per-task time guard | 1200s | `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §10-11 |
| Model-load overhead per worker | **not directly measured in RUN-001** | — |

## Per-task throughput estimate

`77 tasks reached / 2 workers` over `42,180s` of wall-clock gives an average
of `(42,180 x 2) / 77 ≈ 1,095s` of worker-time per task. This is close to
the 1,200s cap, consistent with 53% of reached tasks hitting it — so the
average is not a loose bound, it is close to the worst case.

## 24-index pilot projection

- 24 test-indices, one per task (`PILOT_SAMPLE.md` — no task contributes
  more than one), 2 workers (2xT4, dynamic queue, same as RUN-001) → 12
  tasks/worker in the worst-case sequential assignment.
- **Expected wall-clock**: `12 x 1,095s ≈ 13,140s ≈ 3.65h`.
- **Worst case** (every task hits the full 1,200s cap): `12 x 1,200s =
  14,400s = 4.0h`.
- **Model-load overhead**: unmeasured directly; RUN-001's notebook loads
  the model once per worker, not per task, so this is a one-time addend,
  not a per-task multiplier. Estimated 5-10 minutes per worker based on
  4-bit Unsloth checkpoint loads of comparable size, **not a measurement** —
  flagged as the single largest source of uncertainty in this projection.
- **Combined estimate**: **3.7-4.2 hours**, midpoint ≈ **4.0h**.
- **Uncertainty interval**: 2.5h (optimistic — pilot tasks finish faster
  than RUN-001's average) to 4.5h (pessimistic — every task hits its cap
  plus slow model load). Wide because n=24 is a small sample and RUN-001's
  own per-task variance was not characterised beyond the guard-hit
  fraction.

## Storage

ACQ-001's Shard A archive (85 test-indices, 36,208 candidate records)
compressed to 2.04 MB (`artifacts/ACQ001/shard_a_output/.../candidates.A.jsonl.gz`),
≈56 bytes/candidate compressed. At ACQ-001's own per-index candidate density
(≈426/index), 24 test-indices project to roughly 10,200 candidates ≈ 570
KB compressed — negligible against Kaggle's 19.5 GB writable working
directory (`paper/REPRODUCIBILITY.md`).

## Minimum remaining quota required

Using this project's fixed launch condition:

```
REMAINING KAGGLE GPU QUOTA >= PREDICTED PILOT WALL-CLOCK x 1.5 + 1 HOUR
```

With the 4.0h midpoint estimate: `4.0 x 1.5 + 1 = 7.0 hours` minimum
remaining quota required before launch. Using the pessimistic 4.5h bound:
`4.5 x 1.5 + 1 = 7.75 hours`. **Recommended minimum to check before
launch: 8 hours remaining Kaggle GPU quota**, rounding the pessimistic
case up.

## What this projection does not do

It does not check or assume any live quota figure — Phase 8's own
instruction is explicit that this phase must not query the user's actual
remaining quota. The number above is the threshold a human checks
manually (`~/arc-agi-2-2026/.tools/kaggle-venv/bin/kaggle` or the Kaggle
UI) before running the launch command in `KERNEL_PREFLIGHT.md`.
