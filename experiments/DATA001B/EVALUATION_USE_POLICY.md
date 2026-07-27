# DATA001-B — EVALUATION_USE_POLICY

## Labels

- `clean inductive evidence`: ARC TRAIN and clean DEV comparisons that did not use hidden held-out outputs.
- `transductive competition engineering`: aggregate descriptor comparisons against ACQ-001 and the CompressARC 129 failure set, restricted to input-side and visible-demonstration descriptors.
- `descriptive post-hoc analysis`: leakage, token, and structural summaries after frozen dataset construction.

## Prohibitions

DATA001-B does not use hidden test outputs, target-specific transformation traces, correctness labels, task-by-task nearest-example tuning, or manually reconstructed held-out rules.

## Frozen use in this phase

- Curriculum redesign was driven only by broad covariate gaps from DATA001-A.
- Final quality claims remain grounded in clean local validation and leakage-free generation.
- ACQ-001 and CompressARC descriptor comparisons are descriptive/transductive only and are not presented as clean generalization evidence.
