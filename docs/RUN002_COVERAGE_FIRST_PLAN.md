# RUN-002 coverage-first plan (documentation only — not implemented, not launched)

Addresses `docs/NVARC_SCORE_GAP.md`'s finding directly: RUN-001's ~11pp
aggregate gap versus the ~25% reference is dominated by 43/120 tasks never
being reached at all, not by per-task accuracy collapse (23.4% measured on
the 72 candidate-bearing tasks, close to the ~25% reference). The fix this
implies is architectural — guarantee coverage before spending extra budget
anywhere — not a smarter selector or a bigger model.

This document proposes that architecture. **Nothing here is implemented or
launched.** It is a plan for a future RUN-002, gated on separate approval,
per the explicit instruction this pass operates under.

## Why RUN-001 failed to cover all 120 tasks

`experiments/RUN001/RESULTS.md`: 77/120 reached, 41 of those 77 hit the
per-task guard, 5 reached tasks produced no candidates, 43 never started.
The current 2026 T4x2 notebook spends its budget in task order with a
per-task guard as the only ceiling — a task early in the list can consume a
large fraction of the *global* 11h43m budget before later tasks get any
chance to run at all. There is no mechanism that reserves budget for
"every task gets something" before any task gets "this task gets a lot."

## Proposed architecture: two stages, coverage before depth

### Stage A — coverage floor

- **Every one of the 120 tasks receives a bounded, cheap solver pass before
  any task receives extended budget.** The per-task budget in this stage is
  small and fixed — small enough that 120 x (Stage A budget) fits
  comfortably inside a single 12-hour Kaggle session with margin left for
  Stage B, unlike the current notebook where a handful of slow tasks can
  consume the whole session.
- **No task may consume its extended (Stage B) budget before every task has
  received the Stage A minimum pass.** This is the core ordering constraint
  that RUN-001 lacked. Concretely: the scheduler completes one full pass
  over all 120 task IDs at the Stage A budget before revisiting any task a
  second time.
