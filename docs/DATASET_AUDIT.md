# DATASET_AUDIT

Everything here is regenerable with `python -m src.data_audit`, CPU only, no
network, ~4 seconds. Artifacts:

- `artifacts/data_audit/task_statistics.json` — per-split distribution summaries
- `artifacts/data_audit/task_statistics.csv` — 2480 rows, one per task per split
- `artifacts/data_audit/duplicate_report.json`
- `artifacts/data_audit/schema_report.json`

## 1. Schema validation

Zero violations across all five corpora (1000 + 120 + 240 Kaggle, 1000 + 120
GitHub). Checked: no empty grids, no ragged rows, no dimension above 30, no
colour outside 0..9, every task has at least one demonstration and one test.

Submission contract against `sample_submission.json`: 240 tasks, keys exactly
`attempt_1` / `attempt_2`, no missing ids, no unexpected ids, no entry-count
mismatches.

## 2. The 2026 competition data is the 2025 competition data

Compared `competition_2026/extracted/` against the ARC Prize 2025 files vendored
in `references/paper_winners/02_soar/arc-prize-2025/`:

| File | 2025 | 2026 | Byte-identical |
| --- | --- | --- | --- |
| `arc-agi_evaluation_challenges.json` | 120 | 120 | **yes** |
| `arc-agi_evaluation_solutions.json` | 120 | 120 | **yes** |
| `arc-agi_test_challenges.json` | 240 | 240 | **yes** |
| `sample_submission.json` | 240 | 240 | **yes** |
| `arc-agi_training_challenges.json` | 1009 | 1000 | no — 9 tasks removed |
| `arc-agi_training_solutions.json` | 1009 | 1000 | no — same 9 |

The 1000 shared training tasks are content-identical. The nine removed ids are:

```
0dfd9992  29ec7d0e  3631a71a  40853293  73251a56
9ecd008a  a3df8b1e  c3f564a4  dc0a314f
```

None of them appears in the ARC-AGI-2 GitHub repository, in either split. They
are ARC-AGI-1 carryover tasks that the 2025 Kaggle bundle included and the 2026
bundle drops.

Two consequences that matter:

1. **The 120-task evaluation set we will use is exactly the one the 2025 teams
   tuned against.** NVARC's local eval number (30/120 for Qwen3-4B-Thinking-2507)
   and the ARChitects' (~30.5% ± 1% with known shape) were measured on this
   file. Cross-year comparison on this split is legitimate.
2. **Every contamination that happened in 2025 is still live in 2026.** In
   particular the NVARC synthetic dataset was built from summaries of all 120 of
   these evaluation tasks (`nvarc_2025.pdf` §2.1). See §6.

The mismatch reported in `docs/PROJECT_STATE.md` §5 is therefore a drift in the
*GitHub repository*, not in the competition data. The Kaggle files have been
stable across two competition years; `arcprize/ARC-AGI-2` at `f3283f7` has moved
away from them on 6 tasks.

## 3. Duplicates and near-duplicates

Three notions, defined in `src/data_audit/duplicates.py`:

| Notion | Definition | Cross-split hits |
| --- | --- | --- |
| exact task | identical demonstration pairs | 240 |
| canonical task | identical up to D4 (transpose x rot90) **and** colour relabelling by first appearance | 240 |
| shared demonstration pair | one input/output pair appearing in two splits | 767 |

**All 240 exact and all 240 canonical collisions are the same thing: each
`kaggle_test` task is a copy of the `kaggle_training` task with the identical
id.** Zero groups are anything else. Likewise all 767 shared pairs are
test↔training with matching ids.

Therefore:

- **Zero duplicates within the training set.**
- **Zero duplicates within the evaluation set.**
- **Zero duplicates, exact or canonical, between training and evaluation.**

The canonical notion is the important one: D4 plus colour relabelling is exactly
the augmentation group every reference solver trains on
(`nvarc_t4x2_notebook.py:263-270`, TRM `build_arc_dataset.py`, ARChitects
`arc_loader.augment`). Two tasks identical under it would be literally
indistinguishable to those solvers. There are none.

**Conclusion: ARC-AGI-2's public train/eval split has no structural leakage of
its own.** All contamination risk in this project is imported from external
training data, not intrinsic to the corpus.

## 4. Distribution shift between training and evaluation

