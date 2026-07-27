# DATA001-B — BASELINE_SPEC

## Frozen DATA001-A result

- 6140 generation attempts
- 6000 accepted tasks
  - 4316 TRAIN
  - 1684 VALIDATION
- 140 rejected
  - 127 trivial constant-output
  - 13 identity
- 0 exact overlaps admitted
- 0 structural overlaps admitted
- 0 quarantined reference collisions
- 11 accepted transformation families
- effective depth distribution
  - depth 1: 5124
  - depth 2: 876

## Why DATA001-A failed

The failure was not cleanliness or tooling. DATA001-A passed:

- clean-room provenance;
- exact and structural leakage checks;
- deterministic serialization;
- local training-harness validation;
- operational feasibility for a bounded 4B-class future pilot.

It failed because coverage was too shallow:

- ARC TRAIN weighted descriptor coverage: `0.145`
- ACQ-001 weighted descriptor coverage: `0.087`
- CompressARC-failure weighted descriptor coverage: `0.047`
- CompressARC-failure mean nearest-structure distance: `1.977`

The main missing regions were:

- large grids, especially `145+` cells;
- `7+` colour tasks;
- `7+` object tasks;
- dense multi-object layouts;
- shape-preserving multi-object transformations;
- large output expansions;
- relational and correspondence-heavy structure.

## DATA001-B design response

DATA001-B does not replace the architecture. It retargets the
distribution:

1. richer structural descriptors;
2. harder scene modes;
3. broader general transformation families;
4. nontrivial depth balancing;
5. token-budget-aware corpus selection instead of "accept every valid
   task."