- **Persist candidates after every task**, not just at the end of a batch or
  the end of the run — RUN-001 already does this at the task level
  (`src/run001/archive.py`'s `flush_task`, one gzip member per task), so
  this requirement is inherited, not new; Stage A's job is to guarantee that
  every task *reaches* a `flush_task` call, which RUN-001's 43 unreached
  tasks never did.
- **Produce fallback attempts even when the primary solver fails.** A task
  that errors, times out with zero candidates, or otherwise fails Stage A
  must still emit *something* into the submission (the competition scores a
  missing attempt as wrong regardless of the reason, so a fallback and a
  proper miss are equally "wrong" but only the fallback path keeps the
  submission well-formed and leaves a diagnostic record instead of an
  absence). Candidate fallback sources, cheapest first: the input grid
  itself (correct for identity-transform tasks, a real minority but nonzero
  per `docs/DATASET_AUDIT.md`'s task-family breakdown), the most common
  training-output color/shape pattern, or (if Stage A produced *any*
  candidate before erroring) whatever partial result exists rather than a
  placeholder.

### Stage B — additional compute

Once Stage A has touched all 120 tasks, remaining budget is allocated by
**transparent, fixed rules — not the confidence model EXP002/EXP002-B found
invalid.** `experiments/EXP002B/RESULTS.md` measured that the current
confidence signal does not reliably separate trustworthy from untrustworthy
candidates at the available sample size; building a stopping/allocation
policy on top of it now would inherit that unresolved uncertainty
silently. Stage B's first version must not do this.

Fixed-rule prioritisation, in order, using only signals RUN-001's own
archive already records (no new instrumentation needed):

1. **Tasks still generating new unique candidates** late into Stage A — a
   directly observable signal (`unique candidate count` still climbing at
   the Stage A cutoff, not plateaued) that more compute is not yet wasted
   on this task.
2. **Tasks with multiple close candidates** — near-ties in the native score
   (`score_kgmon`/`beam_score`, already recorded per candidate) suggest the
   generator found real signal but selection is uncertain, a case where more
   generation (more candidates to break the tie) is plausibly higher-value
   than on a task with one dominant candidate.
3. **Tasks where complementary generation is available** — a second branch
   or generation path (TRM, or this project's own CompressARC corpus once
   `experiments/EXP002C2/` resolves feasibility) that has not yet run on
   this task.
4. **Tasks that did not time out repeatedly** — deprioritise a task that has
   already hit its per-task guard more than once; repeated timeouts on the
   same task are evidence that more of the same budget is unlikely to help
   (a `hit_time_guard` flag RUN-001's summary already records per task).

This ordering is a **fixed priority list, evaluated once after Stage A**,
not a learned or continuously-updated policy — deliberately simple, matching
the instruction that "the first version must use transparent fixed rules."

## Where does CompressARC fit?

Evaluated against the four roles the acceptance message named, using the
cost measurements from `experiments/EXP002C/PILOT_RESULTS.md`,
`experiments/EXP002C2/RESULTS.md`, and `experiments/EXP002C3/RESULTS.md`:

| Role | Verdict | Reasoning |
| --- | --- | --- |
| **Universal cheap first pass** (Stage A solver for all 120 tasks) | **No.** | CompressARC trains a fresh model per task (no shared pretraining/inference batching the way NVARC's single checkpoint does); its measured per-task cost (25-90+ min even truncated at 40 min per `experiments/EXP002C/PILOT_RESULTS.md` §1, worse than the reference RTX 4070's ~20 min/task) is far above what a "cheap" Stage A pass needs, even at C3's best-measured 3x-oversubscribed throughput (`experiments/EXP002C2/RESULTS.md`). EXP002-C3 additionally confirmed the throughput ceiling is GPU-sharing-bound, not a fixable CPU-orchestration inefficiency, so there is no cheap further win to close this gap. NVARC's own reduced-budget inference pass remains the natural Stage A solver. |
| **Complementary generator for a subset** | **Plausible, bounded, cost now settled.** | For the minority of tasks where Stage A+B leave spare budget, or where NVARC's candidate set is thin/uncertain (Stage B rule 2), a CompressARC pass adds a genuinely different candidate distribution. Cost is no longer pending: `experiments/EXP002C2/SCALING_PROJECTION.md` (restated, unrevised, in `experiments/EXP002C3/SCALING_PROJECTION.md`) puts a 170-test-index pass at ~38 Kaggle quota GPU-hours using the frozen C3 configuration — affordable as a bounded, separately-scheduled complementary pass, not as an inline per-task Stage B step (CompressARC's own 40-minute-per-task ceiling is too slow for that). |
| **Fallback for NVARC-unreached tasks** | **Plausible; throughput gain confirmed, no further gain available.** | The 43 never-reached tasks are exactly the coverage gap Stage A is designed to close using NVARC's own reduced-budget pass. `experiments/EXP002C2/RESULTS.md` confirmed C3's ~3x task-count throughput gain (clearing the pre-registered 1.75x bar); `experiments/EXP002C3/RESULTS.md` confirmed that gain is already close to this workload's ceiling on Kaggle 2xT4 (CPU-thread tuning and vCPU-derived concurrency both under-performed plain C3), so C3 is the number any fallback-role cost estimate should use, not a placeholder pending further tuning. |
| **Clean research-corpus source only** | **Confirmed, unchanged.** | This is `experiments/EXP002C/EXP002C2/EXP002C3`'s actual, already-approved use — independent of whether CompressARC ever touches a real competition run. Nothing above changes this; it remains true regardless of RUN-002's eventual design. |

**No role above is implemented by this document.** RUN-002's Stage A solver
is NVARC at a reduced per-task budget unless and until CompressARC's
measured cost (`experiments/EXP002C3/SCALING_PROJECTION.md`) shows it is
competitive for one of the bounded roles above. That cost is now a settled
measurement (C3, ~38 GPU-hours for the 170-test-index floor), not an
open question awaiting further oversubscription or orchestration tuning.

## Explicitly out of scope for this document

- No RUN-002 kernel, notebook, or scheduler code.
- No change to RUN-001's frozen baseline or NVARC's solver code.
- No commitment to CompressARC's role beyond "clean research-corpus source,"
  pending `experiments/EXP002C2/RESULTS.md`.
- No stopping-rule or confidence-based allocator (`paper/CLAIM_LEDGER.md`
  C2/C2-confidence remain PROPOSED/partially-supported; Gate 1 for that work
  has not passed, per `paper/EXPERIMENT_REGISTRY.md`'s harness notes).
