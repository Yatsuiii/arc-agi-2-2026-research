# DATA001-A — PLAN

## Objective

Build a clean synthetic ARC task generator, a leakage firewall, and a
model-independent training/evaluation harness that can support a later
small-model learned candidate-generator pilot without consuming Kaggle
GPU quota during this phase.

## Scope

DATA001-A follows two frozen negative branches:

- GEN001-A remains frozen and untouched.
- GEN002-A and GEN002-B remain frozen symbolic null results.

This phase does not reopen verifier research, does not expand the
symbolic DSL again, does not launch NVARC, and does not train a
substantial model.

## Frozen phases

1. Create an isolated worktree from the completed GEN002-B state.
2. Audit existing synthetic-data lineages and choose one clean-room
   architecture before implementation.
3. Define executable structured program and task schemas.
4. Implement structured scene generation and a tiered transformation
   curriculum.
5. Build exact and structural leakage checks against ARC, ACQ-001, and
   placeholder task inventories.
6. Generate a bounded synthetic pilot corpus with immutable manifests.
7. Measure descriptor coverage against legal offline references.
8. Freeze direct-grid and structured-trace target formats.
9. Build a model-independent local training and inference harness.
10. Run CPU/local validation only.
11. Prepare, but do not launch, the later MODEL001-A pilot.
12. Freeze one strategic decision for clean learned candidate generation.

## Success criteria

DATA001-A passes if:

- several thousand valid synthetic tasks are generated;
- no confirmed overlap with ACQ-001 held-out tasks remains after exact
  and structural checks;
- multiple transformation families and composition depths are present;
- serialization and the training harness pass local validation;
- descriptor coverage is materially broader than the frozen symbolic DSL
  surface;
- a bounded later model pilot is operationally feasible.

DATA001-A is a null if:

- accepted tasks are mostly trivial, duplicate, or ambiguous;
- structural similarity to held-out tasks cannot be controlled;
- curriculum diversity is poor;
- dataset construction cost is operationally unreasonable.

## Engineering constraints

- CPU only during this phase.
- No Kaggle, no cloud GPUs, no paid APIs.
- No modification of ACQ-001 artifacts or frozen GEN001/GEN002 claims.
- No held-out outputs during generation.
- No broad model bake-off and no final base-model selection.

## Baseline note

The new branch starts from completed GEN002-B commit
`6eea7016de157d7426e4896bbb999df1bd8bfc1d3`.

In the sibling worktree:

- plain `pytest -q` fails collection because `src` is not on
  `PYTHONPATH`;
- `PYTHONPATH=. pytest -q` reaches 369 passed tests and one failure in
  `tests/gen001/test_pilot_notebook.py`, where the test attempts to
  write a notebook into the read-only sibling worktree.

This is recorded as an environment property of the worktree layout, not
as a DATA001-A regression.