This is the largest single finding of the dataset audit. The public evaluation
set is not a random sample of the public training set.

| Statistic | training (n=1000) | evaluation (n=120) | shift |
| --- | --- | --- | --- |
| median max input height | 13 | **25** | 1.9x |
| median max input width | 14 | **25** | 1.8x |
| median max input cells | 169 | **552** | 3.3x |
| mean max input cells | 245 | **556** | 2.3x |
| median max output cells | 121 (mean 206) | **400** (mean 461) | 3.3x |
| median distinct input colours | 6 | **9** | +3 |
| mean distinct input colours | 5.84 | **7.75** | +1.9 |
| median objects per input grid | 6.3 | **14.3** | 2.3x |
| mean objects per input grid | 15.9 | 31.2 | 2.0x |
| tasks with any grid dimension > 20 | 222 / 1000 (22%) | **85 / 120 (71%)** | 3.2x |
| tasks with <= 2 demonstrations | 158 / 1000 (16%) | **34 / 120 (28%)** | 1.8x |
| mean demonstrations per task | 3.23 | 2.98 | fewer |
| mean test inputs per task | 1.08 | **1.43** | more |
| tasks introducing new colours | 29% | 13% | fewer |
| output shape varies across demos | 57% | 69% | more |

Size relation of output to input, as a fraction of each split:

| relation | training | evaluation |
| --- | --- | --- |
| same | 68.0% | 67.5% |
| smaller | 22.6% | 21.7% |
| larger | 8.0% | 2.5% |
| inconsistent across demos | 1.1% | **6.7%** |
| mixed | 0.3% | 1.7% |

The evaluation tasks are systematically **larger, more colourful, more
object-dense, given fewer demonstrations, scored on more test inputs, and six
times more likely to have an output-size rule that is not consistent across
demonstrations.**

Why this matters concretely:

- **Sequence length.** A 30x30 grid is 930 tokens in the notebook's format (one
  digit per cell plus newlines). A median evaluation task with 3 demonstrations
  plus a test input is ~2200 tokens of grid before formatting overhead; the
  notebook caps at `max_seq_length=8192` and *drops demonstration pairs* when it
  exceeds that (`cut_to_len`, `nvarc_t4x2_notebook.py:227-247`). **On the
  evaluation distribution this truncation fires far more often than on the
  training distribution**, and it removes exactly the evidence the solver needs.
  This is a measurable, unreported failure mode.
- **Model selection.** Hyperparameters chosen on the training split are chosen
  on 13x14 grids and applied to 25x25 grids. Any compute budget or step count
  tuned on training will be mis-set for evaluation.
- **The 6.7% inconsistent size relation** maps directly onto failure category G1
  in `paper/FAILURE_TAXONOMY.md`, and onto the ARChitects' decision to train a
  separate shape-prediction model that was only ~85% accurate.

The colour-frequency profiles also differ: training is dominated by colour 0
(background, 4887 occurrences, most frequent), evaluation is not (colour 0 is
only 6th, 341 occurrences). Evaluation grids are denser, with less black space.

## 5. What may legally and scientifically be used, per split

| Split | Legal to train on | Scientific role |
| --- | --- | --- |
| `arc-agi_training_challenges/solutions.json` (1000) | Yes, under competition rules | **Training and hyperparameter search.** The only split we may fit on. |
| `arc-agi_evaluation_challenges/solutions.json` (120) | Legally yes; **we will not** | See §6. Contaminated for NVARC-derived checkpoints. |
| `arc-agi_test_challenges.json` (240) | n/a | **Pipeline smoke test only.** It is a copy of 240 training tasks (§3). Any accuracy number on it is meaningless. |
| ARC-AGI-2 GitHub `data/training` | Yes | Redundant with the Kaggle training set (identical, verified). No reason to use it. |
| ARC-AGI-2 GitHub `data/evaluation` | Yes | **Do not use.** Differs from the Kaggle eval set on 6 tasks. Mixing sources would make our numbers incomparable to both 2025 results and our own. |
| Hidden test set | n/a | 120 tasks, revealed only at rerun. The only honest generalisation measurement available. |

## 6. Split policy for this project

Frozen decisions. Changing any of these requires a commit that says so.

### 6.1 The evaluation set is quarantined, with one documented exception

