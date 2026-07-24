# SOAR — analysis

Paper: `papers/02_soar.pdf` — Pourcel, Colas, Oudeyer, *Self-Improving Language
Models for Evolutionary Program Synthesis: A Case Study on ARC-AGI*, ICML 2025,
arXiv:2507.14172v2.
Code: `references/paper_winners/02_soar` @ `8ed0890b60b647f4ca8582b30f6dbc2c709ff443`, MIT.

Reported: **52% of the ARC-AGI-1 public test set** using only open-weight LLMs.

## 1. Central theoretical claim

A search system whose search operator is a fixed LLM has a performance ceiling
set by that LLM. If the search *trains* the operator on its own search traces,
the ceiling moves. Concretely: alternate an evolutionary search phase with a
learning phase, and the two compound into a virtuous cycle.

The second claim is the interesting one: **failure is free training data**. A
program that fails the target task is a correct program for whatever task it
does solve, so hindsight relabelling converts every failed attempt into a valid
(task, program) pair. No human-written solutions, no hand-engineered DSL, no
curated dataset.

## 2. Architecture

Not a model. A loop:

**Sample & Refine.** For a task, an LLM samples ~3k candidate Python programs.
Each is executed against the demonstration pairs. The LLM then refines ~6k
programs conditioned on execution feedback. Surviving programs vote by majority
on the test output.

**Learning.** All search traces, successes and failures, are collected.
Successes are deduplicated by code; hindsight-relabelled failures are
deduplicated by output. The pooled data fine-tunes the LLM on two tasks jointly:
program *sampling* and program *refinement*. The paper reports positive transfer
between the two.

Repeat. Four iterations reported.

## 3. Training regime

Fine-tuning open-weight LLMs (Qwen 7B/14B/32B/72B, Mistral-123B) on
self-generated data. Released dataset: `julien31/soar_arc_train_5M`, 5 million
ARC solutions. Two conda environments in the README: sglang for inference,
unsloth for training.

## 4. Inference regime

~3k samples + ~6k refinements per task, then execution filtering and majority
vote. Optionally test-time training on the target tasks, which adds 3-5% across
model sizes.

## 5. Compute

Not centrally tabulated in the local copy. The scale is legible from the
numbers: 9k LLM generations per task, across 400 tasks, times four
self-improvement iterations, at model sizes up to 123B. This is far outside a
Kaggle 12-hour budget and outside our compute entirely.

## 6. Reported ARC-AGI-2 performance

**None.** The paper is ARC-AGI-1 only. `references/paper_winners/02_soar/arc-prize-2025/`
vendors the ARC Prize 2025 competition files, so the authors clearly had
ARC-AGI-2 data, but no ARC-AGI-2 number appears in the paper.

This is the single most important fact about SOAR for our purposes and it is
easy to miss when reading the 52% headline.

## 7. Universality claim

Two forms. Across model scales: gains hold for 7B through 123B, with an extra
10-19% from self-improvement and 3-5% from test-time training at every size.
Across program space: general-purpose Python rather than a hand-built DSL, so
the method is not tied to ARC's primitives.

Not demonstrated: transfer to a different benchmark, or to ARC-AGI-2.

## 8. Main novelty

Closing the loop between evolutionary search and model training on ARC, with
hindsight relabelling as the mechanism that makes failures useful. SOAR names
four deltas over prior self-improvement work on ARC: general Python instead of a
DSL, an execution-feedback refinement step, scaling to larger open-weight LLMs,
and combining test-time training with test-time search.

## 9. Strongest supporting experiment

The four-iteration curve holding across four model scales. A gain that survives
an order of magnitude of scale change is not a tuning artifact. It also
implicitly answers "is this just more compute", because the baseline is
same-compute search with a frozen operator.

## 10. Weakest unsupported assumption

**That ARC-AGI-1 results predict ARC-AGI-2 results.** The paper does not claim
this, but any reader inheriting the method will assume it, and the local evidence
is against it:

- The ARChitects' autoregressive lineage went from 53.5% on ARC-AGI-1 to 16.94%
  on ARC-AGI-2 — the same method, a 3.2x collapse.
- Barbadillo spent the 2025 season on search-and-learn with hindsight
  relabelling, the same core idea, for ARC-AGI-2, and reports zero private test
  tasks solved (`docs/systems/BARBADILLO.md`).

Secondary weakness: majority vote over execution-consistent programs is a strong
filter only when several distinct programs agree. On ARC-AGI-2, where
`docs/DATASET_AUDIT.md` §4 shows tasks are larger and more compositional, the
probability of sampling *any* consistent program falls, and the vote degenerates.

## 11. Failure modes

- Requires at least one program that reproduces every demonstration pair. On
  hard tasks, none is found and the method has nothing to vote on.
- Cost per task is thousands of LLM generations, which does not fit a Kaggle
  runtime.
- Hindsight relabelling generates tasks drawn from the distribution of *what the
  model already writes*, which risks self-reinforcing a narrow program prior.
- Untrusted code execution at scale needs sandboxing (`soar/sandbox/`), an
  engineering cost transduction methods avoid.

## 12. Reproducibility

Good. MIT code, five released checkpoints, a released 5M-solution dataset,
per-experiment instructions in `experience/`, tutorial notebooks. Two gaps for
us: checkpoint licences follow the *base* models, not SOAR's MIT
(`docs/REFERENCE_LICENSE_AUDIT.md` §7), and the compute is out of reach.

## 13. Relationship to the score-winning systems

Almost none, and that is informative. No 2025 ARC-AGI-2 score winner used
program synthesis at solve time. NVARC used LLM-generated Python **only inside
its offline data pipeline** — generating input-grid and output-grid programs to
manufacture training puzzles (`nvarc_2025.pdf` §2.3-2.4). That is SOAR's
machinery repurposed as a data generator rather than a solver, and it is the one
place program synthesis demonstrably paid off on ARC-AGI-2.

## 14. Concepts that could support a new paper

1. **Execution consistency as verification.** SOAR is the only system in this
   audit that can *prove* a candidate consistent with the demonstrations rather
   than merely prefer it. Every transduction system ranks by the model's own
   likelihood. A transduction solver's candidate grid cannot be executed — but
   the question "does a rule exist that maps every demonstration input to its
   output *and* this test input to this candidate?" is still checkable by search
   over a cheap hypothesis space. Transplanting verification, not program
   synthesis, into a transduction pipeline is an open direction.
2. **Hindsight relabelling for transduction.** A wrong grid is the right answer
   to some other task. For program synthesis that other task is recoverable by
   execution. For transduction it is not obviously recoverable — which makes it a
   real question rather than a port.
3. **Positive transfer between sampling and refinement objectives.** Reported
   and under-explored, and it rhymes with the ARChitects' unattempted fix of
   training their model on its own recursive passes.

## 15. Ideas already absorbed elsewhere

- LLM-generated Python for grids → absorbed by NVARC as a **data pipeline**.
- Execution validation of generated programs → absorbed by NVARC's SDG stage 3.
- Consistency across independent samples as a filter → absorbed by NVARC's SDG
  stage 4.
- Hindsight relabelling → attempted independently by Barbadillo for ARC-AGI-2,
  did not score.
- Execution verification **at solve time** → absorbed by nobody in ARC-AGI-2.
