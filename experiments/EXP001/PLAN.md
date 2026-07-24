# EXP001 — PLAN (preregistration)

Preregistered before execution. Not edited after the run; deviations go in
`RESULT.md`.

## 1. Experiment identifier

`EXP001` — Selection headroom and compute headroom from recorded solver traces.

## 2. Research question

Of the tasks a solver fails, how many does it fail because the correct answer was
never produced, versus because the correct answer was produced and not chosen?
And under a fixed total budget, how much accuracy is recoverable by reallocating
compute across tasks rather than spending it uniformly?

These are the two premises that theses T2 and T1 respectively depend on
(`docs/CANDIDATE_RESEARCH_THESES.md`). Both are settled by the same analysis of
the same artifact.

## 3. Falsifiable hypotheses

**H1 (selection headroom).** For a real ARC solver, the number of tasks whose
correct answer appears anywhere in the candidate set exceeds the number ranked
into the top 2 by a margin of **at least 5% of tasks**.

**H2 (compute headroom).** Under a total budget equal to what uniform allocation
consumes, an oracle allocator that knows each task's required budget solves at
least **3% more tasks** than uniform allocation.

**H0 (pipeline).** The analysis pipeline reproduces the reference
implementation's published per-task outcomes exactly. This is a precondition; if
it fails, H1 and H2 results are not trustworthy.

Each hypothesis is falsified by the measurement falling below its threshold.
Thresholds are set at the point where, on 120 evaluation tasks, the effect would
be too small to distinguish from decoder non-determinism (`nvarc_2025.pdf` §3.5
reports 1-2 points of run-to-run variability).

## 4. Theoretical motivation

A solver that emits k candidates and reports 2 has two independent failure
modes, and they call for opposite interventions: generation failures need a
better model or more search, selection failures need a better ranker. The field
has never separated them on ARC-AGI-2. NVARC §4.4 is the only public evidence
and it describes 2-3 tasks in one sentence.

Similarly, uniform compute allocation is optimal only if the marginal return of
compute is equal across tasks. If difficulty is near-binary — solved almost
immediately or never — the oracle gain is near zero and routing is not worth
pursuing. That is a real possibility and it is cheap to check.

## 5. Relationship to prior work

- NVARC `nvarc_2025.pdf` §4.4: correct candidates from TRM "were not always
  picked by Qwen3 scoring". Qualitative, n≈2-3.
- ARChitects `page.md`: 30.5% with known output shape versus 21.67% realised —
  a decomposition of failure, but into generation sub-modes, not into
  generation-versus-selection.
- CompressARC `list_solved_puzzles.py`: computes exactly the rank of the true
  solution at any step budget, and the authors' recorded traces ship with the
  repository. They report accuracy curves but never a selection-headroom or
  budget-reallocation analysis.
- No published ARC-AGI-2 compute-versus-accuracy curve exists.

## 6. Exact baseline

**Stage A (this task, executable now).** CompressARC's own recorded results:
`references/paper_winners/03_compressarc/results_for_the_blog_post/predictions_{training,evaluation}.npz`,
shape `(400, 2000, 2, 2)` — for each of 400 ARC-AGI-1 tasks, at each of 2000
optimisation steps, the hash and score of two logged candidates. Ground truth
from `references/paper_winners/03_compressarc/dataset/`. MIT licensed, CPU only.

Baseline = accuracy@2 at the full 2000-step budget, which is what the paper
reports (20% evaluation, 34.75% training).

**Stage B (blocked on RUN-001).** The primary baseline's persisted candidate
records from `docs/BASELINE_SELECTION.md` RUN-001, on the 120-task ARC-AGI-2
evaluation split.

## 7. Exact intervention

None. This is an observational analysis. Three quantities are computed from
recorded traces:

- `oracle@k(b)` — fraction of tasks where the true solution is within the top k
  ranked candidates at step budget b.
- `realised@2(b)` — fraction where it is within the top 2. The solver's actual
  score.
