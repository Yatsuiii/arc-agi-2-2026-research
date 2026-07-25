# EXP002-C — PLAN (preregistration)

Preregistered before any acquisition run. Directly executes the recommendation
`experiments/EXP002B/CORPUS_REQUIREMENTS.md` made but did not carry out.

## 1. Experiment identifier

`EXP002-C` — Clean ARC-AGI-2 candidate-corpus acquisition using CompressARC.

## 2. Research question

Can a legally clean, sufficiently large candidate corpus be produced so that
EXP002-B's V0-vs-V2 comparison — currently acquisition-bound, not decided,
because every bootstrap CI at n=18/94 overlaps every other
(`experiments/EXP002B/RESULTS.md`) — becomes statistically decidable?

This is an acquisition experiment, not a verifier experiment: the hypotheses
below are about whether the corpus can be produced at the required scale and
cleanliness, not about V0/V1/V2/V3 accuracy, which is EXP002-D's question once
this corpus exists.

## 3. Falsifiable hypotheses

**H0 (pipeline).** The vendored, instrumented CompressARC
(`third_party/compressarc/`, `src/run002c/solve_task_cli.py`) reproduces
upstream's published ARC-AGI-1 accuracy exactly when run against the existing
`references/paper_winners/03_compressarc/dataset/` files, proving the
instrumentation (`solution_grids` persistence) did not change training or
selection behaviour. Precondition; failure stops everything below.

**H1 (yield).** Running CompressARC against a family-stratified sample of
ARC-AGI-2 training tasks (`src/run002c/sample_tasks.py`) produces at least 500
test-indices with a non-trivial candidate set (>=2 unique grids), split so
Fold C alone has >=100 — `CORPUS_REQUIREMENTS.md`'s pre-registered minimum. A
CompressARC run that mostly produces singleton or empty candidate sets on
ARC-AGI-2 (plausible: the paper never reports ARC-AGI-2 numbers,
`docs/papers/COMPRESSARC_ANALYSIS.md` §6) fails H1, which is itself a finding,
not a bug to route around.

**H2 (structural feature availability).** For >=90% of produced test-indices,
`src/harness/features/structural.py` computes every one of
`features.independence.INDEPENDENT_FEATURES` without raising or returning
`None` for the whole set — checking that the grid-persistence instrumentation
actually closes the gap `CORPUS_REQUIREMENTS.md` option A identified (hash-only
archives cannot feed structural features at all).

## 4. Theoretical motivation

EXP002-B's own verdict was not "V2 fails," it was "the corpus cannot decide
either way" (`experiments/EXP002B/RESULTS.md` verdict section). The single
lever available to resolve that without touching NVARC, without building an
allocator, and without a new licence review is more clean data from a solver
already cleared for this project's use
(`docs/REFERENCE_LICENSE_AUDIT.md` §8, MIT, zero pretraining, zero
contamination risk by construction). This experiment is that lever, executed.

## 5. Relationship to prior work

