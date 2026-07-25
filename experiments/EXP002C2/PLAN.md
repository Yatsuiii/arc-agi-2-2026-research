# EXP002-C2 — PLAN (preregistration)

Preregistered before execution. Directly follows the accepted EXP002-C
verdict (PARALLELISE AND SCALE, `experiments/EXP002C/PILOT_RESULTS.md`) and
the user's explicit approval of one bounded follow-up: the CompressARC
oversubscription and throughput pilot.

## 1. Experiment identifier

`EXP002-C2` — CompressARC oversubscription and throughput pilot.

## 2. Research question

Can CompressARC safely run multiple independent task processes on each T4,
substantially reducing corpus-acquisition wall-clock time without damaging
candidate diversity, archive integrity, or solver behaviour?

## 3. Falsifiable hypotheses

**H0 (pipeline, inherited).** The same 5 preregistered tasks
(`experiments/EXP002C/pilot_sample.json`), the same vendored/instrumented
CompressARC, the same 40-minute per-task safety cap, and the same archive
schema as `experiments/EXP002C/PILOT_RESULTS.md` reproduce that pilot's
per-task step-rate for any task re-run uncontended (within measurement
noise) — precondition confirming oversubscription telemetry additions did
not silently change solver behaviour.

**H1 (throughput gain exists).** At least one of C3 (3 processes/T4) or C4
(4 processes/T4) improves completed-task throughput (tasks/wall-clock-hour)
by >= 1.75x over the frozen C1 baseline (`experiments/EXP002C/PILOT_RESULTS.md`
§1-3), matching the user's success-criterion threshold.

**H2 (quality preserved).** The configuration(s) that clear H1 preserve >=90%
of C1's per-task unique-candidate generation rate and keep candidate-oracle
coverage within the (wide, n=6) uncertainty band C1 already reported.

**H3 (no systemic instability).** Neither C3 nor C4 produces archive
corruption, repeated OOM, or a hard-failure rate materially above C1's (which
was 0 hard failures, 5/5 timeouts as expected).

## 4. Theoretical motivation

`experiments/EXP002C/PILOT_RESULTS.md` §2 measured ~26-28% mean GPU
utilisation and sub-2GB peak VRAM per task on 16GB T4s at 1 process/GPU —
direct evidence, not inference, that a single T4 is not compute- or
memory-saturated by one CompressARC task. CompressARC's own upstream
`parallel_train.py` (not vendored into this project; referenced in
`third_party/compressarc/NOTICE.md`) exists specifically to schedule many
puzzles per GPU for this reason. This experiment measures whether that
headroom is real and usable, rather than assuming it, per the same pilot's
explicit verdict text ("This experiment must measure that headroom rather
than assume it").

## 5. Relationship to prior work

Direct continuation of `experiments/EXP002C/PLAN.md` and
`experiments/EXP002C/PILOT_RESULTS.md`. Reuses the identical 5-task sample,
solver code, and archive conventions; adds only concurrency and telemetry.
Note on file names: the acceptance message referenced
`experiments/EXP002C/{COMPUTE_AND_RUNTIME_PLAN,SPLIT_PROTOCOL,BASELINE_SPEC,
SMOKE_TEST}.md` and `experiments/EXP002C/CORPUS_REQUIREMENTS.md`; only
`PLAN.md`, `FEASIBILITY.md`, `PILOT_RESULTS.md`, and `pilot_sample.json`
exist under `experiments/EXP002C/` (`CORPUS_REQUIREMENTS.md` exists under
`experiments/EXP002B/`, the McNemar power analysis EXP002-C's own plan
already cites). Read and confirmed by directory listing before writing this
plan, rather than assuming those files existed. This experiment's own
`BASELINE_SPEC.md` supplies the frozen-configuration record for C1/C3/C4.

## 6. Exact baseline

**C1, reused, not rerun.** `experiments/EXP002C/PILOT_RESULTS.md`'s three
phases (1 solo + 2 concurrent-pair) at 1 process/GPU are the frozen
baseline. Per the user's explicit instruction ("Do not rerun unless required
to obtain missing telemetry"), C1 is not relaunched — its existing numbers
(`artifacts/EXP002C/pilot_kernel_output/exp002c_pilot/pilot_report.json`,
`gpu_monitor.log`) are used as-is. Missing telemetry (per-process PID,
power draw, temperature, CPU/RAM/disk, process-launch delay) was not
captured by C1's instrumentation and cannot be retroactively recovered;
`RESOURCE_ANALYSIS.md` reports this as a known gap in the C1 comparison
column rather than fabricating it.

## 7. Exact intervention

Two new configurations, both launching all 5 tasks concurrently in one phase
each (since 5 tasks fits within both C3's 6 slots and C4's 8 slots):

- **C3**: GPU0 = {`00576224`, `009d5c81`, `0520fde7`} (3 processes), GPU1 =
  {`42f83767`, `8abad3cf`} (2 processes).
- **C4**: GPU0 = {`00576224`, `009d5c81`, `0520fde7`, `8abad3cf`} (4
  processes), GPU1 = {`42f83767`} (1 process, uncontended control).

Assignment reasoning (`BASELINE_SPEC.md` §3 has the full table): `42f83767`
is C1's measured outlier (0.178 steps/s vs. 0.58-0.67 for the other four,
`experiments/EXP002C/PILOT_RESULTS.md` §1) because it has `n_test=2` and by
far the largest peak memory. Isolating it in its own GPU1 slot in both C3
(paired with only one other task) and C4 (fully solo) lets the analysis
distinguish "this task is intrinsically slow" (already established by C1)
from "this task gets slower under contention" (untested by C1), instead of
letting one already-known outlier contaminate the read on the other four
tasks' oversubscription behaviour.

