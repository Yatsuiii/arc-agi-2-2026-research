# EXP002-C — feasibility findings

Measured this pass, before any GPU work. These findings are the input to the
approval decision `experiments/EXP002C/PLAN.md` §16 asks for.

## 1. Local GPU: verified, but not the reference card

```
$ nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
name, memory.total [MiB], memory.used [MiB]
NVIDIA GeForce RTX 4050 Laptop GPU, 6141 MiB, 51 MiB
```

`paper/COMPUTE_LEDGER.md`'s "Local GPU: not verified" row is now resolved to
**verified, present, RTX 4050 Laptop, 6 GB**. This is weaker than the
reference RTX 4070 CompressARC's own README timed at ~20 min/task
(`paper/COMPUTE_LEDGER.md` reference-system table), both in compute and in
VRAM — 6 GB is a real constraint on `parallel_train.py`'s whole design
(schedule several tasks per GPU to saturate memory); on this card, tasks will
likely have to run one at a time, closer to `solve_task_cli.py`'s single-task
design than upstream's parallel scheduler.

## 2. CUDA/PyTorch environment: not installed

```
$ python3 -c "import torch"
ModuleNotFoundError: No module named 'torch'
```

No `torch`, therefore no way to confirm the GPU driver/CUDA toolkit pairing
works end to end, until an install happens. This is a precondition for even
the H0 pipeline check (`experiments/EXP002C/PLAN.md` §13), separate from and
prior to any GPU-hours spent on acquisition itself.

## 3. Data availability: confirmed, ARC-AGI-2-compatible shape

`competition_2026/extracted/arc-agi_training_challenges.json` (1000 tasks) and
`arc-agi_training_solutions.json` (1000 tasks) are present, one level up from
this repository, and match the exact `{task_id: {"train": [...], "test":
[...]}}` shape `preprocessing.Task.__init__` expects — confirmed by loading
and inspecting one entry (`00576224`) this pass. No format-conversion code is
needed; `src/run002c/solve_task_cli.py` reads this file directly.

`benchmark/ARC-AGI-2/data/training/` (1000 individual task JSON files) is a
second, redundant source of the same tasks; not used, since the combined
challenge/solution file is a better match for CompressARC's own file
convention.

## 4. Reference implementation: located, vendored, instrumented

`references/paper_winners/03_compressarc` (outside this repository, at
`/home/Yatsuiii/arc-agi-2-2026/references/paper_winners/03_compressarc`,
commit `83a22218024d46273eb32b769a906340202ffb4d`, MIT) contains the full
training/inference code, not just the recorded traces
`src/analysis/headroom.py` already reads. Nine files vendored into
`third_party/compressarc/` this pass, with one instrumentation change
(grid persistence — `third_party/compressarc/NOTICE.md`), not yet re-verified
against upstream's published numbers because `torch` is not installed to run
the H0 check.

## 5. Driver code: written, not executed

`src/run002c/{solve_task_cli.py, sample_tasks.py, acquire_corpus.py}` — reads
ARC-AGI-2 training tasks, runs vendored CompressARC per task in an isolated
subprocess, archives results in RUN-001's own `CandidateArchive` schema. No
GPU call has been made; this is CPU-only code-writing and file-format
verification, consistent with the session's "prep only, no new GPU candidates"
constraint carried over from EXP002-B and this pass's explicit gate on a "long
GPU run."

## 6. What this changes about the compute estimate

`experiments/EXP002B/CORPUS_REQUIREMENTS.md` costed the acquisition plan
against a card this project did not yet know it had access to ("local GPU
availability is itself unverified"). That is now resolved, but the answer
sharpens the problem rather than solving it: a 6 GB laptop card serially
running ~500 tasks at a (conservatively scaled) 25-35 min/task is
**~210-290 GPU-hours**, which is:

- **Far larger than any single Kaggle session** (12-hour cap,
  `paper/COMPUTE_LEDGER.md`), so it is not comparable to RUN-001's run at all.
- **Payable only across many days/weeks of background local compute**, if the
  laptop can run unattended for that long, which has not been established.
- **Not something this pass should launch unilaterally** — it is the "long GPU
  run" the user's instruction names explicitly, now with a concrete number
  attached instead of an open question.

## 7. Recommended next step, not taken

A **timed pilot of 5-10 tasks** (`experiments/EXP002C/PLAN.md`'s §"Execution"
step 2) would replace every estimate above with a measurement, at a cost of at
most a few hours of local GPU time, and is a small enough commitment to be
worth running before committing to (or downsizing) the full 500-task
acquisition. Still gated on approval, since it is real GPU time, not zero.
