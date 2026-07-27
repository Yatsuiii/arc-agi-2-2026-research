# DATA001-B — PLAN

## Objective

Redesign the clean synthetic curriculum from DATA001-A so that coverage,
not only executability, drives the dataset. The goal is a broader,
token-budget-aware corpus that better matches difficult ARC structure
without reproducing held-out tasks.

## Frozen predecessor

DATA001-A is frozen at commit
`3fd09cd1f5bd7798e58013e1f4d591bcb4651fa4`. Its clean-room generator,
leakage firewall, schemas, provenance, and model-independent harness are
preserved. Its verdict was `REDESIGN SYNTHETIC PIPELINE` because
descriptor coverage on ARC TRAIN, ACQ-001, and the 129 CompressARC
generation failures remained too thin.

## Scope

DATA001-B changes:

1. the descriptor system;
2. the scene distribution;
3. the transformation-family set;
4. the composition policy;
5. the final dataset-selection algorithm.

DATA001-B does not change:

- the clean-room architecture;
- provenance and hashing discipline;
- leakage controls as a baseline;
- direct-grid / structured-trace schemas;
- the model-independent harness;
- the prohibition on Kaggle, paid APIs, verifier reopening, symbolic
  reopening, and held-out-output use.

## Frozen phases

1. Isolate a new worktree from the frozen DATA001-A commit.
2. Freeze coverage metrics, target distribution, family set, attempt
   budget, token budget, and selection objective before implementation.
3. Expand descriptors to structural coverage V2.
4. Expand scene modes and transformation families to target the exposed
   gap regions.
5. Generate a large valid candidate pool under deterministic sharding.
6. Select a compact train/validation corpus under a frozen token budget.
7. Re-run leakage checks with stronger structural quarantine.
8. Measure DATA001-A vs DATA001-B coverage under identical metrics.
9. Run internal family generalization and serialization checks.
10. Recompute hardware projections for a later bounded MODEL001-A pilot.
11. Freeze one verdict without launching training.

## Frozen targets

- Pool attempt budget: `32000` generation attempts.
- Pool acceptance target: at least `25000` valid candidate tasks if
  feasible.
- Final selected corpus target: `10000` tasks, with an allowed band of
  `8000-12000`.
- Final split target: family-disjoint train/validation, roughly
  `85/15` by task count.
- Accepted-depth target: approximately `40%` effective depth 1,
  `40%` effective depth 2, `20%` effective depth 3.
- Direct-grid token budget for the selected corpus: target under
  `24,000,000` tokenizer-units by the local deterministic tokenizer.
- Primary descriptive coverage gate on the 129 CompressARC failures:
  weighted descriptor coverage at least `0.12`, which is at least 2.5x
  DATA001-A's `0.047`, and mean nearest-structure distance materially
  below `1.977`.

## Baseline note

In the sibling worktree:

- `PYTHONPATH=. pytest -q` reaches `374 passed, 1 failed`.
- The single failure remains
  `tests/gen001/test_pilot_notebook.py::test_build_produces_a_notebook`,
  caused by a notebook write into the read-only sibling worktree.

This is recorded as a worktree-environment property, not a DATA001-B
regression.
