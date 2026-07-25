# MODEL_SELECTION_RESOURCE_CONSTRAINTS

What `experiments/EXP002C`, `EXP002C2`, and `EXP002C3`'s measured Kaggle
2xT4 resource behaviour requires any future MODEL-001 base-model choice to
respect. This document states constraints derived from measurement; it
does not select or probe a base model, and it does not claim a specific
model (Qwen-class or otherwise) is preferred — that requires a controlled
bake-off this project has not run.

## 1. One independent model per GPU vs. sharding across both T4s

`EXP002C3/RESULTS.md` §4 measured that GPU-level time-sharing among
concurrent CUDA contexts (not host CPU) is what actually rations compute
under concurrency: `0520fde7`'s training rate roughly halved (0.613 ->
0.354 steps/s) simply from a second process joining its GPU, even while
host CPU stayed well under saturation (76% vs. the 100% ceiling). **Any
future model that runs concurrent instances on a single T4 should expect a
similar GPU-sharing tax, independent of how carefully CPU threads or
affinity are managed** — this project's CPU-side interventions (thread
caps, affinity pinning) produced no measurable throughput gain
(`EXP002C3/RESULTS.md` §7), so a future model's throughput planning should
not budget for a CPU-orchestration fix to this effect; it is a GPU/driver-
level constraint.

**Sharding a single model across both T4s** (rather than running
independent copies, one per GPU) is a different resource profile this
project has not measured — CompressARC's per-task subprocess-isolation
design never spans a model instance across GPUs. No claim is made here
about whether cross-GPU sharding is favourable for MODEL-001; it is simply
outside what these three pilots measured.

## 2. Effective CPU budget per GPU process

**Measured: 4 effective vCPUs total, shared across both T4s, no static
CPU-core partition between them** (`EXP002C3/HOST_TOPOLOGY.md` — confirmed
by `os.cpu_count()`, `sched_getaffinity`, `psutil`, and the cgroup v2 quota
all agreeing exactly). This is a hard Kaggle-container constraint, not
specific to CompressARC. **Any future model-serving/training workload on
this same Kaggle 2xT4 allocation inherits the same 4-vCPU ceiling.** If a
future model's per-instance CPU demand (tokenization, data loading,
Python-side orchestration) is heavier than CompressARC's (which was shown
to already saturate the host at just 5 concurrent lightweight processes),
fewer concurrent instances will be CPU-safe than this project's own
3-per-T4 (6 total) C3 operating point.

## 3. Maximum acceptable worker count

