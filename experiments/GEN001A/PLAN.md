# GEN001-A — PLAN

NVARC generator restoration, contamination audit, and pilot preflight. A
CPU/local preparation phase only: no GPU is touched, no Kaggle kernel is
launched, no candidate is regenerated. The purpose is to determine whether a
restored NVARC pretrained-prior branch is a valid, and potentially
complementary, generator for the 129 CompressARC generation failures found by
`experiments/EXP002D/RESULTS.md`.

## Why this phase exists

EXP002-D (`fb3e93d`) froze the verdict **FREEZE VERIFIER RESEARCH; GENERATION
IS THE DOMINANT BOTTLENECK**: 129/171 (75.44%) of ACQ-001's clean corpus
test-indices have no correct CompressARC candidate at all, regardless of
selection mechanism. No amount of better ranking can fix a candidate set that
never contained the answer. The only lever left that could move the needle is
a second, independent generator that produces candidates CompressARC does not.
NVARC is the strongest public generator this workspace has already partially
restored (RUN-001) and is therefore the first candidate to test, not because
it is assumed to work, but because it is the cheapest complementarity
hypothesis to falsify.

## Central question

Not "does NVARC alone beat CompressARC's selection." That question is already
contaminated (`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §20) and orthogonal to
what EXP002-D found. The question is:

> Does NVARC generate correct candidates on test-indices where CompressARC
> generated none?

This is a set-complementarity question (candidate oracle union), not a
selection-quality question. Selection accuracy is explicitly secondary in this
phase (Phase 4 below).

## Scope of this phase

CPU/local only. Concretely, this phase:

- reconciles ACQ-001/EXP002-D's apparent count discrepancy (Phase 1);
- documents exactly which NVARC lineage branch RUN-001 restored, with no
  restoration of new checkpoints or branches (Phase 2);
- audits the restored checkpoint for training-data overlap with ACQ-001's
  160-task corpus (Phase 3) — **mandatory before any pilot is built**;
- defines the generator-comparison metrics the eventual GPU pilot will report
  (Phase 4);
- freezes a deterministic 24-test-index pilot sample (Phase 5);
- restores exactly one frozen NVARC configuration as a candidate-exporting
  adapter, compatible with the ACQ-001/RUN-001 archive schema
  (`src/run001/archive.py::CandidateArchive`) (Phase 6);
- validates everything possible without a GPU, using a mocked generator
  (Phase 7);
- projects GPU runtime/quota for the 24-index pilot from RUN-001's own
  measurements (Phase 8);
- builds, but does not launch, a Kaggle 2xT4 pilot kernel package (Phase 9);
- predeclares success/null/ambiguous criteria for that future pilot
  (Phase 10);
- writes the analysis script the pilot's output will be fed into, so no
  analysis choice is made after seeing pilot results (Phase 11);
- writes the strategic decision memo connecting this to the paper's thesis
  (Phase 12).

## What this phase explicitly does not do

Per the acceptance message's execution limits: no Kaggle launch, no GPU
quota consumption, no NVARC inference, no CompressARC rerun, no ACQ-001
modification, no verifier training, no MODEL-001, no restoring or comparing
multiple checkpoints, no hyperparameter tuning, no Kaggle submission, no
RUN-002, no full 171-index NVARC run. The phase stops the moment the pilot
package is fully prepared and locally validated — launch is a separate,
future, explicitly human-gated action (Phase 8's launch condition).

## Corpus and baseline

Frozen inputs, unchanged from EXP002-D:

- `artifacts/ACQ001/merged_corpus_manifest.json` — 160 tasks, 171
  test-indices, 73,147 candidate records, 70,680 unique, 24.56% oracle.
- `artifacts/ACQ001/shard_{a,b}_output/acq001_{a,b}/archive/candidates.{A,B}.jsonl.gz`
  — the frozen CompressARC candidate archives (immutable, read-only in this
  phase).
- CompressARC candidate oracle (C, defined in Phase 4): 24.56%, restated in
  `experiments/GEN001A/BASELINE_SPEC.md`.

## Contamination position, stated up front

`docs/NVARC_LINEAGE.md` already documents that NVARC's SDG training mixture
includes "all 120 ARC-AGI-2 public evaluation tasks, with test-pair
ground-truth outputs, at 6 augmented copies" (`arc2_evaluation6`). Phase 3
extends this specifically to ACQ-001's 160-task corpus, which is drawn from
the ARC-AGI-2 **training** split, not the evaluation split the lineage doc
already flags — a distinct question this plan does not presuppose an answer
to before running the audit.

## Stopping rule

This document, `BASELINE_SPEC.md`, `CONTAMINATION_POLICY.md`, and
`PILOT_PROTOCOL.md` are committed before any NVARC code is inspected for
contamination-audit purposes beyond what is already on disk, and before the
pilot manifest is frozen — matching this project's standing discipline
(preregister before execution) already used for ACQ-001 and EXP002-D.
