# Guillermo Barbadillo (`arc25`) — architectural teardown

Source: `references/score_winners/05_barbadillo` @ `25d723ddea5183f0f79cd402f643af0d6569abe6`
Report: `docs/05_Solution_Summary.md`, `docs/01`–`docs/06` (CRISP-DM structure)
Licence: `setup.py:20  license='All rights reserved'` — **RESEARCH REFERENCE ONLY**

This is the most valuable *documentation* artifact among the score winners and
the least valuable code artifact, because we may not use any of it. It is also
the only one that reports a year-long negative result in full.

## 1. Core solver paradigm — stated intent versus shipped system

**Intended.** Deep-learning-guided program synthesis searching Python program
space, adapting at test time by test-time training on hindsight-relabelled
attempts, in a tight search-and-learn loop.

**Shipped.** "The best result on the leaderboard was achieved with minor
adaptations of last year's transduction with test-time training approach."

The gap between the two is the finding.

## 2. Techniques

| Technique | Present | Notes |
| --- | --- | --- |
| Test-time training | yes, both in the shipped system and via hindsight relabelling in the research line | `arc25/training_tasks.py`, notebooks 003/006/007 |
| Supervised fine-tuning | yes | `scripts/finetuning.py`, `finetuning_hr.py` |
| Synthetic data | via hindsight relabelling, not generation | notebooks 006-007 |
| Recursive refinement | yes, "prediction refinement" | notebook 014, report §5 |
| Diffusion | no | |
| **Program synthesis** | **yes, the central line** | `arc25/code_execution.py`, `BARC_dsl.py`, `dsl.py` |
| Search | yes, independent-sample search | report §"My search method was very basic" |
| Ensembling | no | |
| Verifier | **yes, by construction** — a program either reproduces the demonstrations or it does not | `arc25/code_execution.py`, `parallel_code_execution.py` |
| Augmentation | yes | `arc25/data_augmentation.py` |
| RL | yes, GRPO attempts | `scripts/rl_code_finetuning*.py`, notebooks 005/012 |

## 3-4. Models

BARC induction models (Li et al.) as the primary program generator, plus base
models tried in notebooks 009-011. Sizes are not centrally tabulated in the
report. `requirements.txt` pins `unsloth==2025.9.3`, `vllm==0.10.1.1`,
`trl==0.23.0`, indicating LoRA fine-tuning and vLLM inference at 7B-ish scale.

## 5-7. Representation

Programs, not grids. Grids are rendered for the LLM by `arc25/encoders.py` and
`arc25/prompting.py`; the solver's output is Python source executed against the
demonstration inputs.

This makes the 2D-structure question moot in a way worth noting: a program that
manipulates a grid **has** the right inductive bias by construction, which is
the standard argument for induction over transduction. It did not translate into
score.

## 8-9. Augmentation and synthetic data

Hindsight relabelling rather than generation: a program that fails the target
task is a *correct* program for whatever task it does solve, so failed search
attempts become training data. Same idea as SOAR's hindsight learning
(`docs/papers/SOAR_ANALYSIS.md`), developed independently for ARC-AGI-2.

## 10-14. Search, refinement and compute

The report's own post-mortem is the most useful part:

> - A stronger induction model is needed to beat ARC. How to craft that model
>   remains an open question.
> - My search method was very basic, relying only on independent predictions.
>   That would only work on trivial tasks; to solve complex tasks, refinement is
>   needed.
> - More work is also needed to learn as much as possible from the failed
>   attempts.

`arc25/resource_monitor.py`, `memory_limit.py` and `parallel_code_execution.py`
show a real sandboxing and resource-budgeting layer — running untrusted
generated Python at scale inside Kaggle is a genuine engineering cost that the
transduction systems simply do not pay.

## 21. What generates the score

Not the research line. The report is explicit that the search-and-learn system
**"does not yet solve any of the private test tasks from ARC-AGI-2"**, and that
the leaderboard result came from the 2024 transduction + TTT recipe with minor
changes.

## 25. Hidden-set failure modes

Reported honestly: the induction model is not strong enough; independent-sample
search without refinement only solves trivial tasks; the learning signal from
failures is under-exploited.

## 26-27. Ablations

The repository is unusually rich in *reported experiments*: 20+ numbered
notebooks tracing test-time training exploration, HER v1 and v2, GRPO, search
with base models versus BARC models, search-and-learn with Unsloth, RL for
prediction refinement, Kaggle runtime analysis, and prediction analysis. Each is
a documented experiment with a conclusion, several negative.

He states the evidence obtained: **"search and learn outperforms pure search
approaches for the same number of predictions per task."** That is a real,
citable, positive result about the mechanism, even though the system built on it
did not score.

## 28-30. Reproducibility

The code is complete and installable (`environment.yml`, `requirements.txt`,
`docker/Dockerfile`, `Makefile`, `mkdocs.yml`, tests). It is also **All rights
reserved**, so none of it may enter our repository.

Reproducing would additionally need BARC checkpoints and substantial GPU time
for the RL work.

## What this system is worth to us

1. **A strong prior against betting on program synthesis for ARC-AGI-2.**
   Someone spent a full competition season on it, with working infrastructure
   and documented intermediate results, and solved zero private tasks. Combined
   with SOAR's ARC-AGI-1-only results, the local evidence says induction has not
   been shown to transfer to ARC-AGI-2 by anyone.
2. **The only public evidence that search-and-learn beats pure search at fixed
   prediction budget.** Directly relevant to any compute-allocation thesis.
3. **The clearest statement that refinement, not sampling, is the missing
   ingredient in search** — which converges with the ARChitects' independent
   conclusion from the transduction side.
4. **A model of honest reporting** that we should match: the abstract states the
   negative result in its second sentence.
