# GEN001-A — SUCCESS_CRITERIA

Predeclared before any pilot is launched, per the acceptance message's Phase
10. These thresholds govern how a future pilot's output is read; they are
not adjusted after seeing results.

## Primary

**NVARC solves at least 3 of the 12 preregistered Group-A CompressARC
generation failures** (`PILOT_SAMPLE.md`). Equivalent to >=25% incremental
coverage on Group A (`GENERATOR_COMPARISON.md`'s `|N \ C|` metric restricted
to Group A's 12 test-indices).

## Secondary (all must hold, alongside the primary, for a genuinely
promising result)

- Union oracle exceeds CompressARC's own oracle on the 24-index pilot by
  at least 12.5 absolute percentage points.
- No archive corruption (`read_records` on the pilot archive completes
  without raising past the last complete record).
- No target leakage (`check_no_ground_truth_archived`-style static check,
  `validate_pilot_notebook.py`, plus a runtime check that no candidate
  record's grid was ever compared against ground truth before archiving).
- At least 90% of the 24 indices complete (>=22/24).
- Runtime remains within `QUOTA_PROJECTION.md`'s projected range.
- Candidates are not overwhelmingly duplicates of CompressARC's own
  candidates (Jaccard overlap, `GENERATOR_COMPARISON.md`, should not sit
  near 1.0).
- The improvement is not solely on Group C tasks CompressARC already
  solves (a regression-free result on Group C is necessary but not
  sufficient; the primary criterion is about Group A specifically).

## Strong success

- At least 5/12 Group-A rescues (>=41.7% incremental coverage).
- Meaningful candidate-family complementarity (structural distance between
  NVARC's and CompressARC's candidate populations is non-trivial, not just
  score-magnitude differences on similar grids).
- Projected full-corpus (171-index) cost is feasible within a realistic
  Kaggle quota budget, extrapolated from the pilot's own measured
  cost-per-incremental-solved-index.

## Null result

- 0-1/12 Group-A rescues.
- Candidates are mostly duplicates of CompressARC's own candidate set.
- Runtime excessively exceeds projection (a specific, practically
  disqualifying overrun — not merely "slower than estimated" but enough
  to make a full-corpus run infeasible on any realistic quota).
- No union-oracle improvement over CompressARC's own oracle on the pilot
  subset.

## Ambiguous

- Exactly 2/12 Group-A rescues.
- Strong task-family concentration (all rescues land in one
  `size_relation` family, making generalisation to the other 129
  generation-failure indices uncertain).
- Incomplete execution (<90% of the 24 indices complete).
- Contamination (already established, `CONTAMINATION_AUDIT.md`) prevents
  scientific interpretation of any accuracy number, even where the
  set-complementarity signal itself remains readable.

## How contamination interacts with these criteria

`CONTAMINATION_AUDIT.md` already classifies the checkpoint
SCIENTIFICALLY CONTAMINATED for this exact corpus. That classification does
not zero out these criteria — a contaminated checkpoint that fails to
rescue any Group-A test-index is still informative (contamination alone
did not manufacture success), and a contaminated checkpoint that does
rescue several is a competition-engineering signal worth pursuing, just
never a clean paper claim (`CONTAMINATION_POLICY.md`'s consequences,
restated). Every verdict this phase's future pilot produces carries the
contamination label regardless of which bucket above it lands in.
