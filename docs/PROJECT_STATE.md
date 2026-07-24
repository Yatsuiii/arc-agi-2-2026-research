# PROJECT_STATE

Phase 0 verification and freeze. Everything below is derived from the local
artifacts, not from prior assumptions.

Date of verification: 2026-07-24

## 1. Repository identity

| Item | Value |
| --- | --- |
| Active repository | `/home/Yatsuiii/arc-agi-2-2026/our_project` |
| Branch | `main` |
| HEAD at start of Phase 0 | `2c6b502e888c5978814165999c6753b64c0b7867` |
| Working tree at start | clean |

Commit history at freeze time:

```
2c6b502 Add readable export of NVARC 2xT4 baseline
c06f593 Configure ARC-AGI-2 project structure
9ec2af8 Initialize ARC-AGI-2 research project
```

## 2. Workspace layout

```
~/arc-agi-2-2026/
├── benchmark/ARC-AGI-2/            official arcprize benchmark (git clone, shallow)
├── competition_2026/
│   ├── arc-prize-2026-arc-agi-2.zip
│   └── extracted/                  six competition JSON files
├── metadata/                       SOURCE_MANIFEST.tsv, PAPER_SHA256SUMS.txt, KAGGLE_DOWNLOAD_PENDING.txt
├── papers/                         5 PDFs
├── references/
│   ├── 2026_baselines/nvarc_t4x2/  the 2026 T4x2 Kaggle notebook + kernel metadata
│   ├── kaggle_notebooks/           EMPTY
│   ├── paper_winners/{01_tiny_recursive_models,02_soar,03_compressarc}
│   └── score_winners/{01_nvarc,02_architects,05_barbadillo}
├── our_project/                    this repository
└── .tools/kaggle-venv/             local kaggle CLI venv
```

## 3. Competition file verification

All six files under `competition_2026/extracted/` parse as JSON.

| File | Type | Entries |
| --- | --- | --- |
| `arc-agi_training_challenges.json` | dict | 1000 |
| `arc-agi_training_solutions.json` | dict | 1000 |
| `arc-agi_evaluation_challenges.json` | dict | 120 |
| `arc-agi_evaluation_solutions.json` | dict | 120 |
| `arc-agi_test_challenges.json` | dict | 240 |
| `sample_submission.json` | dict | 240 |

### Task schema

A challenges file maps `task_id -> {"train": [...], "test": [...]}`.

- Each `train` element is `{"input": grid, "output": grid}`.
- Each `test` element is `{"input": grid}` only. Outputs are never present in a
  challenges file, including the training challenges file.
- A grid is a list of rows, each row a list of ints in `0..9`.

A solutions file maps `task_id -> [grid, ...]`, one grid per test input, in the
same order as the `test` list of the corresponding challenges file.

### Submission schema

`sample_submission.json` maps `task_id -> [ {"attempt_1": grid, "attempt_2": grid}, ... ]`,
one object per test input of that task.

Verified:

- `set(sample_submission) == set(test_challenges)` (240 ids).
- For every task, `len(sample_submission[id]) == len(test_challenges[id]["test"])`.
  Zero mismatches.

## 4. The Kaggle `test` file is a placeholder, not a real test set

**All 240 task ids in `arc-agi_test_challenges.json` are byte-identical to the
corresponding entries in `arc-agi_training_challenges.json` (240/240).**

- `test ∩ kaggle_training` = 240
- `test ∩ kaggle_evaluation` = 0
- `test ∩ github_evaluation` = 0

This is the standard Kaggle rerun pattern: the locally downloadable
`arc-agi_test_challenges.json` is a decoy sampled from the public training set
and is swapped for the real hidden set (120 tasks per the ARC-AGI-2 release
note) at rerun time.

Consequences that must be respected for the rest of the project:

1. Local scores on `arc-agi_test_challenges.json` are meaningless as a measure
   of generalisation. They only verify that the submission pipeline runs.
2. A submission notebook must not assume 240 tasks, and must not assume the
   number of test inputs per task.
3. The only locally available held-out signal is the 120-task evaluation set.

## 5. Kaggle competition files versus the official GitHub benchmark