The 120-task public evaluation set is **not** a clean held-out set for us,
because the checkpoint we are most likely to baseline against
(`sorokin/qwen3_4b_grids15_sft139`) was trained on synthetic data generated from
those exact tasks:

> "We managed to label 29 puzzles and write puzzle summaries manually. [...] we
> generated additional puzzle summaries for the remaining 91 evaluation puzzles"
> — `nvarc_2025.pdf` §2.1
>
> "NVARC full subset uses both training and evaluation puzzles from ARC-AGI-2"
> — `nvarc_2025.pdf` Table 1, 54.9% of 3.2M samples
>
> "Despite the fact that we 'leaked' the descriptions of these puzzles to our
> synthetic dataset, we saw a good correlation with public leaderboard."
> — `nvarc_2025.pdf` §3.5

Policy:

1. Any number measured on the 120-task evaluation set with an NVARC-derived
   checkpoint is labelled **CONTAMINATED** in every table it appears in. It is a
   sanity check, never evidence of generalisation.
2. Comparative measurements that hold the checkpoint fixed and vary only
   something downstream of it — selection algorithm, candidate count, routing —
   are **less** affected, because contamination shifts both arms equally. These
   are usable for relative claims and not for absolute ones. This is the design
   principle behind EXP001.
3. Absolute generalisation claims require a Kaggle rerun score. Nothing else.

### 6.2 Split for our own development

From the 1000 training tasks:

- **fit** (800 tasks): anything we train on.
- **dev** (200 tasks): hyperparameter and model selection.
- Split by a fixed seed, stratified on the flags that drive the train/eval shift
  (`large_grid`, `few_demonstrations`, `size_relation`), so that dev at least
  partially resembles the evaluation distribution.
- The split is written to `artifacts/data_audit/` once and never regenerated.

Because the shift documented in §4 is large, **dev accuracy will over-estimate
evaluation accuracy.** We report both and expect a gap; a method whose gain
survives the shift is the one worth having.

### 6.3 Avoiding public-leaderboard overfitting

The 2025 evidence is unambiguous that this is a real failure: the ARChitects
expected ~26% and scored 21.67%, and attributed it to "some overfitting towards
the evaluation set" (`page.md` §Final Submission's Results).

Rules:

1. Submission budget is preregistered per experiment in `experiments/*/PLAN.md`.
   A submission not named in a plan does not happen.
2. No hyperparameter is ever selected by comparing leaderboard scores. Selection
   happens on `dev`; the leaderboard confirms or refutes, once.
3. The leaderboard number is recorded in `paper/EXPERIMENT_REGISTRY.md` whether
   it helps or hurts.
4. `paper/CLAIM_LEDGER.md` A4 forbids reporting leaderboard-tuned improvements.

### 6.4 Task-family leakage control

There is no official task-family labelling, and inventing one with an LLM would
be both expensive and unreproducible. Instead we use the deterministic flags
already computed in `task_statistics.csv` (`size_relation`,
`output_shape_varies`, `introduces_colours`, `removes_colours`,
`few_demonstrations`, `large_grid`) as a coarse family proxy.

Control: the fit/dev split is stratified on these flags, and every accuracy
table is additionally broken down by them. If a method's gain is concentrated in
a single stratum, that is reported as a limitation rather than aggregated away.
This directly feeds the universality row of `paper/RUBRIC_SCORECARD.md`.

The canonical-duplicate check (§3) is the leakage control for the strong form:
it is rerun whenever any external corpus (RE-ARC, ConceptARC, BARC, synthetic
data) is added, against the evaluation set, before that corpus is used. Zero
canonical collisions is the gate.

## 7. Transformation families

Deliberately **not** produced. Assigning transformation families requires either
human labelling or an LLM, and the brief forbids the latter for this audit. The
deterministic flags in §6.4 are the honest substitute and are labelled as a
proxy, not as families. Human family labelling, if it happens, follows the
two-rater protocol in `paper/FAILURE_TAXONOMY.md`.

## 8. Task ambiguity

Also not automated. A task is ambiguous when more than one simple rule fits the
demonstrations, which is not decidable from grids alone. Recorded as taxonomy
label T5, human-review only. The `inconsistent` size relation (6.7% of
evaluation tasks) is the one machine-detectable *symptom* of ambiguity and is
reported in §4.
