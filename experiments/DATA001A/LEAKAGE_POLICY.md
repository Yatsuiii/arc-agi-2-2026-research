# DATA001-A — LEAKAGE_POLICY

## Allowed inputs during generator development

DATA001-A may use:

- ARC TRAIN tasks and outputs;
- ARC-AGI-2 TRAIN and DEV descriptors and legal metadata;
- ACQ-001 manifest metadata needed for contamination checking;
- frozen CompressARC failure descriptors and aggregate statistics;
- local papers, reports, and codebases for architectural reference;
- frozen GEN001-A, GEN002-A, and GEN002-B reports as negative evidence.

## Forbidden inputs during generation

The generator may not use:

- held-out ACQ-001 test outputs;
- hidden outputs from any of the 171 held-out test indices;
- NVARC data artifacts or code whose licence does not permit reuse;
- Kaggle or cloud compute;
- paid APIs;
- manual task templates reverse-engineered from held-out answers.

## Contamination controls

Every generated task must be checked against:

- ARC-AGI-1;
- ARC-AGI-2;
- ACQ-001 TRAIN;
- ACQ-001 DEV;
- all 160 ACQ-001 held-out tasks;
- all 171 held-out test indices;
- Kaggle placeholder tasks.

The firewall includes exact checks and structural checks. A task is not
considered clean merely because exact hashes differ.

## Quarantine rule

Generated tasks with suspicious similarity are either:

- excluded from the accepted corpus; or
- written to `artifacts/DATA001A/quarantined_tasks.jsonl` with the
  triggered overlap features recorded.

Quarantined tasks do not enter training or validation splits.

## Split discipline

Synthetic train/validation splits must be family-disjoint where
possible. Coverage analysis against held-out references occurs after the
pilot corpus is frozen. If the analysis reveals coverage gaps, proposed
improvements are deferred to DATA001-B rather than patched into the
frozen pilot.
