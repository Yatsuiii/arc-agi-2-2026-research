# EXP001 — RESULT (Stage A)

Stage A only. Stage B is blocked on RUN-001 and has not been run.

## 1. Commit SHA

Analysis code committed alongside this file. The preregistration
(`experiments/EXP001/PLAN.md`) was committed at `9230ca9`, before any
measurement.

## 2. Exact configuration

- Source: `references/paper_winners/03_compressarc/results_for_the_blog_post/predictions_{training,evaluation}.npz`
  @ repo commit `83a22218024d46273eb32b769a906340202ffb4d`, MIT.
- Ground truth: `references/paper_winners/03_compressarc/dataset/arc-agi_*_solutions.json`
  (ARC Prize 2024 bundle, ARC-AGI-1, 400 tasks per split).
- Budget grid: 50, 100, 200, 400, 800, 1200, 1600, 2000 optimisation steps.
- k values: 1, 2, 3, 5, 10, 20, any.
- Hash comparison after `>> 16`, log-sum-exp score accumulation — both matching
  `list_solved_puzzles.py`.

## 3. Exact command

```
python -m src.analysis.headroom
```

## 4. Random seeds

None. The analysis is deterministic. CPython hashes integer tuples
deterministically, so `PYTHONHASHSEED` does not affect the result — verified by
H0 reproducing the published counts exactly.

## 5. Runtime

19.8 s wall-clock.

## 6. Hardware

Local CPU. **Zero GPU, zero network, zero downloads.**

## 7. Results

### H0 — pipeline verification: **PASSED EXACTLY**

| Split | Our `realised@2` | CompressARC published |
| --- | --- | --- |
| ARC-AGI-1 training | 139 / 400 = **34.75%** | 34.75% |
| ARC-AGI-1 evaluation | 80 / 400 = **20.00%** | 20% |

Exact reproduction of both published figures from the raw traces. The analysis
pipeline is trustworthy.

### H1 — selection headroom: **PASSED, by a wide margin**

| | training | evaluation |
| --- | --- | --- |
| realised@2 | 139 (34.75%) | 80 (20.00%) |
| oracle@1 | 121 (30.25%) | 74 (18.50%) |
| oracle@2 | 139 (34.75%) | 80 (20.00%) |
| oracle@3 | 146 (36.50%) | 88 (22.00%) |
| oracle@5 | 153 (38.25%) | 97 (24.25%) |
| oracle@10 | 166 (41.50%) | 104 (26.00%) |
| oracle@20 | 175 (43.75%) | 115 (28.75%) |
| **oracle@any** | **212 (53.00%)** | **137 (34.25%)** |
| **headroom (oracle@any − realised@2)** | **73 tasks, 18.25pp** | **57 tasks, 14.25pp** |

Threshold was 5pp. Measured 14.25pp on the held-out split.

The correct answer is **generated for 71% more evaluation tasks than are
reported** (137 vs 80). Even restricting to the top 10, oracle@10 exceeds
realised@2 by 24 tasks — a 30% relative improvement available purely from
ranking, with no change to the solver.

### H2 — compute headroom: **PASSED, by a wide margin**

Tasks solved at top-2, uniform allocation versus an oracle allocator held to the
same total budget (budget x 400 steps):

| per-task budget | training uniform | training oracle | evaluation uniform | evaluation oracle |
| --- | --- | --- | --- | --- |
| 50 | 4 | **82** | 3 | **60** |
| 100 | 10 | **119** | 6 | **82** |
| 200 | 59 | **148** | 25 | **90** |
| 400 | 106 | 148 | 57 | **90** |
| 800 | 133 | 148 | 76 | **90** |
| 1200 | 138 | 148 | 84 | 90 |
| 1600 | 143 | 148 | 90 | 90 |
| 2000 | 148 | 148 | 90 | 90 |

Threshold was 3pp. Measured 16.25pp on the evaluation split at budget 200
(25 → 90).

Restated as compute rather than accuracy: **the oracle allocator reaches the
full-budget accuracy at a per-task budget of 200 steps, where uniform allocation
needs 1600.** That is an 8x compute reduction for identical accuracy, on the
held-out split.

The mechanism is visible in the histogram: most solvable tasks are solved very
early, and the uniform allocator spends most of its budget on tasks that will
never be solved. `never_solved` = 252 / 400 training, 310 / 400 evaluation.

### Unplanned finding: solved, then lost

| Split | solved@2 at *some* budget | solved@2 at 2000 | **lost by running longer** |
| --- | --- | --- | --- |
| training | 148 | 139 | **9** |
| evaluation | 90 | 80 | **10** |

Ten evaluation tasks are correctly ranked into the top 2 at an intermediate
budget and then demoted out of it by continued optimisation. That is 2.5pp — an
eighth of the solver's entire score — thrown away by not stopping. It is a
selection failure and a compute failure at once, and it is a stronger version of
H2 than the one preregistered.