GitHub benchmark commit: `f3283f727488ad98fe575ea6a5ac981e4a188e49`
(`benchmark/ARC-AGI-2`, shallow clone, no usable history).

| Comparison | Result |
| --- | --- |
| kaggle training ids ∩ github training ids | 1000 / 1000 |
| kaggle evaluation ids ∩ github evaluation ids | 120 / 120 |
| kaggle training ∩ kaggle evaluation | 0 |
| kaggle training ∩ github evaluation | 0 |
| kaggle evaluation ∩ github training | 0 |
| training tasks with identical demonstration pairs | 1000 / 1000 |
| evaluation tasks with identical demonstration pairs | 118 / 120 |
| evaluation tasks with identical test solutions | 115 / 120 |

### The two sources are NOT interchangeable on the evaluation set

Six evaluation tasks differ between the Kaggle 2026 files and GitHub `f3283f7`:

| Task | GitHub | Kaggle 2026 | Nature of the difference |
| --- | --- | --- | --- |
| `4a21e3da` | 1 test pair | 2 test pairs | Kaggle's first test pair does not exist anywhere in the GitHub task file |
| `abc82100` | 1 test pair | 2 test pairs | same |
| `b6f77b65` | 2 test pairs | 3 test pairs | same |
| `f560132c` | 1 test pair | 2 test pairs | same |
| `faa9f03d` | 4 train / 1 test | 3 train / 2 test | Kaggle's first test pair is absent from GitHub; GitHub additionally promoted one pair into `train` |
| `d8e07eb2` | 5 train pairs | 5 train pairs | one Kaggle train pair is absent from GitHub (the changelog documents a 2025-04-17 train pair fix for exactly this task) |

Checked directly: for the first five tasks, the Kaggle *extra* test pair is not
present as a train pair, a test pair, or any other pair in the GitHub task JSON.
It is genuinely unavailable in the public benchmark repository.

Implications:

1. **The Kaggle `competition_2026/extracted` files are authoritative for this
   competition.** The GitHub repo is a secondary source for provenance and the
   changelog only.
2. **Published ARC-AGI-2 "public eval" numbers from 2025 systems (NVARC,
   ARChitects, TRM, CompressARC) were measured against a different pair set than
   the one we will score against.** Any comparison we make must state which
   evaluation snapshot produced each number. Treat cross-source score
   comparisons as approximate, never as exact.
3. Do not build a mixed evaluation set from both sources. Pick the Kaggle files
   and freeze them.

The benchmark clone is shallow (`git log` shows only `f3283f7`), so the
direction of the drift cannot be reconstructed locally. Recorded as an open
provenance question, not as a resolved fact.

## 6. External repository commit SHAs

From `metadata/SOURCE_MANIFEST.tsv`, all confirmed present on disk:

| Local path | Commit | Remote |
| --- | --- | --- |
| `benchmark/ARC-AGI-2` | `f3283f727488ad98fe575ea6a5ac981e4a188e49` | github.com/arcprize/ARC-AGI-2 |
| `references/paper_winners/01_tiny_recursive_models` | `c01103738605ba39d1430519b1ee0c62f4c707f8` | github.com/SamsungSAILMontreal/TinyRecursiveModels |
| `references/paper_winners/02_soar` | `8ed0890b60b647f4ca8582b30f6dbc2c709ff443` | github.com/flowersteam/SOAR |
| `references/paper_winners/03_compressarc` | `83a22218024d46273eb32b769a906340202ffb4d` | github.com/iliao2345/CompressARC |
| `references/score_winners/01_nvarc` | `846d0198efa752534594e321fc3289fc0a06c657` | github.com/1ytic/NVARC |
| `references/score_winners/02_architects` | `efcadc66a0fcc1ea7eca2c90eac066c54f8fc543` | github.com/LambdaLabsML/ARC2025_Solution_by_the_ARChitects |
| `references/score_winners/05_barbadillo` | `25d723ddea5183f0f79cd402f643af0d6569abe6` | github.com/ironbar/arc25 |

### NVARC submodules are declared but not fetched

`references/score_winners/01_nvarc/.gitmodules` declares seven submodules; all
seven directories exist but are empty. Recorded gitlink SHAs:

