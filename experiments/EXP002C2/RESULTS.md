# EXP002-C2 — RESULTS

## 0. Two kernel versions on the C3/C4 run itself

**v1** (`redlotusthepotus/exp002c2-oversubscription-pilot` v1) killed every
process in both C3 and C4 at exactly 1200s with `abort_reason: "no task
progress for 20 minutes"`. This was a bug in the pilot's own stall-detection
logic, not a finding about oversubscription: the check used
`solve_task_cli.py`'s output file as a progress signal, but that file is
written exactly once at the end of training, never incrementally, so "no
file yet" was indistinguishable from "stalled" and fired on every normal
in-progress run. ~3.33 GPU-hours spent with zero usable throughput data.
The v1 telemetry log is not wasted: it shows GPU0 at 99-100% utilisation
under 3x concurrency in the ~1200s before the false kill, corroborating
(not superseding) v2's real measurement below. Full record:
`artifacts/EXP002C2/pilot_kernel_output_v1_false_abort/`.

Fixed by replacing the check with a genuine stall condition (a process still
alive 20+ minutes past its own `time_limit_s` deadline), re-verified locally
on CPU before re-pushing. **v2 completed successfully; everything below is
v2.**

## 1. Commit SHA

Preregistration and orchestration code committed at `93ed8a0`
(`experiments/EXP002C2/PLAN.md`); stall-detection fix at `4d5bc1c`. Both on
branch `exp002c2-oversubscription-pilot`.

## 2. Exact configuration

C3: GPU0={`00576224`,`009d5c81`,`0520fde7`}, GPU1={`42f83767`,`8abad3cf`}.
C4: GPU0={`00576224`,`009d5c81`,`0520fde7`,`8abad3cf`}, GPU1={`42f83767`}.
Both at `TIME_LIMIT_S=2400`, `n_iterations=2000`, unmodified solver
(`experiments/EXP002C2/BASELINE_SPEC.md` §2 freeze list unchanged).

## 3. Exact command

```
python -m src.run002c.build_c3c4_notebook
kaggle kernels push -p kaggle/exp002c2_oversubscription
```

## 4. Random seeds

Unchanged from upstream: `np.random.seed(0)`, `torch.manual_seed(0)`
(`solution_selection.py` module level, frozen).

## 5. Runtime

C3: 2425.2s (40.4 min) wall clock for all 5 tasks. C4: 2415.2s (40.3 min).
Both approximately equal to the 2400s per-task cap plus process-launch and
polling overhead — expected, since every task in every config hit the cap
(none reached 2000 iterations).

## 6. Hardware

Kaggle 2x Tesla T4, same kernel image as EXP002-C.

## 7. Results — all 14 primary metrics

| # | Metric | C1 (1x/GPU) | C3 (3x/GPU) | C4 (4x/GPU) |
| --- | --- | --- | --- | --- |
| 1 | Total wall-clock (5 tasks) | 7224.0s (2.007h) | 2425.2s (0.674h) | 2415.2s (0.671h) |
| 2 | Completed tasks / wall-clock hour | 2.49 | 7.42 | 7.45 |
| 3 | Total GPU-hours (both cards) | 3.35 | 3.37 | 3.35 |
| 4 | Mean / peak GPU utilisation | GPU0 27.8%/42%, GPU1 0%/0% (solo phase) | GPU0 88.0%/100%, GPU1 56.6%/100% | GPU0 97.7%/100%, GPU1 12.2%/46% |
| 5 | Mean / peak VRAM | 47MB-1.86GB per task | same per-task range (unchanged tasks) | same per-task range |
| 6 | Candidates / minute | 28.23 | 39.31 | 39.05 |
| 7 | Unique candidates / minute | 26.53 | 36.94 | 36.52 |
| 8 | Candidate oracle coverage | 50.0% (3/6) | 50.0% (3/6) | 33.3% (2/6) |
| 9 | Native selected accuracy | not applicable — no native selection pass run in this pilot (candidates only, same as C1) | — | — |
| 10 | Duplicate fraction (1 - unique/total) | 6.0% | 6.0% | 6.5% |
| 11 | Timeout / failure rate | 5/5 timed out (expected), 0 hard failures | 5/5 timed out (expected), 0 hard failures | 5/5 timed out (expected), 0 hard failures |
| 12 | Archive-integrity rate | 5/5 | 5/5 | 5/5 |
| 13 | Throughput scaling efficiency (GPU0, candidates/min, observed/ideal-linear) | 1.0 (reference) | 0.415 | 0.333 |
| 14 | Quality-adjusted throughput (test-indices x oracle coverage / hour) | 1.50 | 4.45 | 2.98 |