**This project's own measurement supports up to 3 CompressARC processes
per T4 (C3) as the adopted operating point** — not because CPU allows
more (it does not; 5-on-4 already saturates CPU) but because C3 was the
configuration whose task-count throughput gain (2.98x over 1x) was
verified without quality loss, and further increasing to 4/T4 (C4,
`EXP002C2/RESULTS.md`) or attempting CPU-derived lower concurrency (B2,
this document's own source pilot) neither improved on it. **For a future
model, "maximum acceptable worker count" must be re-derived per model**,
since CompressARC's tiny (76K-parameter) per-task model size and short
per-step GPU time are not representative of a 4B-9B-parameter neural
model's resource footprint — this number does not transfer.

## 4. Available VRAM headroom

Each T4 exposes **14,911 MiB (~14.6 GiB)** total VRAM
(`EXP002C3/HOST_TOPOLOGY.md`). CompressARC's own peak-VRAM footprint was
47 MB - 1.86 GB per task (`experiments/EXP002C/PILOT_RESULTS.md` §2) —
trivial relative to the 14.6 GiB ceiling, which is why VRAM was never the
binding constraint for CompressARC's concurrency. **A 4B-parameter model
in bf16/fp16 requires roughly 8 GB just for weights (before KV-cache,
activations, or LoRA/TTT overhead), and a 9B-parameter model roughly
18 GB** — already exceeding a single T4's 14.6 GiB before any inference
or training overhead is added, meaning a 9B-class model likely requires
either quantization (as RUN-001's own notebook already does, 4-bit) or
splitting across both T4s. This is arithmetic from measured VRAM, not a
new benchmark; it does not by itself determine feasibility, only bounds
it.

## 5. Required task throughput and minimum task coverage

`experiments/EXP002C2/SCALING_PROJECTION.md` and this pilot's restated
version (`EXP002C3/SCALING_PROJECTION.md`) establish that **170
test-indices is the minimum statistically powered target**, payable in
~38 Kaggle quota GPU-hours at CompressARC's C3 rate. **Any future model
used for the same acquisition purpose (clean-corpus candidate generation)
inherits the same 170-test-index floor** if it is meant to feed the same
downstream verifier-evaluation pipeline (`src/harness/`) — the power
requirement is about the corpus, not the generating model.

## 6. Acceptable per-task adaptation time

CompressARC's per-task budget (2000 iterations / 2400s) was frozen
throughout EXP002-C/C2/C3 and never varied as an experimental condition
(explicitly out of scope, `BASELINE_SPEC.md` §2 in each pilot). **No
measurement in this project's history establishes what a comparable
per-task adaptation-time budget should be for a TTT-based neural model**
(NVARC's own reference uses 128 TTT steps per task, `nvarc_2025.pdf` §4.2,
a very different unit of work from CompressARC's from-scratch 2000-step
training). This is an open question for MODEL-001, not answered here.

## 7. Model-load overhead

Not measured by any EXP002-C/C2/C3 pilot — CompressARC trains a fresh
76K-parameter model per task from random initialization, so it has no
"load" phase comparable to loading a multi-GB checkpoint from disk. **A
future neural base model's load time (checkpoint read, quantization,
device placement) is an unmeasured cost this project must instrument
separately** before it can be compared against CompressARC's near-zero
load overhead.

## 8. Whether a 9B-class model is operationally plausible

**Not established by this document.** §4's arithmetic (9B-class weights
alone approach or exceed a single T4's 14.6 GiB) is a necessary-condition
check, not a feasibility conclusion — it does not account for
quantization, gradient/activation memory during TTT, or multi-GPU
sharding, none of which this project has measured for any neural model.
Per the acceptance message's explicit instruction, this document does not
select or claim a preference between model sizes.

## 9. Whether a 4B-class model offers a coverage advantage

**Not established by this document**, for the same reason — no controlled
comparison between model sizes has been run. A 4B model's per-instance
memory footprint (roughly half a 9B model's) would mechanically allow more
concurrent instances within the same 14.6 GiB/T4 ceiling if the workload
were otherwise identical to CompressARC's, but "coverage advantage" also
depends on per-task accuracy and adaptation time this project has not
measured for any candidate base model.

## 10. What metrics must decide between 4B and 9B (or any other size)

Before MODEL-001 selects between candidate base models, it needs, at
minimum, measurements this project's EXP002-C-family pilots establish the
*template* for but do not themselves provide for a neural model:

- Per-task wall-clock and GPU-seconds at the target concurrency level
  (this project's methodology: `BASELINE_SPEC.md`-style frozen
  configurations, `RESOURCE_ANALYSIS.md`-style per-process telemetry).
- Peak VRAM per instance, measured, not estimated from parameter count
  alone (as `EXP002C/PILOT_RESULTS.md` did for CompressARC).
- Whether GPU-level sharing (this document's §1) imposes the same kind of
  throughput tax on a larger model that it did on CompressARC's much
  smaller per-step GPU workload — this may differ substantially for a
  model whose per-step GPU kernel occupancy is much higher.
- Accuracy-per-task-time tradeoff at a fixed compute budget, the same
  compute-vs-accuracy curve `paper/FIGURE_REGISTRY.md`'s F5 (currently
  BLOCKED, needs EXP003/EXP004) is designed to produce.

No such bake-off has been run. This document constrains what any future
bake-off must measure; it does not substitute for one.
