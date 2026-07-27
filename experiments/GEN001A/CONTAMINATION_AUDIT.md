# GEN001-A — CONTAMINATION_AUDIT

Classification per `CONTAMINATION_POLICY.md`, computed before any pilot
code touches the checkpoint. Full per-task table:
`artifacts/GEN001A/task_overlap.csv`.

## The finding

**All 160 of ACQ-001's tasks are members of the exact file glob NVARC's SDG
pipeline used to build its `arc2_training` fine-tuning dataset, and that
dataset includes each task's test-pair ground-truth output, not just its
demonstration pairs.**

## Evidence chain

1. `references/score_winners/01_nvarc/SDG/scripts/build_datasets.py:246`:

   ```python
   ds = convert_arc_to_messages("external/ARC-AGI-2/data/training/*.json", seed=3)
   ds.save_to_disk(f"{output_path}/arc2_training")
   ```

   `convert_arc_to_messages` defaults to `num_samples=256` (no override
   given for this call, unlike the `arc2_evaluation6` call which passes
   `num_samples=6`) — so every included task contributes **256 augmented
   training samples**, not 6.

2. Inside `convert_arc_to_messages` (`build_datasets.py:143`):

   ```python
   pairs = data["train"] + data["test"]
   ```

   **The test-pair(s) are concatenated directly into the pool of pairs used
   to build training messages.** For an ARC-AGI-2 training-split task file,
   `data["test"]` includes the full input/output pair (unlike a competition
   evaluation file, training-split task files ship the test output because
   that is the file format's standard shape for a "training" task — this is
   distinct from, and a strictly worse contamination path than, the
   `arc2_evaluation6` path `docs/NVARC_LINEAGE.md` already documented,
   because here the test *output* enters the SDG mixture as a directly
   modelled input/output pair rather than as an held-out answer used only
   for a different task's self-scoring).

3. `competition_2026/extracted/arc-agi_training_challenges.json` (ACQ-001's
   own corpus source, `artifacts/ACQ001/corpus_manifest.json:source`) is
   **byte-identical by task-ID set** to `benchmark/ARC-AGI-2/data/training/`
   — verified directly: `1000/1000` task IDs match, `0` present in only one
   side. This is the same file glob `build_datasets.py:246` reads (modulo
   local path — `external/ARC-AGI-2/data/training/` in NVARC's own tree,
   `benchmark/ARC-AGI-2/data/training/` in this workspace, both the
   upstream ARC-AGI-2 public training split).

4. ACQ-001's 160 corpus tasks are drawn from this same 1000-task training
   file (`artifacts/ACQ001/corpus_manifest.json: n_test_tasks=160,
   source=.../arc-agi_training_challenges.json`). Cross-referencing the 160
   task IDs actually acquired (`run_manifest.{A,B}.json:task_ids`) against
   `benchmark/ARC-AGI-2/data/training/`: **160/160 present, 0/160 present
   in the evaluation split** (`artifacts/GEN001A/task_overlap.csv`).

## One unverifiable caveat, stated rather than silently assumed away

`convert_arc_to_messages` skips a puzzle if its basename collides with a
name in `external/re-arc/re_arc/tasks/*.json`
(`build_datasets.py:143-146`). RE-ARC's own task-naming convention uses
ARC-AGI-1's original 8-character hex task IDs; ARC-AGI-2's training set
uses its own (distinct but same-format) 8-character hex IDs, and RE-ARC
data is **not present in this workspace** (`find` over `~/arc-agi-2-2026`
returns nothing for `re-arc`/`re_arc`), so this skip-list cannot be checked
locally. Per `CONTAMINATION_POLICY.md`'s rule — **a missing manifest is
never read as clean** — this does not soften the classification below for
any of the 160 tasks; it is recorded as an open, currently-unresolvable
verification gap, not grounds for a cleaner label.

## Overlap with the evaluation-split contamination path

Independently, `docs/NVARC_LINEAGE.md` already documents `arc2_evaluation6`
(all 120 ARC-AGI-2 evaluation tasks, 6 aug, with test-pair ground truth).
ACQ-001's 160-task corpus has **zero overlap** with the 120-task evaluation
split (`artifacts/GEN001A/task_overlap.csv`: `in_arc2_evaluation_split=0`
for all 160 rows) — this specific contamination path does not apply to
ACQ-001's corpus. The training-split path (above) is a distinct and, for
this corpus, the operative contamination mechanism.

## Classification

**SCIENTIFICALLY CONTAMINATED**, for all 160/160 of ACQ-001's tasks, per
`CONTAMINATION_POLICY.md` category 3 ("overlap is confirmed for all or
most of the corpus's tasks, or overlap is confirmed for the corpus's core
evaluation signal — test-pair outputs — specifically"). Both conditions in
category 3 hold simultaneously here: the overlap is total (160/160) and it
is specifically the test-pair output, not merely the demonstration pairs,
that is implicated.

## Consequences (per `CONTAMINATION_POLICY.md`, restated concretely)

- The GEN001-A pilot (Phases 5-9) proceeds as a **competition-engineering
  experiment only**: it can still answer "does this generator's candidate
  set contain grids CompressARC's does not," which is a set-membership
  question the checkpoint's training exposure does not trivially resolve
  in NVARC's favour (memorizing a task's output does not guarantee the
  4-bit-quantized, TTT-adapted, 2xT4-constrained inference pass actually
  reproduces it at generation time — RUN-001's own 23.4% accuracy on
  candidate-bearing, *evaluation-split-contaminated* tasks is the closest
  local evidence that contamination does not equal perfect recall).
- **No accuracy or oracle-coverage number from this checkpoint on
  ACQ-001's corpus may be reported as clean paper evidence.** Any future
  pilot result is contamination-labelled in every table it appears in.
- **NVARC pilot outputs must never be merged into, or used to train or
  evaluate, the EXP002-D clean-verifier corpus or any successor.** That
  corpus's entire scientific value is contingent on leakage-audited
  cleanliness (`experiments/EXP002D/LEAKAGE_AUDIT.md`); this is now a
  second, independent reason (beyond EXP002-D's own frozen verdict) not to
  mix generator families into it without a fresh, separately-audited
  corpus.
- Every record `src/gen001/nvarc_adapter.py` produces carries
  `contamination_status="SCIENTIFICALLY_CONTAMINATED"` as a first-class
  field (Phase 6), never inferred after the fact from which pipeline
  produced it.

## What this does not establish

This audit does not measure whether contamination *helps* NVARC's
inference-time accuracy on this corpus — that would require actually
running the pilot, which this phase does not do. It only establishes that
any future accuracy number from this checkpoint on this corpus cannot be
read as measuring generalisation, only as measuring (at best) a
contamination-inflated upper bound, and must be labelled as such
permanently.
