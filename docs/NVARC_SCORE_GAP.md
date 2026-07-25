# NVARC score gap: ~24-25% reference versus RUN-001's 14.0%

Explains the apparent collapse between NVARC's published/reference local
number and RUN-001's local baseline, before any further acquisition work
proceeds. Written because a reader who sees "14.0%" next to "24-27%" without
this decomposition would reasonably conclude the solver itself got much
worse on this hardware — the actual picture is dominated by coverage, not
accuracy.

## The two numbers being compared

| | Value | Source |
| --- | --- | --- |
| NVARC contaminated local number, this exact checkpoint | 30/120 = **25.0%** | `nvarc_2025.pdf` Table 2, `docs/DATASET_AUDIT.md` line 49, full 12h on 4xL4 |
| NVARC 2025 public-leaderboard range (different systems/checkpoints, not this exact local number) | ~24-27.6% during competition, ~29.7% shortly after | `paper/CLAIM_LEDGER.md` B1, `nvarc_2025.pdf` abstract, §3.5, Table 2 |
| RUN-001, this project's own T4x2 port | **14.0%** aggregate over 120 tasks | `experiments/RUN001/RESULTS.md` |

The project's own records do not contain a literal "24.03%" figure; the
closest documented analog is NVARC's own contaminated local number for this
checkpoint, 30/120 = 25.0%, and that is the comparison used throughout this
document. Nothing below depends on the exact decimal — the decomposition is
the same whichever reference figure in the 24-27% range is used.

## The decomposition

RUN-001 measured, exactly (`experiments/RUN001/RESULTS.md` "Headline" and
"Score" tables):

| Quantity | Value |
| --- | --- |
| Tasks reached before the 11h43m budget drained | 77 / 120 |
| Tasks that produced candidates | 72 / 120 |
| Tasks reached but produced no candidates (timed out mid-task) | 5 |
| Tasks never reached at all (budget exhausted first) | 43 |
| Accuracy over the 72 candidate-bearing tasks | 16.8 / 72 = **23.4%** |
| Accuracy over the full 120-task split (43 unreached score 0) | 16.83 / 120 = **14.0%** |

The arithmetic check the acceptance message asked for holds almost exactly:
23.4% x (72/120) = 23.4% x 0.60 = **14.04%**, against the measured 14.0% (the
small residual is the 5 reached-but-candidateless tasks, which also score 0
and are folded into the 120-task denominator but not the 72-task one).

**This single fact — 23.4% on the tasks the solver actually got to run on,
versus 14.0% once the 43 never-reached tasks are folded in at 0% — is almost
the entire gap.** 23.4% is itself close to the ~25% contaminated reference
figure (both numbers describe "accuracy given the solver actually ran"); the
remaining ~1.6pp gap between 23.4% and 25.0% is real solver-accuracy
variation (see §5), an order of magnitude smaller than the ~11pp coverage
effect.

## Five distinct failure axes, kept separate

### 1. Solver accuracy, conditional on candidate generation

**23.4% (72 tasks) vs. the ~25.0% reference.** This is the only axis that is
actually about solver quality in the "did it get the puzzle right" sense,
and it is close to the reference number, not collapsed. The residual ~1.6pp
gap is plausibly explained by axis 5 below (branch/quantisation/compute
differences within a comparable-coverage regime), not investigated further
here because it is small relative to the coverage effect.

### 2. Task coverage

**77/120 tasks reached, 43 never started.** This is a scheduling/global-budget
fact, not a per-task solver-quality fact: a task in the unreached 43 was never
given a chance to succeed or fail, it simply never ran. This is the single
largest contributor to the aggregate gap (11h43m budget on 2xT4 could not
reach the full 120-task list at the per-task compute this notebook spends).

### 3. Candidate-generation failure (within reached tasks)

**5 of the 77 reached tasks produced no candidates at all** before their
per-task guard fired (`experiments/RUN001/RESULTS.md` "Coverage" row, "41/77
hit the per-task guard" — a large fraction of reached tasks ran close to or
into their own per-task budget wall, and 5 of them never got far enough to
emit even one candidate). This is a distinct failure mode from coverage
(axis 2): the task *was* reached, and still produced nothing.

