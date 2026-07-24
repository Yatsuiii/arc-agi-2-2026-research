# REFERENCE_LICENSE_AUDIT

Provenance and reuse audit of every external artifact in `~/arc-agi-2-2026`.
Evidence is a file path plus the licence text found at it. Where no licence
exists, that absence is itself the evidence and the conclusion is restrictive.

Audited: 2026-07-24. Not legal advice; this is an engineering risk assessment
that governs what this repository is allowed to contain.

## Classification key

| Class | Meaning |
| --- | --- |
| `DIRECTLY REUSABLE` | Permissive licence, no attribution burden beyond keeping the notice. |
| `REUSABLE WITH ATTRIBUTION` | Permissive licence, must retain copyright/licence notice and state changes. |
| `RESEARCH REFERENCE ONLY` | May be read and cited. No code or asset may enter our repository or our submission. |
| `CLEAN-ROOM REIMPLEMENTATION REQUIRED` | The idea is usable; the expression is not. Must be reimplemented from published description without copying source. |
| `UNCLEAR - NEEDS AUTHOR CLARIFICATION` | Licence intent ambiguous; blocked pending a written answer from the author. |

## Summary table

| # | Reference | Path | Licence evidence | Class |
| --- | --- | --- | --- | --- |
| 1 | NVARC | `references/score_winners/01_nvarc` | **No LICENSE file, no SPDX, no per-file header** | RESEARCH REFERENCE ONLY / CLEAN-ROOM REQUIRED |
| 2 | ARChitects (2025) code | `references/score_winners/02_architects/pretraining_code/*.py` | Apache-2.0 header, `Copyright 2024-2025 Daniel Franzen, Jan Disselhoff and David Hartmann` | REUSABLE WITH ATTRIBUTION |
| 2b | ARChitects (2025) report | `references/score_winners/02_architects/page.md:62` | `license: "CC BY-SA 4.0"` | REUSABLE WITH ATTRIBUTION (prose, share-alike) |
| 3 | Barbadillo `arc25` | `references/score_winners/05_barbadillo` | `setup.py:20  license='All rights reserved'` | RESEARCH REFERENCE ONLY |
| 4 | MindsAI | **absent** | n/a | UNAVAILABLE |
| 5 | Lonnie | **absent** | n/a | UNAVAILABLE |
| 6 | Tiny Recursive Models | `references/paper_winners/01_tiny_recursive_models/LICENSE` | MIT, `Copyright (c) 2025. Samsung Electronics Co., Ltd.` | REUSABLE WITH ATTRIBUTION |
| 7 | SOAR | `references/paper_winners/02_soar/LICENSE.md` | MIT, `Copyright (c) 2024 Julien Pourcel` | REUSABLE WITH ATTRIBUTION |
| 8 | CompressARC | `references/paper_winners/03_compressarc/LICENSE` | MIT, `Copyright (c) 2025 Isaac Liao` | REUSABLE WITH ATTRIBUTION |
| 9 | 2026 NVARC T4x2 notebook | `references/2026_baselines/nvarc_t4x2/*.ipynb` | **No licence statement anywhere in the notebook or kernel metadata** | UNCLEAR - NEEDS AUTHOR CLARIFICATION |
| 10 | ARC-AGI-2 benchmark | `benchmark/ARC-AGI-2/LICENSE` | Apache-2.0 | DIRECTLY REUSABLE (data) |
| 10b | Kaggle competition data | `competition_2026/extracted/*.json` | Governed by the ARC Prize 2026 Kaggle rules, not by a repo licence | USE ONLY UNDER COMPETITION RULES |

---

## 1. NVARC

Path: `references/score_winners/01_nvarc` @ `846d0198efa752534594e321fc3289fc0a06c657`

**Licence evidence: none.** Searched the whole tree for `LICENSE`, `COPYING`,
`NOTICE`, SPDX identifiers and per-file copyright headers. Zero hits. Under
default copyright law, absence of a licence means all rights reserved.

Contents and their individual status:

| Asset | Path | Status |
| --- | --- | --- |
| SDG pipeline scripts (10 files) | `SDG/scripts/*.py` | RESEARCH REFERENCE ONLY |
| SDG LLM prompts (6 files) | `SDG/prompts/*.md` | RESEARCH REFERENCE ONLY |
| Qwen3 SFT config + launcher | `ARChitects/run_sft.py`, `run_sft_4b.sh`, `sft_mg.yaml` | RESEARCH REFERENCE ONLY. Hyperparameters are facts and may be cited. |
| Cut tokenizer artifacts | `ARChitects/qwen3_configs/*` | RESEARCH REFERENCE ONLY, and separately governed by the upstream Qwen3 licence |
| TRM training/eval scripts | `TRM/pretrain-no-eval.py`, `TRM/eval-arc-k-10.py` | Derivatives of MIT-licensed TRM but redistributed without the MIT notice. **UNCLEAR - NEEDS AUTHOR CLARIFICATION** |
| ARC-AGI-1 notebooks | `ARC-AGI1/*.ipynb` | RESEARCH REFERENCE ONLY |
| Solution paper | `nvarc_2025.pdf` | Citable. Do not redistribute. |

