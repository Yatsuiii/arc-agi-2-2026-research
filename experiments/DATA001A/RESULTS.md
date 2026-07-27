# DATA001-A — RESULTS

## Outcome

DATA001-A generated a clean synthetic pilot corpus and a model-independent local training harness without using Kaggle or cloud GPU.

## Key metrics

- Attempts: 6140
- Accepted tasks: 6000
- Train / validation: 4316 / 1684
- Rejected tasks: 140
- Quarantined tasks: 0
- Family count: 11
- Composition-depth distribution: {'1': 5124, '2': 876}
- ARC TRAIN weighted descriptor coverage: 0.145
- ACQ-001 held-out weighted descriptor coverage: 0.087
- CompressARC failure weighted descriptor coverage: 0.047
- Direct-grid train token mean / p95 / max: 2022.19 / 3562 / 5379

## Quality-gate decision

- Several-thousand-task criterion: PASS
- Leakage criterion: PASS
- Diversity criterion: PASS
- Local-validation criterion: PASS
- Future-pilot feasibility criterion: MARGINAL

## Verdict

REDESIGN SYNTHETIC PIPELINE
