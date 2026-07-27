# GEN002-A — PLAN

Clean, CPU-only, typed object-centric program-synthesis generator, evaluated
on the same frozen 24-index pilot GEN001-A already built for the (currently
quota-blocked) NVARC pilot. A real bounded pilot, not infrastructure
preparation alone.

## Why this phase exists

EXP002-D (`fb3e93d`, other worktree) froze verifier research: 75.44% of
ACQ-001's clean corpus is a generation failure, not a selection failure.
GEN001-A prepared a complementary-generator test using a pretrained NVARC
checkpoint, but that checkpoint is contaminated against this exact corpus
(`experiments/GEN001A/CONTAMINATION_AUDIT.md`, read-only from this
worktree) and its pilot cannot launch for ~5 days (Kaggle quota).
GEN002-A tests the same complementarity hypothesis with a generator that
has **no pretrained-checkpoint contamination risk at all** — a typed
program synthesizer that only ever sees the demonstration pairs it is
asked to solve, searches a hand-specified DSL, and requires an *exact*
match on every visible training pair before it emits a test candidate.
Contamination is structurally impossible here, not merely audited and
labelled: there is no training corpus to contaminate.

## Central question

> Can typed object-centric program synthesis generate correct outputs for
> CompressARC generation failures without pretrained-checkpoint
> contamination?

Same shape as GEN001-A's question (set-complementarity against the 129
CompressARC generation failures), different generator family. Selection
accuracy is secondary here for the same reason it was secondary in
GEN001-A (`experiments/GEN001A/GENERATOR_COMPARISON.md`) — a candidate
that exists but is not the program search's own top pick is still a
harness-level win once a union candidate pool exists (Phase 9).

## Corpus

Identical 24-index pilot GEN001-A froze
(`artifacts/GEN001A/pilot_manifest.json`, read-only from this worktree):
12 Group-A CompressARC generation failures, 6 Group-B selection failures,
6 Group-C native successes. Not re-derived, not re-stratified — reusing
the exact same frozen sample makes GEN001-A's and GEN002-A's results
directly comparable once both exist, which is the entire point of Phase
10's decision matrix.

## Scope of this phase

CPU/local only, real execution (not merely preparation, per the
acceptance message's explicit framing):

- audits which program-search concepts are legally reimplementable from
  local references (Phase 1);
- implements deterministic grid/object/scene-graph representations
  (Phase 2);
- implements a minimal typed DSL (Phase 3);
- implements two frozen search policies, enumerative and constraint-guided
  best-first (Phase 4);
- enforces demonstration-exactness before any test candidate is emitted
  (Phase 5);
- runs both policies on the frozen 24-index pilot, CPU-only (Phase 6);
- computes offline oracle/union metrics only after generation completes
  (Phase 7);
- classifies every unsuccessful pilot task into missing-language /
  search-failure / generalization-failure (Phase 8);
- builds a generator-neutral candidate-union interface, schema only, no
  new learned selector (Phase 9);
- predeclares the post-both-pilots decision matrix (Phase 10).

## What this phase explicitly does not do

No Kaggle, no cloud GPU, no paid API, no GEN001-A modification, no
CompressARC rerun, no verifier training, no confidence routing, no
modification of the frozen 24-index sample, no primitive added after
viewing pilot correctness, no tuning against test outputs, no full
171-index search, no leaderboard submission. Stops after the pilot and its
analysis are complete.

## Timeout deviation, stated up front

The acceptance message's "recommended initial ceiling" (5 CPU-min/task S0,
15 CPU-min/task S1) totals up to 8 CPU-hours across 24 tasks per policy.
This phase uses much shorter per-task ceilings (`SEARCH_PROTOCOL.md`) —
a state-budget cap is the binding constraint in practice, not wall-clock,
because this DSL's branching factor at shallow depth is small enough that
either the exact program is found in seconds or the state budget exhausts
before minutes pass. This is a resource-conscious deviation, declared here
before any search runs, not discovered and rationalized after the fact.

## Stopping rule

This document and `BASELINE_SPEC.md`, `DSL_SPEC.md`, `SEARCH_PROTOCOL.md`,
`LEAKAGE_POLICY.md` are committed before any DSL primitive or search
algorithm is implemented, matching this project's standing
preregister-before-execution discipline.