Direct continuation of `experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s
recommendation. Reuses `src/analysis/exp002_verifier_eval.py`'s fold-assignment
code (`FOLD_SEED`, `load_family_flags`, `assign_folds`) rather than
re-deriving it, so EXP002-C's folds are drawn by the identical, already-tested
procedure as EXP002/EXP002-B's folds over the evaluation split.

## 6. Exact baseline

None — this is acquisition, not an evaluation against a baseline. The
"baseline" role EXP001/EXP002 usually name is filled here by upstream
CompressARC's own published ARC-AGI-1 numbers, which H0 checks.

## 7. Exact intervention

1. Vendor CompressARC into `third_party/compressarc/` (done this pass, MIT
   notice retained, `third_party/compressarc/NOTICE.md`).
2. Instrument `solution_selection.Logger` to persist `hash -> grid`
   (`solution_grids`), the one behavioural change from upstream, verified by
   H0 to be accuracy-neutral.
3. Sample ARC-AGI-2 training tasks, family-stratified
   (`src/run002c/sample_tasks.py`), size TBD by H1's yield check — see §12.
4. Run CompressARC per sampled task (`src/run002c/solve_task_cli.py`, one
   subprocess per task, 2000 iterations or a wall-clock cap, whichever comes
   first per task).
5. Archive results in RUN-001's own schema (`src.run001.archive.CandidateArchive`,
   `src/run002c/acquire_corpus.py`) so downstream tooling needs a path change
   only.

## 8. Training split

Not applicable in the ML sense — CompressARC trains one model per task from
that task's own demonstration pairs, with no cross-task training data. The
"training split" here is procedural: ARC-AGI-2's own `training` split
(`benchmark/ARC-AGI-2/data/training/`, 1000 tasks;
`competition_2026/extracted/arc-agi_training_challenges.json`, same 1000 in
the CompressARC-compatible challenge/solution JSON shape verified this pass).

## 9. Validation split

Fold B of the sampled tasks (`assign_folds`'s stratified 60/20/20, same seed
`20260725` as EXP002/EXP002-B), used the same way — verifier calibration in
EXP002-D, not touched by this acquisition pass.

## 10. Held-out evaluation split

Fold C of the sampled tasks — the fold EXP002-D's V0-vs-V2 comparison will
report on, sized to >=100 test-indices per H1.

## 11. Leakage risks

- **Solver contamination: none by construction.** CompressARC has no
  pretraining phase, so there is no checkpoint to have seen any task, training
  or evaluation (`docs/REFERENCE_LICENSE_AUDIT.md` §8). This is the entire
  reason this route was chosen over re-running NVARC
  (`CORPUS_REQUIREMENTS.md`, option C, rejected for exactly this).
- **Fold leakage.** Training and evaluation are ARC-AGI-2's own disjoint
  splits; sampling only from `training` means nothing here can leak into or
  contaminate the 120-task evaluation corpus RUN-001/EXP002/EXP002-B already
  used, and vice versa — these are two entirely separate corpora, never
  merged.
- **Near-duplicate tasks across the sampled set's own folds.** Not yet
  checked — `docs/DATASET_AUDIT.md` §3's canonical-duplicate detector is not
  wired into `sample_tasks.py`. Recorded as a known gap, same as
  `CORPUS_REQUIREMENTS.md` option D flagged for EXP002/EXP002-B's folds. If
  H1's yield lands close to the 500/100 minimum, this gap should be closed
  before EXP002-D trusts Fold C; if yield lands well above minimum, it can be
  addressed by simply dropping flagged duplicates rather than re-sampling.

## 12. Compute budget

**Not spent by this pass.** `paper/COMPUTE_LEDGER.md`'s reference figure is
~20 minutes/task on one RTX 4070. This machine's GPU, freshly verified this
pass, is an RTX 4050 Laptop GPU with 6 GB VRAM (`nvidia-smi`) — weaker than
the reference card, and CUDA/`torch` are not currently installed
(`experiments/EXP002C/FEASIBILITY.md` has the full readout). Sample size and
wall-clock estimate are therefore provisional until a timed pilot batch (5-10
tasks) is run and measured on this hardware; scaling the reference 20 min/task
figure by an assumed 1.3-1.8x slowdown for the weaker card puts 500 tasks at
roughly **220-300 GPU-hours serially**, which is not a "long GPU run" in the
sense of one 12-hour Kaggle session — it is far longer, and would need either
many sessions, a smaller sample than 500 test-indices, or parallelism this
6 GB card cannot support (`parallel_train.py`'s whole design point). This
number is the central input the approval decision in §16 needs.

## 13. Success criterion

H0 passes exactly (bit-for-bit reproduction of upstream ARC-AGI-1 numbers).
H1's yield reaches the 500/100 minimum, or a smaller number is explicitly
accepted as an interim target with the corresponding power loss stated
plainly (per `CORPUS_REQUIREMENTS.md`'s own "not a formal power analysis"
caveat). H2 clears 90% structural-feature coverage.

## 14. Kill criterion

KILLED if H0 fails (instrumentation changed solver behaviour — must be fixed
before any of the rest is trustworthy). Interim/ABANDONED-with-reason if a
timed pilot shows the wall-clock cost in §12 is not payable within the
project's remaining 100-day budget (`paper/COMPUTE_LEDGER.md`'s calendar
table) even at a reduced sample size — in which case the honest conclusion is
that thesis T2's decisive experiment is not testable before the deadline on
this hardware, which is itself a result for `paper/CLAIM_LEDGER.md`.

## 15. Intended paper claim

Acquisition only; produces the corpus `paper/CLAIM_LEDGER.md` C2 needs to move
past "NOT YET SHOWN," not the claim itself. No verifier-accuracy or
calibration claim is made from this experiment.

## 16. Possible negative interpretation

Most likely outcome given §12's numbers: full 500/100 acquisition at 2000
iterations/task is not payable on this hardware within a reasonable
wall-clock budget, and either the iteration count must be reduced (with a
documented accuracy cost, since CompressARC's own accuracy curve is a function
of step count) or the sample size must be reduced below the pre-registered
minimum (with the corresponding power loss stated, not hidden). Either
degrades EXP002-D's eventual power, and that degradation must be reported
alongside EXP002-D's results, not discovered after the fact.

---

## Execution

**Gated. Not run by this pass.** Per the user's explicit instruction ("do not
launch a long GPU run without approval") and this project's own rule that
approval for a run is separate from approval for its preregistration
(`paper/EXPERIMENT_REGISTRY.md` rule 1), this file, the vendored/instrumented
CompressARC code, and the `src/run002c/` driver are committed as preparation.
The commands below are the exact intended execution, not yet invoked:

```
# 0. environment (not yet done — see FEASIBILITY.md)
pip install torch --index-url ...

# 1. pipeline check (H0) — CPU-comparable, reuses existing reference traces
python -m src.analysis.headroom

# 2. timed pilot (5-10 tasks) to replace the estimate in §12 with a measurement
python -m src.run002c.sample_tasks --n-tasks 8 --out artifacts/EXP002C/pilot_sample.json
python -m src.run002c.acquire_corpus --sample artifacts/EXP002C/pilot_sample.json \
    --run-dir artifacts/EXP002C/pilot_run --device cuda

# 3. full acquisition, size set by the pilot's measured cost against the
#    remaining compute budget — not run until 2 returns a number and a human
#    approves the resulting wall-clock estimate
```
