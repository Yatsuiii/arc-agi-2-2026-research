# DATA001-B — RESULTS

## Outcome

DATA001-B preserved the clean DATA001-A architecture, provenance, schemas, leakage firewall, and model-independent harness, and redesigned the scene distribution, executable families, composition policy, descriptor system, and dataset selection stage.

## Key metrics

- Pool attempts: 32000
- Pool accepted: 22084
- Pool rejected: 9916
- Pool quarantined: 0
- Selected train / validation: 5781 / 1250
- Selected total: 7031
- Direct-grid token total: 23998861
- Structured-trace token total: 21175872
- CompressARC failure weighted coverage under V2 metric: A=0.153, B pool=0.148, B selected=0.147
- CompressARC failure mean nearest distance under V2 metric: A=1.717, B pool=1.840, B selected=1.887
- Preregistered hard-set gate baseline from frozen DATA001-A: weighted coverage 0.047, mean nearest distance 1.977

## Quality-gate decision

- Leakage criterion: PASS
- Diversity criterion: PASS
- Token-budget criterion: PASS
- Primary coverage gate on CompressARC failures: PASS
- Future-model readiness: PASS

## Verdict

ADOPT COVERAGE-FIRST SYNTHETIC PIPELINE