- `oracle_alloc(B)` — under total budget B, the maximum number of tasks solvable
  by choosing a per-task budget with foreknowledge, solved as a knapsack over
  each task's minimum sufficient budget.

`oracle@k - realised@2` is the selection headroom. `oracle_alloc(B) -
realised@2(B/n)` is the compute headroom.

## 8. Training split

None. No model is fitted in EXP001.

## 9. Validation split

Stage A: ARC-AGI-1 **training** split (400 tasks) is used for pipeline
verification and for reading the shape of the curves.

## 10. Held-out evaluation split

Stage A: ARC-AGI-1 **evaluation** split (400 tasks), analysed once, after the
training-split analysis is complete and the code is frozen.

Stage B: ARC-AGI-2 Kaggle evaluation (120 tasks), reported as **CONTAMINATED**
for the primary baseline per `docs/DATASET_AUDIT.md` §6.1. Relative quantities
(oracle minus realised) are affected far less than absolute ones, because
contamination shifts both terms, and that is precisely why this experiment is
built on a difference rather than a level.

## 11. Leakage risks

| Risk | Assessment |
| --- | --- |
| Fitting anything to the evaluation split | **none** — no model is fitted |
| Reusing CompressARC's recorded runs | **none** — CompressARC has no pretraining and no training set, so it cannot have seen any task |
| Stage B checkpoint contamination | **real and known**; mitigated by reporting differences and by labelling every absolute number |
| Analysis-code overfitting (repeatedly rerunning until the number looks good) | mitigated by freezing the code after the ARC-AGI-1 training split and touching the evaluation split once |
| ARC-AGI-1 versus ARC-AGI-2 conflation | Stage A is ARC-AGI-1 and says so everywhere; it establishes the method and the shape of the curves, not the ARC-AGI-2 numbers |

## 12. Compute budget

Stage A: **CPU only, under one minute, zero GPU, zero network.**
Stage B: no compute of its own; consumes RUN-001's output.

## 13. Success criterion

- H0: per-task solved/unsolved at 2000 steps reproduces the published counts for
  both splits (20% evaluation, 34.75% training) exactly.
- H1: `oracle@k - realised@2 >= 5%` of tasks for some k ≤ 10.
- H2: `oracle_alloc - uniform >= 3%` of tasks at matched total budget.

## 14. Kill criterion

- H0 fails → stop; the artifact is not what we think it is, and nothing
  downstream is valid.
- H1 < 5% on both ARC-AGI-1 splits **and** on Stage B → thesis T2 is killed.
- H2 < 3% on both ARC-AGI-1 splits **and** on Stage B → thesis T1 is killed.

If both are killed, T3 becomes the thesis by elimination, and the negative result
is itself the first paper contribution.

## 15. Intended paper claim

Supports `paper/CLAIM_LEDGER.md` C1 (complementarity/headroom exists), C2
(selection is a bottleneck distinct from generation), C3 (compute reallocation
has headroom). Provides figures F4 (oracle@k vs realised) and F5
(compute-vs-accuracy, uniform vs oracle).

## 16. Possible negative interpretation

The most likely negative outcome is that ARC difficulty is near-binary: a task is
either solved in the first few candidates and the first fraction of the budget,
or never solved at any k or any budget. In that case both headrooms are near
zero, both T1 and T2 die, and the honest conclusion is that **generation, not
selection or allocation, is the entire bottleneck on ARC-AGI-2.**

That would be a clean, quantified, publishable negative result — and it is
recorded here *before* the measurement so it cannot later be reframed as
something we always suspected.

A weaker negative: headroom exists on ARC-AGI-1 (CompressARC) but not on
ARC-AGI-2, which would say the two benchmarks differ in kind and not only in
difficulty. Also worth reporting.

---

## Execution

Stage A only, in this task, because it is CPU-only, needs no downloads, and its
purpose is to verify the analysis pipeline before any GPU quota is spent.

```
python -m src.analysis.headroom
```

Stage B is **not** executed and must not be until RUN-001 is approved and run.
