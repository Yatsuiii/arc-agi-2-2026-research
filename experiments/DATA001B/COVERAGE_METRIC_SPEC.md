# DATA001-B — COVERAGE_METRIC_SPEC

## Principle

Coverage must measure meaningful ARC structure, not only superficial
size/colour marginals.

## Frozen metric families

Descriptor groups:

1. grid scale
2. colour structure
3. object structure
4. relational structure
5. transformation structure
6. complexity

Each task is mapped to:

- backward-compatible DATA001-A descriptor bins for direct comparison;
- a V2 descriptor vector with stable categorical bins;
- a scalar nearest-structure distance in that V2 space.

## Frozen reported metrics

For every reference corpus, DATA001-B reports:

- unique descriptor coverage;
- weighted descriptor coverage;
- descriptor-bin occupancy;
- family coverage;
- scale coverage;
- colour coverage;
- object-count coverage;
- relational coverage;
- output-expansion coverage;
- composition-depth coverage;
- mean nearest-structure distance;
- token cost per covered descriptor bin.

## Reference sets

A. ARC TRAIN  
B. clean DEV (`artifacts/ACQ001/folds.json`'s `dev_task_ids`)  
C. ACQ-001 full corpus, clearly labelled descriptive/transductive  
D. CompressARC's 129 generation failures, clearly labelled
descriptive/transductive

## Frozen success thresholds

Primary descriptive coverage gate on the 129 failure indices:

- weighted descriptor coverage >= `0.12`
- weighted coverage improvement factor >= `2.5x` over DATA001-A
- mean nearest-distance < `1.80`

Secondary gates:

- high-colour bins materially populated;
- high-object bins materially populated;
- large-grid bins materially populated;
- depth-2 and depth-3 accepted tasks meet the frozen balance target;
- leakage audit remains clean.

Coverage metrics are explicitly not treated as evidence of solver
accuracy.
