# DATA001-B — LEAKAGE_POLICY

## Preserved controls from DATA001-A

- exact task hashes;
- grid and pair hashes;
- colour-normalized hashes;
- rotation/reflection-normalized hashes;
- no held-out outputs during generation;
- no ACQ-001 artifact modification;
- no admitted quarantined tasks.

## Strengthened structural controls

DATA001-B additionally freezes:

- scene-graph hashes;
- transformation-trace hashes;
- input-output delta signatures;
- object-correspondence signatures;
- panel-layout signatures;
- composition-tree hashes;
- nearest-neighbour structural review for suspicious cases.

## Allowed descriptive use

Broad input-side and visible-demonstration descriptors from ACQ-001 and
the 129 CompressARC generation failures may inform covariate-gap
targeting only. They may not be used to reproduce task-specific rules.

## Forbidden use

- hidden test outputs;
- target-specific transformation traces;
- correctness labels while generating tasks;
- manual reconstruction of particular held-out tasks;
- task-by-task nearest-example curation.
