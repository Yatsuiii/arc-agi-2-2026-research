# RUN-001 — PLAN

RUN-001 is **not an experiment**. It is dataset acquisition plus a
competition-baseline capture. It tests no hypothesis and supports no claim on
its own. It is registered so the artifact it produces has a provenance record.

## 1. Identifier

`RUN-001` — NVARC T4x2 baseline execution and candidate archive.

## 2. Purpose

1. Run the current 2026 NVARC T4x2 baseline unmodified.
2. Make no solver improvements.
3. Capture every generated candidate with its metadata.
4. Produce a reusable dataset for later CPU-only verification, ranking and
   compute-allocation studies (theses T1/T2/T3).

## 3. What it is not

- Not evidence of generalisation. The checkpoint was trained on the split this
  run scores (`docs/systems/NVARC.md` §9).
- Not a thesis test. T1/T2/T3 remain unselected.
- Not a leaderboard submission. No auto-submit.

## 4. Baseline

The frozen reference, `BASELINE_SPEC.md`, with exactly the changes in
`INSTRUMENTATION_DIFF.md`: two sanctioned, plus one necessary model-path fix
that is flagged there rather than hidden.

## 5. Split

Interactive mode, so the notebook reads
`arc-agi_evaluation_challenges.json` — 120 tasks, 172 test inputs.
**CONTAMINATED for this checkpoint.**

## 6. Leakage risks

| Risk | Handling |
| --- | --- |
| Checkpoint trained on the eval split | Every accuracy number labelled CONTAMINATED. Absolute values are not usable; relative comparisons over stored candidates are the point. |
| Archiving hidden answers | Statically forbidden and tested. The archive stores predictions only. |
| Notebook self-scoring | The reference prints a local score in interactive mode. Reported as contaminated; not propagated to any claim. |

## 7. Compute budget

One Kaggle run, up to 11 h 40 min on 2x T4, ~40% of a weekly quota. One kernel
version. No duplicate runs.

## 8. Success criteria

1. Kernel completes or hits its own time guard cleanly.
2. `submission.json` exists and satisfies the competition contract.
3. `candidates.jsonl.gz` is readable and joins to the submission.
4. Manifest records commit, environment and asset identities.

## 9. Kill criteria

Stop and document, without substituting a model or altering the solver, on:
inaccessible model asset, dependency install failure, Persona block, GPU
unavailable, OOM, timeout with no usable partial output, archive corruption, or
invalid submission.

## 10. Expected result

Below 27.64%. The T4x2 port has roughly a quarter of the per-task compute that
produced that number and a looser DFS cutoff (0.20 vs 0.07-0.17). A shortfall is
the expected outcome, not a bug.

## 11. What it unblocks

EXP001-B: the ARC-AGI-2 replication of the Stage A headroom analysis, which is
the measurement that decides between T1 and T2.