### 4. Selector failure (within candidate-bearing tasks)

Separate from both of the above and already the subject of EXP002/EXP002-B:
of the 72 tasks that did produce candidates, the oracle (correct answer
present *somewhere* in the candidate set) rate was 31.9% versus the realised
selected rate of 24.5% (`experiments/RUN001/RESULTS.md` "Selection ablation"
section) — a **7.4pp selection gap** on top of whatever generation achieved.
This is the axis `experiments/EXP002B/RESULTS.md` investigated directly and
found inconclusive at the current sample size (every V0-vs-V2 bootstrap CI
overlaps). Not re-litigated here; noted only to keep it distinct from axes
2-3, which are upstream of selection entirely.

### 5. Compute, branch, quantisation, and evaluation-setting differences

Even within reached, candidate-bearing tasks, RUN-001 is not running the same
configuration as the reference numbers:

- **Branch.** The 2026 T4x2 notebook is a **constrained branch-1-only** port
  (Qwen3-4B path only); the TRM branch that NVARC's fuller configuration also
  runs is not exercised (`docs/systems/NVARC.md`, `paper/COMPUTE_LEDGER.md`
  reference-system table lists the TRM branch as a separate row with its own
  hardware/time).
- **Quantisation.** The T4x2 port runs 4-bit, versus the reference
  configuration's higher-precision path — a real compute/accuracy tradeoff
  made specifically to fit T4's smaller VRAM and older tensor cores
  (`experiments/RUN001/ACCESS_REPORT.md` measured environment: `unsloth`,
  `bitsandbytes` in the pinned image, both 4-bit-quantisation-oriented
  libraries).
- **Compute per task.** `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §11 (cited
  directly by `experiments/RUN001/RESULTS.md`) documents that the T4 port
  runs "roughly a quarter of the per-task compute and a looser DFS cutoff"
  relative to the stronger reference configuration.
- **Hardware.** 2x T4 (sm75, `paper/COMPUTE_LEDGER.md`) versus the reference
  configuration's 4x L4 or 8xH100-class hardware depending on which reference
  row is compared (`paper/COMPUTE_LEDGER.md` reference-system table).
- **Evaluation setting.** The ~25% reference figure is itself a *local*,
  *contaminated* number for this same checkpoint on the same 120-task split
  (not a rerun-mode/semi-private leaderboard score); RUN-001's 14.0%/23.4%
  are the same category of number (local, contaminated,
  `experiments/RUN001/RESULTS.md`'s own explicit warning), so this axis is
  not an additional confound *between* the two numbers being compared here —
  both are equally local/contaminated — but it does mean **neither number
  should be read as a leaderboard estimate** (`paper/CLAIM_LEDGER.md` A1).

## What this does and does not establish

**Does establish:** the ~11pp aggregate gap is overwhelmingly a throughput
and coverage story (axis 2, with axis 3 as a smaller contributor), not a
per-task solver-accuracy collapse (axis 1 shows only a ~1.6pp gap, plausibly
attributable to axis 5's branch/quantisation/compute differences).

**Does not establish:** that reaching full 120-task coverage would
automatically recover the full ~25% reference figure. Coverage and
throughput are currently the dominant aggregate-score loss *given the
tasks reached score close to the reference rate* — but the 43 never-reached
tasks are not a random sample of the 120; they could be systematically
easier or harder than the 77 that were reached (task ordering, difficulty
correlation with position in the run, or budget-guard interaction are all
unmeasured). No claim is made about their expected accuracy. This is exactly
why `docs/RUN002_COVERAGE_FIRST_PLAN.md` proposes a coverage floor rather
than assuming coverage alone solves the gap.

## Relevance to EXP002-C2

This document exists because oversubscription/throughput work
(`experiments/EXP002C2/`) is motivated by the same underlying fact this
decomposition makes precise: **the dominant lever available right now is
running more tasks to completion, not making per-task selection or
generation smarter.** EXP002-C2's CompressARC-corpus-acquisition throughput
question and `docs/RUN002_COVERAGE_FIRST_PLAN.md`'s NVARC-coverage-floor
question are two applications of the same diagnosis to two different
systems.
