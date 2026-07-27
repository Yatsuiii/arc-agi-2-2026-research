# DATA001-A — MODEL_PREFLIGHT_SPEC

## Objective

Prepare the infrastructure for a later clean neural candidate-generator
pilot without selecting a final base model or consuming GPU quota during
DATA001-A.

## Required model-independent interfaces

The local harness must support:

- direct-grid training targets;
- optional structured-trace auxiliary targets;
- family-balanced sampling;
- curriculum scheduling;
- tokenizer compatibility checks;
- sequence-length statistics;
- checkpoint/config hashing;
- deterministic seeds;
- validation generation;
- candidate export in the shared archive schema;
- exact-grid parsing and malformed-output tracking.

## Allowed local validation

DATA001-A may run:

- dataset iteration;
- serialization round trips;
- batch construction;
- mock prediction evaluation;
- a tiny already-installed overfit smoke test only if it does not pull
  new heavy dependencies or large checkpoints.

## Deferred decisions

DATA001-A explicitly defers:

- final base-model selection;
- GPU-backed training;
- broad model comparison;
- claims about 4B versus 9B preference;
- held-out ACQ-001 model evaluation.

## Launch gate for MODEL001-A

MODEL001-A may be launched later only if DATA001-A finishes with:

- a clean accepted synthetic corpus;
- leakage controls that hold up under exact and structural checks;
- passing local harness validation;
- a bounded hardware and runtime projection that fits available quota.