**Submodules declared but not fetched** (`.gitmodules`, seven entries). Each
carries its own upstream licence and must be audited separately if fetched.
Note in particular:

- `external/BARC` (xu3kev/BARC) - the BARC dataset has its own terms and the
  NVARC paper states BARC was *removed* from the final data mix.
- `external/re-arc` (michaelhodel/re-arc), `external/ConceptARC`,
  `external/MINI-ARC`, `external/h-arc` - all feed the NVARC training mix
  (`nvarc_2025.pdf` Table 1) and each has its own licence.
- `external/TinyRecursiveModels` pinned at `e7b6871`, MIT.

**Kaggle datasets referenced by the README and never downloaded**:
`sorokin/nvarc-artifacts-puzzles`, `sorokin/nvarc-synthetic-puzzles`,
`sorokin/nvarc-augmented-puzzles`, `cpmpml/arc-prize-trm-training-data`,
`cpmpml/arc-prize-trm-evaluation-data`, `cpmpml/arc-prize-trm-031`. Kaggle
dataset licences are set per dataset and are **not** implied by the GitHub repo.
Each must be checked on its Kaggle page before any download.

### Derived-data contamination warning

`nvarc_2025.pdf` §2.1 and Table 1 state plainly:

- 29 ARC-AGI-2 **public evaluation** puzzles were manually labelled with
  natural-language summaries; summaries for the remaining 91 were LLM-generated
  from those.
- The `NVARC full` subset (54.9% of the 3.2M augmented training samples) "uses
  both training and evaluation puzzles from ARC-AGI-2".
- The paper acknowledges it: *"Despite the fact that we 'leaked' the
  descriptions of these puzzles to our synthetic dataset, we saw a good
  correlation with public leaderboard."*

**Consequence for us:** any NVARC-derived checkpoint, including
`sorokin/qwen3_4b_grids15_sft139`, must be assumed to have been trained on data
derived from the 120-task public evaluation set. Numbers we measure for such a
checkpoint on that set are **not held-out** and cannot support a generalisation
claim. This is a scientific constraint, not a licensing one, and it is carried
into `docs/DATASET_AUDIT.md` and `docs/BASELINE_SELECTION.md`.

**Verdict: RESEARCH REFERENCE ONLY.** Ideas, hyperparameters and reported
numbers may be cited. No file may be copied. Any component we want must be
CLEAN-ROOM REIMPLEMENTED from the paper.

## 2. ARChitects

Path: `references/score_winners/02_architects` @ `efcadc66a0fcc1ea7eca2c90eac066c54f8fc543`

The repository root has **no LICENSE file**, but the four Python files carry an
explicit Apache-2.0 header:

```
references/score_winners/02_architects/pretraining_code/arc_loader.py:1
  # Copyright 2024-2025 Daniel Franzen, Jan Disselhoff and David Hartmann
  # Licensed under the Apache License, Version 2.0 (the "License");
```

Same header verified in `model_tools.py`,
`finetune_LladaMix1400k-...-multigpu.py`, `finetune_LladaMix1400k-...-size230k.py`.

The prose report is separately licensed: `page.md:62  license: "CC BY-SA 4.0"`.

| Asset | Class | Obligation |
| --- | --- | --- |
| `pretraining_code/*.py` | REUSABLE WITH ATTRIBUTION | Apache-2.0 §4: retain the copyright and licence notice, include a copy of the licence, and add a NOTICE stating our modifications. |
| `page.md`, `The ARChitects - Technical Report*.md`, figures | REUSABLE WITH ATTRIBUTION | CC BY-SA 4.0. Quoting requires attribution; **reproducing substantial prose forces share-alike on the derived text**. Quote sparingly and cite; do not paste sections into our paper. |
| LLaDA-8B-Base weights (external) | NOT AUDITED | `GSAI-ML/LLaDA-8B-Base` has its own model licence. Out of scope until we intend to use it. |

**Verdict: REUSABLE WITH ATTRIBUTION** for the code, provided we ship the
Apache-2.0 notice and a NOTICE file. This is the only score-winning system whose
source we are actually permitted to build on. That fact matters for
`docs/BASELINE_SELECTION.md`.

## 3. Barbadillo (`arc25`)

Path: `references/score_winners/05_barbadillo` @ `25d723ddea5183f0f79cd402f643af0d6569abe6`