Not in the plan; reported as an observation, not as a tested hypothesis.

## 8. Confidence intervals

n = 400 per split. Wilson 95% intervals on the evaluation split:

- realised@2 = 20.00% [16.4%, 24.2%]
- oracle@any = 34.25% [29.8%, 39.0%]

The intervals do not overlap, so the selection headroom is not a sampling
artifact. The compute-headroom gap at budget 200 (25 vs 90) is far outside any
plausible interval.

## 9. Per-task breakdown

`artifacts/exp001/headroom.json` — per split: `selection` counts at every k,
`uniform_accuracy_by_budget`, `oracle_allocation_by_budget`,
`minimum_sufficient_budget_histogram`, `never_solved`.

## 10. Failure categories

Mapping to `paper/FAILURE_TAXONOMY.md`, evaluation split, 400 tasks:

| Branch | Count | Share of failures |
| --- | --- | --- |
| Branch G — correct answer never generated | 263 | **82.2%** |
| Branch S — generated, ranked below 2 | 57 | 17.8% |
| of which S1/S2, rank 3-20 | 35 | 10.9% |
| of which rank > 20 | 22 | 6.9% |

Sub-categories within branch G are not computable from these traces, which
record only hashes and scores, not the candidate grids. That limitation is
specific to the CompressARC artifact; the Stage B artifact stores full grids and
will support the full taxonomy.

## 11. Claims supported / weakened / rejected

| Claim | Effect |
| --- | --- |
| C2 (selection is a bottleneck distinct from generation) | **SUPPORTED** on ARC-AGI-1. 17.8% of failures are selection failures. |
| C3 (compute reallocation has headroom) | **SUPPORTED** on ARC-AGI-1, strongly: 8x compute reduction at matched accuracy. |
| C1 (cross-solver complementarity) | **UNTOUCHED** — needs a second solver's per-task vector, which is Stage B. |
| B5 (correct candidates generated then not chosen) | **STRENGTHENED** from one qualitative sentence about 2-3 tasks to a measured 57 of 400. |
| Thesis T2 (verification) | premise **holds**. Not killed. |
| Thesis T1 (routing) | premise **holds**. Not killed. |

**Neither thesis is killed. The preregistered most-likely negative outcome —
that difficulty is near-binary and both headrooms are near zero — did not
occur.**

## 12. Artifact paths

- `artifacts/exp001/headroom.json`
- `src/analysis/headroom.py`

## 13. Candidate figures

- **F4** (oracle@k vs realised@2): generatable now from `headroom.json`.
- **F5** (compute-vs-accuracy, uniform vs oracle): generatable now.

Both are ARC-AGI-1 / CompressARC figures and must be captioned as such. They are
motivation figures, not result figures.

## 14. Follow-up justified by the evidence

1. **Stage B is now clearly worth its GPU cost.** The premises of both surviving
   theses hold on a real solver. Proceed to RUN-001 with candidate-record
   persistence, then rerun this exact analysis on ARC-AGI-2.
2. **The stopping question is now first-class.** The solved-then-lost result says
   *when to stop* may matter as much as *how to rank*. TRM's unused `q_halt` head
   (`docs/papers/TRM_ANALYSIS.md` §14.2) becomes materially more interesting.
3. **T2's decisive question narrows.** Selection headroom exists; the open
   question is whether a *model-independent* signal can capture it, which the
   Stage B artifact (full candidate grids) can answer and this one cannot.

## 15. Deviations from plan

1. **Budget grid is coarse** (8 points, 50-2000). Minimum sufficient budgets are
   rounded up to the next grid point, which makes the oracle's advantage a
   *conservative* underestimate. Not a threat to the conclusion.
2. **`oracle@any` was not in the preregistered k list.** Added because "was the
   answer ever produced" is the natural ceiling and the plan's `oracle@k` list
   stopped at 20. Reported alongside the preregistered k values, not instead.
3. **The solved-then-lost analysis was unplanned.** Reported as an observation.
4. **Both splits analysed in one pass**, whereas the plan called for freezing the
   code on training before touching evaluation. In practice the code was written
   against the reference implementation and validated by H0 on both splits
   simultaneously; no threshold or parameter was tuned after seeing either
   result. Recorded honestly as a protocol deviation. It does not affect H0
   (exact reproduction) and the effect sizes are far too large for analysis
   flexibility to explain.

## Scope limits, stated plainly

- **This is ARC-AGI-1, not ARC-AGI-2.** Every headroom number here is measured on
  the easier benchmark.
- **This is CompressARC, not the primary baseline.** A 76K-parameter
  per-task-trained model has a different candidate distribution from a 4B
  test-time-trained LLM. In particular CompressARC's candidates come from one
  optimisation trajectory, not from a decoder search, so its selection headroom
  may be structurally larger.
- **Nothing here justifies a thesis claim about ARC-AGI-2.** It justifies
  spending one GPU run to ask the same question there.
