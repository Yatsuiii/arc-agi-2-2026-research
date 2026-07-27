# GEN001-A — CONTAMINATION_POLICY

Written before `CONTAMINATION_AUDIT.md` is produced, so the classification
rule is fixed before the result is known.

## Classification (exactly one, per checkpoint, per corpus)

1. **CLEAN FOR PAPER EVALUATION** — no overlap found between the corpus's
   tasks (or documented transformations/descendants of them) and any stage
   of the checkpoint's training/fine-tuning pipeline, and every stage of
   that pipeline's data provenance is documented well enough to make that a
   positive claim, not an absence of evidence.
2. **PARTIALLY CONTAMINATED** — overlap is confirmed for a strict, named
   subset of the corpus's tasks, and the remaining tasks' provenance is
   independently confirmed clean.
3. **SCIENTIFICALLY CONTAMINATED** — overlap is confirmed for all or most of
   the corpus's tasks, or overlap is confirmed for the corpus's core
   evaluation signal (test-pair outputs) specifically.
4. **TRAINING PROVENANCE UNKNOWN** — no training/fine-tuning manifest is
   available to check against, for all or part of the pipeline.

**A missing manifest is never read as clean.** If a training-data manifest
is absent for a pipeline stage, that stage defaults to category 4 for
whatever fraction of the corpus its absence covers, not category 1.

## Consequences, fixed in advance

If the classification is anything other than CLEAN FOR PAPER EVALUATION:

- The pilot (Phases 5-9) may still be built and, later, run — this is
  explicitly framed as a **competition-engineering experiment**
  (does a second generator move the union-oracle number), not a paper
  evidence-generation run.
- Results from it **may not be reported as clean paper evidence** — no
  accuracy or oracle-coverage number derived from it enters
  `paper/CLAIM_LEDGER.md` as an unqualified claim.
- Its predictions (candidates, scores, selections) **must not be used to
  train or evaluate the frozen clean verifier work** (EXP002-D and any
  successor) — that corpus's entire value is its leakage-audited cleanliness
  (`experiments/EXP002D/LEAKAGE_AUDIT.md`), and mixing in a contaminated
  generator's output would destroy it for every future verifier
  experiment, not just this one.
- **Every artifact and table this pilot produces carries an explicit
  contamination label** (`contamination_status` field, propagated per
  `src/gen001/nvarc_adapter.py`'s candidate schema) — never presented
  unlabelled, never silently dropped from a table.

## What this policy does not gate

Building the adapter, the pilot manifest, and the (unlaunched) Kaggle
package. Those are software-engineering artifacts, not paper claims. The
gate applies to what happens with results once (if) the pilot is later run.

## Scope of the audit this policy governs

`experiments/GEN001A/CONTAMINATION_AUDIT.md` covers exactly the checkpoint
identified in `NVARC_LINEAGE_AUDIT.md` (Phase 2's single frozen
configuration) against exactly ACQ-001's 160-task, 171-test-index corpus.
It does not re-audit NVARC's contamination against the ARC-AGI-2 evaluation
split — that is already documented in `docs/NVARC_LINEAGE.md` and
`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §3-5 and is restated, not
re-derived, where relevant.