**Licence evidence:** `setup.py:20` — `license='All rights reserved'`. This is an
affirmative reservation, stronger than mere absence.

The repository is nevertheless the most valuable *documentation* artifact of the
three score winners: `docs/01`–`docs/06` are a full CRISP-DM writeup including
negative results. It records that the author's search-and-learn line **did not
solve any private ARC-AGI-2 test task**, and that his leaderboard result came
from a minor adaptation of the 2024 transduction + test-time-training approach.

`requirements.txt` pins `unsloth==2025.9.3`, `vllm==0.10.1.1`, `trl==0.23.0` —
useful as a compatibility reference only.

**Verdict: RESEARCH REFERENCE ONLY.** Read and cite. Copy nothing.

## 4. MindsAI

**ABSENT.** No directory under `references/score_winners/03_*`;
`references/kaggle_notebooks/` is empty.

Available evidence is limited to third-party description in the ARC Prize
technical reports (`papers/00_arc_prize_2025_technical_report.pdf`,
`papers/00_arc_agi_2_technical_report.pdf`) and to the fact that the 2024
test-time-training lineage is attributed to them by both NVARC
(`nvarc_2025.pdf` ref [2], Cole & Osman) and the ARChitects. MindsAI have
historically not open sourced their solution.

**Verdict: UNAVAILABLE.** Any teardown is necessarily secondhand and every
conclusion must be marked uncertain. See `docs/systems/MINDSAI.md`.

## 5. Lonnie

**ABSENT.** No directory, no notebook, no paper in the local workspace.

**Verdict: UNAVAILABLE.** See `docs/systems/LONNIE.md`.

## 6. Tiny Recursive Models

Path: `references/paper_winners/01_tiny_recursive_models` @ `c01103738605ba39d1430519b1ee0c62f4c707f8`

`LICENSE` — MIT, `Copyright (c) 2025. Samsung Electronics Co., Ltd. All Rights Reserved.`

The README carries an upstream notice that the repo has been **archived
(read-only)**. That affects maintenance and issue reporting, not the licence.

Datasets built by `dataset/build_arc_dataset.py` are derived from ARC-AGI-1/2
and ConceptARC, each with its own upstream licence; the MIT grant covers the
code, not those corpora.

**Verdict: REUSABLE WITH ATTRIBUTION.** MIT requires only that the copyright
notice and permission notice be retained. This is the most permissive
score-relevant codebase available to us.

## 7. SOAR

Path: `references/paper_winners/02_soar` @ `8ed0890b60b647f4ca8582b30f6dbc2c709ff443`

`LICENSE.md` — MIT, `Copyright (c) 2024 Julien Pourcel`.

Two separate items to note:

- Released models (`julien31/Soar-qwen-{7b,14b,32b,72b}`,
  `julien31/Soar-mistral-123b`) inherit the **base model** licences (Qwen,
  Mistral), not SOAR's MIT. Mistral-123B in particular is not open-weights for
  commercial use. Must be checked per checkpoint before use.
- `julien31/soar_arc_train_5M` (5M ARC solutions) is a HuggingFace dataset with
  its own card-level licence, to be checked before download.
- `references/paper_winners/02_soar/arc-prize-2025/*.json` is a **vendored copy
  of the ARC Prize 2025 Kaggle competition data**. Do not treat it as a source
  of truth and do not re-vendor it.

**Verdict: REUSABLE WITH ATTRIBUTION** for the code. Checkpoints and datasets
are separately gated.

## 8. CompressARC

Path: `references/paper_winners/03_compressarc` @ `83a22218024d46273eb32b769a906340202ffb4d`

`LICENSE` — MIT, `Copyright (c) 2025 Isaac Liao`.

No external checkpoints at all: the method trains a 76K-parameter model from
scratch per task. This makes it the single cleanest artifact in the workspace
from a provenance standpoint — nothing to download, nothing pretrained, nothing
contaminated.

`results_for_the_blog_post/predictions_{training,evaluation}.npz` are the
authors' own recorded per-task predictions, MIT-covered. **These are directly
usable as a real solver's per-task output for complementarity analysis** without
running a single GPU. Recorded here because it materially affects EXP001.

**Verdict: REUSABLE WITH ATTRIBUTION.**

## 9. The 2026 NVARC 2xT4 baseline notebook

Path: `references/2026_baselines/nvarc_t4x2/baseline-nvarc-arc-25-winning-solution-for-t4x2.ipynb`
Kaggle id: `nihilisticneuralnet/baseline-nvarc-arc-25-winning-solution-for-t4x2`

**No licence statement** in the notebook (8 cells, all code, zero markdown) or in
`kernel-metadata.json`. Kaggle notebooks default to whatever the author selects
on the kernel page; that field is not present in the exported metadata, so the
licence is unknown from local evidence alone.

