# BASELINE_SELECTION

## Candidates evaluated

| | Candidate | What it is |
| --- | --- | --- |
| A | 2026 NVARC 2xT4 notebook, unmodified | `references/2026_baselines/nvarc_t4x2/`, branch 1 of NVARC on `qwen3_4b_grids15_sft139` |
| B | Clean reimplementation of NVARC branch 1 from the ARChitects Apache-2.0 source | our own loader/solver/decoder, same checkpoint |
| C | TRM as a lightweight independent baseline | MIT code + published `arc-prize-trm-031` checkpoint |
| D | ARChitects branch B (LLaDA diffusion) as a complementary solver | Apache-2.0 pretraining code, **no released checkpoint** |
| E | CompressARC | MIT, no checkpoint needed, per-task from scratch |

## Scoring

| Criterion | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| Reproducibility | medium — needs an unlicensed-status checkpoint | medium — same checkpoint, our code | **high** — MIT code + published checkpoint | **low** — no checkpoint, 39 h on 8xH100 to make one | **highest** — nothing to download |
| 2026 competition compatibility | **high** — targets the 2026 competition and 2xT4 directly | high | medium — NVARC's Kaggle port exists but is not in the repo | low | low — 20 min/task x 240 exceeds 12 h at 2 GPUs |
| Expected score | highest available, but below 27.64% (see §Compute) | same as A | 7-10% ARC-AGI-2 | unknown, ~21.67% at full scale | untested on ARC-AGI-2, likely low single digits |
| Compute to run once | 1 Kaggle run, ~11.7 h | same | ~2-4 h | infeasible | infeasible |
| Licence | **unclear** (notebook), **unchecked** (checkpoint) | ARChitects portions Apache-2.0 with notice restored; checkpoint still unchecked | **MIT, clean** | Apache-2.0 code, no weights | **MIT, cleanest** |
| Implementation clarity | good — 1015 readable lines, four modules | best — ours | good | prose-only sampler | good |
| Ablatability | **high** once candidate records are persisted | **highest** — we control every seam | medium | n/a | low — one monolithic objective |
| Suitability for a paper contribution | high — it is the system everything else is measured against | high | high — independent second solver | n/a | high — zero contamination |

## Decision

### PRIMARY BASELINE — A, then B

**A: the 2026 NVARC 2xT4 notebook, run unmodified except for artifact
persistence.**

Rationale:

1. It is the only artifact in the workspace that targets ARC Prize 2026 and 2xT4
   and produces a valid submission. Everything else needs porting work before it
   produces a number at all.
2. It descends from the strongest public ARC-AGI-2 system, so a result against
   it is a result against the state of the art rather than against a strawman.
3. Its provenance is completely traced (`docs/NVARC_2026_T4_BASELINE_AUDIT.md`),
   including exactly what its checkpoint was trained on. We know precisely what
   we can and cannot claim from it.

The single modification permitted on the first run is **persisting the
per-candidate records the notebook already builds in memory** (`beam_score`, the
eight `score_aug` values, the grid). Those records turn one GPU run into a
permanent CPU-reanalysable dataset that supports the entire selection-ablation
family (`paper/ABLATION_MATRIX.md` AB-S1, AB-S2) and the oracle analysis EXP001
needs. It changes no model behaviour.

**B is the migration target, not a competitor.** Once we intervene in the
pipeline, our code must be licence-clean: the loader comes from
`references/score_winners/02_architects/pretraining_code/arc_loader.py` with its
Apache-2.0 notice restored and a NOTICE of our changes, never from the notebook
(`docs/REFERENCE_LICENSE_AUDIT.md` §9). Plan A first for the number, B before
any published claim.

### SECONDARY DIAGNOSTIC BASELINE — C (TRM)

Chosen for four reasons that have nothing to do with its score:

1. **It is the only clean-licence, independently-reproducible ARC-AGI-2 solver
   with a published checkpoint.** MIT throughout.
2. **It is architecturally maximally different** from the primary: 7M recursive
   network versus 4B autoregressive LLM, different representation, different
   training data, different failure surface. Complementarity measured between
   these two is measured between genuine opposites.
3. **It is cheap**: ~2-4 h on Kaggle versus ~11.7 h.
4. **It carries the only native confidence signal in the field** — the `q_halt`
   head, which every system discards. Whether that signal predicts correctness
   is a question only this baseline can answer.