No changes to solver code, iteration count (2000), timeout (2400s / 40 min),
seeds, task ordering within a config, archive schema, or candidate
extraction — the full freeze list in `BASELINE_SPEC.md` §2.

## 8-10. Training / validation / held-out splits

Not applicable — same as `experiments/EXP002C/PLAN.md` §8-10, this is
acquisition/throughput measurement, not a verifier evaluation. All 5 tasks
are used in every configuration; there is no train/cal/eval split of the
5-task sample itself.

## 11. Leakage risks

None beyond what `experiments/EXP002C/PLAN.md` §11 already covers (solver
contamination: none by construction; fold leakage: not applicable, no folds
touched). New risk specific to this pass: telemetry sampling overhead
(nvidia-smi/psutil polling threads) could itself perturb measured throughput
if sampled too aggressively — mitigated by using the same ~2s polling
interval as C1's own `gpu_monitor.log`, which already proved low-overhead
enough not to visibly affect C1's numbers.

## 12. Compute budget

Two Kaggle 2xT4 kernel executions (or one kernel running C3 then C4
sequentially), each config bounded by the same 2400s per-task safety cap as
C1, so each configuration's wall-clock is bounded above by 2400s regardless
of how many processes run (all processes within a config launch together and
the config's phase ends once every process in it has returned or been
capped). Upper bound: 2 configs x 2400s x roughly 1.0-1.3x overhead margin
for process-launch staggering ≈ under 2 hours total, well inside a single
12-hour Kaggle session and a small fraction of the ~30 GPU-hour/week quota.

## 13. Success criterion

Exactly the user's stated seven-point list (`experiments/EXP002C2/RESULTS.md`
§"Success criteria check" reproduces it verbatim against measured numbers):
>=1.75x completed-task throughput over C1; no systematic archive corruption;
no repeated OOM; >=90% of baseline unique-candidate generation preserved;
candidate-oracle coverage within C1's uncertainty band; no material
hard-failure increase; stability for the full 40-minute window.

## 14. Kill criterion

Per the user's early-abort rules: abort the *active configuration only* (not
the whole experiment) on repeated GPU OOM, archive corruption, interference
crashes, critical system-RAM exhaustion, sustained unsafe GPU temperature, no
task progress for 20 minutes, median throughput >25% worse than C1, or
unguaranteeable archive integrity. A configuration abort is logged and
reported as a finding (REDESIGN- or REJECT-leaning evidence), never hidden or
silently retried at reduced concurrency.

## 15. Intended paper claim

Feeds `experiments/EXP002C/CORPUS_REQUIREMENTS.md` / the eventual EXP002-D
clean-corpus acquisition plan's feasibility, not `paper/CLAIM_LEDGER.md`
C1-C4 directly. No verifier-accuracy or selection claim is made from this
experiment; it is acquisition-throughput engineering.

## 16. Possible negative interpretation

Most consistent with C1's own utilisation numbers (~26-28%, comfortably
under 100%) would be H1 holding at C3 and possibly C4. But CPU-side overhead
in the per-step logging/postprocessing (`_track_solution`,
`third_party/compressarc/NOTICE.md`) rather than raw GPU compute could be
the true bottleneck, in which case throughput would fail to scale even
though GPU utilisation looked low — the low-utilisation reading would then
have been misleading about *why* headroom appeared to exist, not wrong about
the fact that headroom existed. This experiment's CPU-utilisation telemetry
(§"Resource and interference telemetry") is specifically designed to
distinguish these two explanations if H1 fails.

---

## Execution

```
python -m src.run002c.build_c3c4_notebook
kaggle kernels push -p kaggle/exp002c2_oversubscription
kaggle kernels status redlotusthepotus/exp002c2-oversubscription-pilot
kaggle kernels output redlotusthepotus/exp002c2-oversubscription-pilot -p artifacts/EXP002C2/pilot_kernel_output
```

Not executed until this file is committed, per `paper/EXPERIMENT_REGISTRY.md`
rule 1.