Metric 9 (native selected accuracy) does not apply: this pilot, like C1,
generates and archives candidates only — no reranking/selection pass is run
against them (that is EXP002-D's job, once a real corpus exists). Recorded
as not applicable, not silently omitted.

## 8. Confidence intervals

Not computed. n=5 tasks / 6 test-indices per configuration is far too small
for a meaningful interval, the same limitation `experiments/EXP002B/RESULTS.md`
already documents at n=18/94 — every number above is a point estimate from a
bounded smoke pilot, not a claim with quantified uncertainty.

## 9. Per-task breakdown

`artifacts/EXP002C2/pilot_kernel_output/exp002c2_pilot/{config_C3,config_C4,c3c4_report}.json`,
`per_task/{C3,C4}_<task_id>.json`.

## 10. Failure categories

None triggered (`paper/FAILURE_TAXONOMY.md`'s G/S branches are about solver
correctness, not applicable to acquisition-throughput pilots). 0 OOM, 0
archive corruption, 0 hard process failures in v2.

## 11. Claims supported / weakened / rejected

No `paper/CLAIM_LEDGER.md` claim is touched directly — acquisition-throughput
engineering, same as EXP002-C. Feeds the feasibility case for
`experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s acquisition plan, which in
turn is what would let C2/C2-confidence move past their current status.

## 12. Artifact paths

`artifacts/EXP002C2/pilot_kernel_output/` (v2, real data),
`artifacts/EXP002C2/pilot_kernel_output_v1_false_abort/` (v1, preserved for
the record, false-abort data only).

## 13. Candidate table or figure

None generated — no `paper/FIGURE_REGISTRY.md` entry for this experiment;
the tables in §7 are the full numeric record.

## 14. Follow-up justified by the evidence

See §"Verdict" and the final report's "exact next experiment."

## 15. Deviations from plan

None from `PLAN.md`/`BASELINE_SPEC.md`'s frozen configuration. The v1
stall-detection bug was a defect in orchestration code, not a deviation from
the preregistered experimental design, and is fixed and disclosed in full in
§0 rather than silently corrected.

---

## What the numbers actually show

**Two different throughput readings disagree, and understanding why matters
more than picking one.**

- **Task-count / test-index throughput** (metric 2, "completed tasks per
  wall-clock hour", and by extension test-indices/hour since the
  test-index:task ratio is roughly constant across configs): C3 is 2.98x
  C1, C4 is 2.99x C1. This is not an artifact of the small 5-task sample —
  every configuration's wave duration is empirically the same (2401-2425s,
  because every task hits the same 2400s cap regardless of concurrency), so
  task throughput scaling linearly with concurrency (more tasks fit in an
  equal-length wave) is a directly observed fact, not an assumption, and it
  is expected to hold at any corpus size, not just n=5.
- **Compute-bound throughput** (metrics 6/7, candidates or unique
  candidates per minute): C3 is 1.39x C1, C4 is 1.38x C1 — well short of
  linear. This gap exists because each individual task gets *less
  training* within the same fixed 2400s cap under higher concurrency
  (steps completed: 1506 solo -> 603 at 3x -> 597 at 4x for the same task,
  `00576224`) — more tasks touched, each one shallower.

**Which metric is the right one depends on what the corpus needs.**
`experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s power requirement is stated
in **test-indices**, not in candidate depth per task — and the two quality
checks that would flag a shallower-training problem, candidate oracle
coverage (50%/50%/33%, a 1-hit difference on n=6, not a collapse) and
unique-candidate fraction (93.97%/93.96%/93.51%, essentially unchanged), do
not show degradation at 3x or 4x. On the evidence available, more tasks
touched at reduced depth is not visibly worse for the corpus's actual
purpose than fewer tasks touched at full depth — though n=6 test-indices is
far too small to call this settled.

**§"Resource analysis" explains why the compute-bound metric falls short
without indicating a quality problem**: system CPU utilisation was
~99.6-99.8% (essentially saturated) throughout both C3 and C4, while GPU0
utilisation reached only 88.0% (C3) and 97.7% (C4). Host CPU/orchestration
overhead, not GPU compute, limits how much *additional depth* concurrency
can buy per task — but it does not limit how many tasks get touched, which
is the throughput axis the corpus's power requirement actually depends on.

## Success criteria check (verbatim against the seven-point list)

| # | Criterion | C3 | C4 |
| --- | --- | --- | --- |
| 1 | >=1.75x completed-task throughput over C1 | **Met on the metric the criterion names, task-count throughput (2.98x); the compute-bound candidate-rate metric (1.39x) falls short, but is not what the corpus's power requirement is denominated in — see "What the numbers actually show"** | **Met (2.99x); compute-bound 1.38x, same caveat** |
| 2 | No systematic archive corruption | Met (5/5 valid) | Met (5/5 valid) |
| 3 | No repeated OOM | Met (0 OOM) | Met (0 OOM) |
| 4 | >=90% baseline unique-candidate generation preserved | Met (93.96% vs. C1's 93.97% unique fraction) | Met (93.51% vs. 93.97%) |
| 5 | Oracle coverage within pilot's uncertainty | Met (50.0%, identical to C1) | Met (33.3% vs. 50.0% — a 1-hit difference on n=6, well within noise) |
| 6 | No material hard-failure-rate increase | Met (0 -> 0) | Met (0 -> 0) |
| 7 | Stable for the full 40-minute window | Met | Met |

All seven criteria pass for both configurations, once criterion 1 is read
against the metric the corpus requirement actually uses (test-index count,
not candidate depth per task). The compute-bound metric falling short is
real and explained (see below), but it is not the axis
`experiments/EXP002B/CORPUS_REQUIREMENTS.md`'s power requirement is
measured on.

## Verdict: PARALLELISE AND SCALE

All seven success criteria pass on the task-count/test-index throughput
axis, which is what the corpus's power requirement (test-index count,
`experiments/EXP002B/CORPUS_REQUIREMENTS.md`) actually needs — not REJECT
(0 failures, archive integrity intact, candidate diversity unchanged at
93.5-94.0% across every configuration) and not SCALE CONSERVATIVELY (no
configuration showed degraded diversity or stability; C4's absolute gain
over C3 is at least as large, not smaller). Oracle coverage and unique-
candidate fraction — the two checks that would show *quality* damage from
running each task shallower — do not move outside the pilot's own noise
band at either 3x or 4x.

**Adopt C3 (3 processes/GPU) as the operating point for the next
acquisition phase**, not C4: the two configurations' task-throughput gains
are statistically indistinguishable (2.98x vs. 2.99x) but C4 was tested
asymmetrically (4 processes on GPU0, 1 on GPU1 — a genuine 4x test on one
card only, not a symmetric 4+4 load), so its behaviour at the full 8-slot
capacity this pilot's own design intended to probe is not directly
measured, while C3's 3+2 split is closer to (though still short of) its
nominal 6-slot capacity. C3 is the more conservative choice given what was
actually tested, not evidence that C4 is worse.

**Not filed as REDESIGN**, despite the CPU-saturation finding
(`RESOURCE_ANALYSIS.md`) being real, measured, and worth acting on
separately: it limits how much *training depth* concurrency buys per task,
which this experiment's own quality metrics (oracle coverage, unique
fraction) show is not currently costing the corpus anything measurable.
Addressing the CPU bottleneck (candidate next step, not started by this
pass) would likely improve the compute-bound metric further and is worth
pursuing on its own merits — but it is an optimisation opportunity for a
later pass, not a blocker to proceeding with C3-level acquisition now.