It is a *diagnostic* baseline: at 7-10% it is not a competitive submission, and
we will not present it as one.

### COMPLEMENTARY SOLVER — E (CompressARC), analysis only

Not as a submission — 20 min/task x 240 tasks does not fit 12 hours on 2 GPUs.

Included because it is the **only uncontaminated solver in the workspace**. It
has no pretraining, so it cannot have seen any evaluation task, which makes it
the only reference point immune to the problem that invalidates the primary
baseline's eval numbers.

And its recorded results
(`references/paper_winners/03_compressarc/results_for_the_blog_post/predictions_*.npz`)
give per-task solution ranks across 2000 inference steps for 400 tasks, MIT, on
disk, readable on CPU. That is a complete compute-versus-accuracy curve and
selection-oracle trace for a real solver, available today. It is what makes
EXP001 runnable with zero GPU quota.

**D (ARChitects diffusion) is rejected**: no released checkpoint, and creating
one costs 39 h on 8xH100. The idea remains the most interesting in the audit
(`docs/SYSTEM_COMPARISON.md` §10.2); the artifact is unavailable.

### Why not an ensemble as the primary scientific baseline

Forbidden by `paper/CLAIM_LEDGER.md` A3, and independently a bad idea on the
evidence: NVARC ran exactly this experiment and the ensemble contributed **zero**
at the 4B scale (27.22 → 27.22). Component contributions would not be separable
and the prior says there is nothing to separate.

## Blockers before any run

| Blocker | Severity | Resolution |
| --- | --- | --- |
| No Kaggle credentials (`metadata/KAGGLE_DOWNLOAD_PENDING.txt`) | **BLOCKING** | user creates `~/.kaggle/kaggle.json` |
| Checkpoint licence unverified (`sorokin/qwen3_4b_grids15_sft139`) | **BLOCKING for publication**, not for a private run | read the Kaggle model page, record in the licence audit |
| Notebook licence unclear | blocking for reuse of its code | use the ARChitects source instead (option B) |
| ARC Prize 2026 rules not held locally | blocking for final licence conclusions | obtain and record |
| Time guards will bind at 2xT4 | expect a below-27.64% score | measure it; do not treat the shortfall as a bug |

## Exact first Kaggle run plan — NOT TO BE LAUNCHED WITHOUT APPROVAL

**RUN-001: primary baseline calibration**

Purpose: establish what the primary baseline actually scores in the 2026 rerun
environment on 2xT4, and produce the persisted candidate dataset every later
CPU experiment depends on. **Not** to produce a research result.

Preconditions:
1. Kaggle credentials present.
2. `sorokin/qwen3_4b_grids15_sft139` licence read and recorded.
3. This plan committed, and its SHA recorded.

Procedure:
1. Fork the notebook into our own Kaggle kernel. Do not edit model, TTT,
   decoding or selection.
2. Two changes only:
   - Delete the four-id debug filter at `starter.py` so interactive runs cover
     the whole set rather than four tasks.
   - After the worker loop, tar `/kaggle/inference_outputs` into
     `/kaggle/working/candidates.tar.bz2` so the per-candidate records survive
     as a notebook output.
3. Verify `enable_internet: false`, GPU `NvidiaTeslaT4`, and that the model and
   dependency-notebook sources are attached.
4. Submit once. Record the public LB score.
5. Download `candidates.tar.bz2` into `artifacts/` and record its SHA256.

What is recorded: public LB score; wall-clock; how many tasks completed versus
hit the 1200 s guard; peak VRAM per GPU from the notebook's own instrumentation;
candidate counts per task; the `submission.json` SHA256.

What is **not** claimed: nothing about generalisation. The public LB is half the
hidden set, and one run of a non-deterministic decoder.

Budget: ~11.7 h of a ~30 h weekly quota. One submission of the daily allowance.

Kill condition: if fewer than 60% of tasks complete before the guards bind, the
2xT4 configuration is not viable and we reconsider — reduce TTT augmentations,
tighten the DFS cutoff, or move to an L4 allocation.

**RUN-002 (later, contingent): TRM diagnostic.** Same shape, ~2-4 h, produces the
second solver's per-task solve vector and its `q_halt` values. Not scheduled
until RUN-001 completes and EXP001 has been analysed.
