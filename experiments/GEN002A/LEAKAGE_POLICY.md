# GEN002-A — LEAKAGE_POLICY

Three leakage surfaces, audited before any search code runs.

## 1. Generation-time leakage

No search or scoring function ever receives a test output. Enforced
structurally, not just by convention:

- `search/best_first.py`'s priority function signature is
  `score(program, train_pairs) -> tuple`; there is no `test_pair`
  parameter for it to misuse.
- Demonstration validation (Phase 5) checks a candidate program against
  training pairs only, before it is ever applied to a test input to
  produce a candidate grid.
- The test input's *shape and cells* are legitimately visible (a solver
  must see what it's asked to transform) — only the test *output* is
  withheld until Phase 7.
- A static check (`tests/gen002/test_no_leakage.py`) greps the search and
  DSL modules for any reference to a solutions-file path or a `test`
  dict key used for anything but reading `input`.

## 2. Sample-selection leakage

The 24-index pilot sample is GEN001-A's, frozen before any NVARC or
program-synthesis prediction existed
(`experiments/GEN001A/PILOT_SAMPLE.md`). GEN002-A reads it read-only
(`artifacts/GEN001A/pilot_manifest.json`) and does not re-derive or
re-stratify it. No program-synthesis result can have influenced which 24
indices were chosen, because they were chosen before this experiment's DSL
existed.

## 3. Primitive-design leakage (the acceptance message's explicit prohibition)

**No primitive is added, and no existing primitive's parameters are
tuned, after Phase 6's pilot run produces correctness results.**
`DSL_SPEC.md` is committed (Phase 0) before implementation, and the DSL's
actual implementation (Phase 3) is committed before Phase 6 runs — both
before pilot correctness is known. If Phase 8's error analysis identifies
a missing-language gap, the fix is scoped to a *future, separately
preregistered* experiment (`PLAN.md`'s stopping rule), never a same-pass
edit. This is checked mechanically, not just by discipline: `src/gen002/dsl/`'s
git history within this phase shows commits ordered PLAN → DSL_SPEC →
implementation → pilot run → analysis, and no DSL commit follows a pilot
run commit.

## 4. Pretrained-checkpoint contamination — structurally absent

Unlike GEN001-A's NVARC checkpoint (`experiments/GEN001A/CONTAMINATION_AUDIT.md`,
SCIENTIFICALLY CONTAMINATED against all 160 ACQ-001 tasks), this generator
has no pretrained parameters and no training corpus of any kind. There is
no contamination classification to run, because there is no training data
whose provenance could overlap ACQ-001's tasks — the DSL and search
algorithm are fixed, general-purpose code, not learned from any ARC
corpus, this project's or any other's. This is the structural property
`PLAN.md`'s central question is built around: this pilot's results, unlike
GEN001-A's, can potentially become clean paper evidence directly, subject
only to the usual generalization caveats of a small (n=24), CPU-only
pilot — not to a contamination gate.