### Derivative-work finding

`arc_loader.py` written by cell 2 of the notebook is a **derivative of the
Apache-2.0 ARChitects `arc_loader.py`**, with the copyright header removed.
Evidence — matching class and method names with matching semantics:

| Notebook (cell 2) | ARChitects `pretraining_code/arc_loader.py` |
| --- | --- |
| `class ArcDataset` | `class ArcDataset(object)` (line 62) |
| `permute_mod(a, descriptor, invert)` | `permute_array(a, descriptor, invert)` (line 371) |
| `forward_mod` / `invert_mod` | `transform_array(..., invert=)` (line 383) |
| `change_keys`, `as_list`, `get_length` | lines 262, 508, 481 |
| `augment`, `shuffle_ex` | `augment` (552), `permute_ex` (519) |
| `get_submission`, `fill_submission`, `validate_submission` | lines 582, 590, 597 |

The augmentation key grammar (`.rot90`, `.transpose`, `.permuteNNNNNNNNNN`,
`.exNNN`, `.copyN`, `.outN`) is identical in both.

`arc_decoder.py` (cell 3) implements two selection functions:
`score_full_probmul_3` — the ARChitects 2024 product-of-experts scorer — and
`score_kgmon` — the NVARC `score_agg` formula of `nvarc_2025.pdf` §3.4.

**Consequence:** the notebook redistributes Apache-2.0 code with the required
notice stripped, which does not satisfy Apache-2.0 §4(a)-(b). Whatever the
notebook's own licence turns out to be, **if we build on it we must restore the
ARChitects copyright and licence notice and add a NOTICE of changes.** We are
not bound by the upstream author's omission and must not replicate it.

**Verdict: UNCLEAR - NEEDS AUTHOR CLARIFICATION** for the notebook as a whole.
Its ARChitects-derived portions are separately REUSABLE WITH ATTRIBUTION under
Apache-2.0 *if we source them from the ARChitects repository rather than from
the notebook*, which is the clean path and the one we will take.

### External assets it depends on

| Asset | Licence status |
| --- | --- |
| Kaggle model `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1` | NOT CHECKED. Derived from Qwen3-4B (Apache-2.0 base) fine-tuned on NVARC synthetic data. The Kaggle model page licence is authoritative and must be read before download. Also subject to the eval-set contamination warning in §1. |
| Kaggle notebook `sorokin/pip-install-unsloth-flash-patch` | NOT CHECKED. Supplies offline pip wheels. |
| Docker image `gcr.io/kaggle-private-byod/python@sha256:320043e1...` | Kaggle-provided. Not redistributable by us. |

## 10. Official benchmark and competition data

- `benchmark/ARC-AGI-2/LICENSE` — Apache-2.0. **DIRECTLY REUSABLE** as data,
  with the notice retained. Commit `f3283f727488ad98fe575ea6a5ac981e4a188e49`.
- `competition_2026/extracted/*.json` — obtained through Kaggle. Governed by the
  ARC Prize 2026 competition rules, which are **not present locally**
  (`references/score_winners/05_barbadillo/rules/` contains only a `.empty`
  placeholder, and that would be the 2025 rules anyway). Treat as: usable for
  the competition and for research, not redistributable from this repository.

**Action item:** obtain the ARC Prize 2026 rules text and record the exact
clauses on external data, model licensing and open-sourcing requirements. The
ARC Prize open-source requirement historically conditions prize eligibility on
publishing the solution under a permissive licence — which is precisely why the
NVARC and Barbadillo licence positions matter for us.

---

## Consolidated policy for this repository

1. **No file from NVARC or Barbadillo enters this repository, ever.** Their
   ideas and published numbers are cited with a path and a page reference.
2. **ARChitects code, if used, is taken from
   `references/score_winners/02_architects/pretraining_code/` and never from the
   2026 notebook**, and arrives with its Apache-2.0 header intact plus a NOTICE
   recording our changes.
3. **TRM, SOAR and CompressARC code may be vendored** under MIT with the notice
   retained, into a clearly marked `third_party/` tree that does not yet exist.
4. **No checkpoint or Kaggle dataset is downloaded** until its Kaggle/HF page
   licence has been read and recorded in this document.
5. **Any evaluation number produced with an NVARC-derived checkpoint is reported
   as contaminated** with respect to the 120-task public evaluation set.
6. Two questions are open and blocking only for the reuse path, not for the
   study:
   - Notebook `nihilisticneuralnet/baseline-nvarc-arc-25-winning-solution-for-t4x2`: what licence?
   - NVARC repository `1ytic/NVARC`: is the absence of a LICENSE intentional?
