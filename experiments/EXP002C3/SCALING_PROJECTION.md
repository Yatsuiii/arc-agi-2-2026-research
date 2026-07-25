# EXP002-C3 — SCALING_PROJECTION

Since `RESULTS.md`'s verdict is **KEEP FROZEN C3**, the acquisition-cost
basis is unchanged from `experiments/EXP002C2/SCALING_PROJECTION.md` — this
document restates it for EXP002-C3's own record rather than recomputing
from B1/B2 (neither is adopted, so neither should set the projection).

## Basis numbers (unchanged, C3-derived)

| | Value | Source |
| --- | --- | --- |
| C3 test-indices/hour | 8.91/hour | `experiments/EXP002C2/RESULTS.md` §7 |
| Kaggle quota-hours per wall-clock hour | 2 | `paper/COMPUTE_LEDGER.md` |
| Test-indices per task (5-task sample) | 1.2 | `experiments/EXP002C/pilot_sample.json` — still highly uncertain at this n |
| Observed failure rate (C3+C4+B1+B2 combined) | 0/20 task-processes | `experiments/EXP002C2/RESULTS.md` + this pilot's `RESULTS.md` §10 |

## Projections (identical to `experiments/EXP002C2/SCALING_PROJECTION.md`)

| Target | Wall-clock hours | Kaggle sessions (12h cap) | Kaggle quota GPU-hours | Estimated storage | Estimated candidates | Retry allowance |
| --- | --- | --- | --- | --- | --- | --- |
| 100 test-indices | 11.2 | 1 | 22.4 | ~9.5 MB | ~26,480 | +10-15% wall-clock margin |
| 140 test-indices | 15.7 | 2 | 31.4 | ~13.3 MB | ~37,072 | same |
| 170 test-indices (McNemar floor) | 19.1 | 2 | 38.1 | ~16.1 MB | ~45,016 | same |
| 250 test-indices | 28.1 | 3 | 56.2 | ~23.8 MB | ~66,200 | same |
| 500 test-indices | 56.2 | 5 | 112.3 | ~47.6 MB | ~132,400 | same |

Uncertainty range for 500 test-indices: 112-334 Kaggle quota GPU-hours
(unchanged basis: C1's un-oversubscribed rate as the conservative bound,
C3/C4's oversubscribed rate as the tested-optimistic bound —
`experiments/EXP002C2/SCALING_PROJECTION.md` for the full derivation).

## What this pilot changes about the projection: nothing to the numbers, one qualitative addition

EXP002-C3 does not revise any of these figures upward or downward — B1/B2
were not adopted, so C3 remains the operating point the projection is
built on. What EXP002-C3 *adds* is a resolved explanation for *why* the
gap between task-count throughput (~3x) and candidate-throughput (~1.4x)
exists (`RESULTS.md` §4: GPU-level sharing, not CPU orchestration) — this
means the acquisition team should **not expect further CPU-side tuning to
improve on C3's measured rate**, so 8.91 test-idx/hour is a reasonably
stable planning number, not a pessimistic placeholder waiting on an
orchestration fix.

## Minimum statistically powered corpus (unchanged)

170 test-indices remains the pre-registered McNemar floor
(`experiments/EXP002B/CORPUS_REQUIREMENTS.md`), payable in ~38 Kaggle
quota GPU-hours / ~2 sessions at C3's measured rate — unaffected by this
pilot's null result on CPU orchestration.

## Recommendation

Unchanged from `experiments/EXP002C2/SCALING_PROJECTION.md`: the
500-test-index target (112-334 GPU-hours) is feasible within the project's
compute budget; 170-250 test-indices is unambiguously payable in 1-3 weeks.
This pilot's contribution is confidence, not a new number: C3's rate is now
understood to be close to this workload's real ceiling on 2xT4 given the
measured 4-vCPU host, rather than a rate future orchestration tuning might
still meaningfully beat.