| Submodule | Pinned SHA | Upstream |
| --- | --- | --- |
| `external/ARC-AGI-2` | `f3283f727488ad98fe575ea6a5ac981e4a188e49` | arcprize/ARC-AGI-2 |
| `external/BARC` | `a7b51a6b1ff969da3a78a71c533b6d79a93966e7` | xu3kev/BARC |
| `external/ConceptARC` | `b22ef526b4656679816b7811e78f55cc24d736d7` | victorvikram/ConceptARC |
| `external/MINI-ARC` | `792d082c40d496f2f106f63fa7125bb115c8230b` | KSB21ST/MINI-ARC |
| `external/TinyRecursiveModels` | `e7b68717f0a6c4cbb4ce6fbef787b14f42083bd9` | SamsungSAILMontreal/TinyRecursiveModels |
| `external/h-arc` | `2983eb8672097cd555685a8d140e2f66e1a3a91a` | Le-Gris/h-arc |
| `external/re-arc` | `e5b7f1d06362a76f9d3b8c25154ff1fafca897ce` | michaelhodel/re-arc |

Note the TRM pin `e7b6871` differs from our own TRM clone `c011037`. NVARC's TRM
branch was built against a specific TRM revision that we do not currently hold.

## 7. Papers present

`papers/` with SHA256 recorded in `metadata/PAPER_SHA256SUMS.txt`:

- `00_arc_agi_2_technical_report.pdf`
- `00_arc_prize_2025_technical_report.pdf`
- `01_tiny_recursive_models.pdf`
- `02_soar.pdf`
- `03_compressarc.pdf`

Additionally `references/score_winners/01_nvarc/nvarc_2025.pdf` (the NVARC
solution paper) and
`references/score_winners/02_architects/The ARChitects - Technical Report 2a30571b42f380b6bee5c7d51d71126c.md`
(the ARChitects 2025 technical report, markdown export with figures).

## 8. Missing references

| Expected | Status | Impact |
| --- | --- | --- |
| `references/score_winners/03_*` (MindsAI) | **ABSENT** | No score-producing artifact. MindsAI has historically not open sourced. Teardown will be evidence-limited. |
| `references/score_winners/04_*` (Lonnie) | **ABSENT** | No score-producing artifact. |
| `references/kaggle_notebooks/` | **EMPTY** | No exact score-winning notebooks beyond the 2026 T4x2 baseline. |
| NVARC submodule contents (7 repos) | **NOT FETCHED** | BARC, re-arc, h-arc, MINI-ARC, ConceptARC, TRM@e7b6871 unavailable. Blocks exact reproduction of the NVARC SDG pipeline. |
| NVARC Kaggle datasets (`nvarc-artifacts-puzzles`, `nvarc-synthetic-puzzles`, `nvarc-augmented-puzzles`) | **NOT DOWNLOADED** | 103k synthetic + 3.2M augmented puzzles. Required to retrain either NVARC branch. |
| TRM Kaggle datasets (`cpmpml/arc-prize-trm-training-data`, `-evaluation-data`, `arc-prize-trm-031`) | **NOT DOWNLOADED** | Required to retrain or run the NVARC TRM branch. |
| `sorokin/qwen3_4b_grids15_sft139` checkpoint | **NOT DOWNLOADED** (deliberately, per implementation limits) | Required to run the 2026 T4x2 baseline. |
| Kaggle API credentials | **ABSENT** (`metadata/KAGGLE_DOWNLOAD_PENDING.txt`) | Blocks every Kaggle dataset/model download above. **This is the single largest reproducibility blocker.** |

None of these block the literature and architecture study. All are recorded as
explicit gaps and are carried into `docs/REFERENCE_LICENSE_AUDIT.md` and
`docs/BASELINE_SELECTION.md`.

## 9. Frozen decisions from Phase 0

1. `competition_2026/extracted/*.json` is the authoritative dataset. Frozen.
2. `arc-agi_test_challenges.json` is a pipeline smoke-test fixture only, never
   an accuracy signal.
3. The 120-task Kaggle evaluation set is the only local held-out signal and is
   subject to the split policy defined in `docs/DATASET_AUDIT.md`.
4. All external directories outside `our_project` are read-only.
5. No reference code is copied into this repository before
   `docs/REFERENCE_LICENSE_AUDIT.md` clears it.
