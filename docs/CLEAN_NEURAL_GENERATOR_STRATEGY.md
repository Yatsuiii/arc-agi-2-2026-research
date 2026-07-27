# CLEAN_NEURAL_GENERATOR_STRATEGY

## Why verifier research was frozen

EXP002-D showed that at ACQ-001's powered 171-index scale, every tested clean verifier underperformed the frozen native selector. The remaining oracle gap is real but not recoverable by the tested verifier family under this project's compute and feature constraints.

## Why symbolic research was frozen

GEN002-A and GEN002-B both produced clean null results. The redesigned typed symbolic line still emitted zero candidates on fresh held-out validation and reached only 2/75 exact-program coverage on TRAIN/DEV.

## Why learned candidate generation is now the primary clean direction

A synthetic pipeline gives the project one thing the frozen branches lacked: scalable clean supervision with exact provenance. It supports both direct-grid prediction and auxiliary structured traces without touching held-out outputs.

## What NVARC still provides

NVARC remains relevant as competition engineering context and as a contamination-labelled control in future model pilots.

## Why NVARC cannot provide clean paper evidence

Its lineage and synthetic-data provenance overlap the ACQ-001 task pool in ways that block clean held-out claims for this project.

## DATA001-A minimum quality gates before training

1. several thousand accepted tasks;
2. zero admitted exact/structural overlap with held-out references;
3. multiple executable transformation families and at least two composition depths;
4. local serialization / batching / parsing / export checks pass;
5. descriptor coverage materially broader than the frozen symbolic line.

## Conditions for launching MODEL001-A

- GPU quota available;
- the clean corpus and manifests stay frozen;
- a single 4B-class clean model plus one smaller control are enough to answer the next decision;
- the contaminated NVARC lineage remains quarantined to control-only status.

## Conditions for abandoning the synthetic pipeline

- structural leakage becomes unmanageable under future scale-up;
- accepted-task diversity stalls around trivial families;
- direct-grid decoding remains mostly malformed even in bounded pilots;
- future clean pilots fail to add coverage over CompressARC at reasonable cost.
