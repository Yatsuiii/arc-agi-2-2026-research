# ARC-AGI-2 2026 Research

Independent ARC-AGI-2 solver and paper-track project for ARC Prize 2026.

Developed paper-first: every experiment is preregistered before it runs, and
failed hypotheses stay in the record.

## Research posture

This repository is organized as a research log, not as a single polished
solver release.

- `main` is the stable landing branch and project index.
- major experiments live on dedicated branches and remain separated when they
  represent materially different hypotheses or contamination status.
- negative results are preserved rather than rewritten away.
- clean evidence, contaminated competition engineering, and descriptive
  post-hoc analysis are tracked separately.

## Current status

As of `2026-07-27`, the repository has four main research lines:

1. `EXP001` selection-analysis work:
   complete on ARC-AGI-1 recorded traces; selection headroom is supported,
   predictor work on ARC-AGI-2 is still blocked on `RUN-001`.
2. `GEN001/GEN002` symbolic and verifier lines:
   verifier research was frozen and two symbolic-generator configurations
   (`gen002a-program-synthesis-preflight`, `gen002b-dsl-redesign`) both ended
   as negative results.
3. `DATA001-A` clean synthetic generator preflight:
   successful on provenance, schemas, leakage control, and local harness
   validation, but failed its original coverage gate.
4. `DATA001-B` coverage-first synthetic redesign:
   completed on `data001b-coverage-curriculum` at
   `fb6b7c1b259b0a354ef82f18fd862c3749633e5d`; clean generation and leakage
   controls held, and the frozen phase verdict is
   `ADOPT COVERAGE-FIRST SYNTHETIC PIPELINE`.

`main` intentionally does not auto-merge all experiment branches. The branch
itself is the frozen record for that line of work.

## Branch guide

| Branch | Purpose | Latest status |
| --- | --- | --- |
| `main` | stable index branch | current repository landing page |
| `acq001-clean-corpus-shard-a` | held-out corpus curation | completed corpus branch |
| `run001-nvarc-baseline` | contaminated NVARC baseline path | prepared, not launched in this clean repo state |
| `exp002c2-oversubscription-pilot` | verifier oversubscription pilot | historical experiment branch |
| `exp002c3-vcpu-throughput` | verifier throughput study | historical experiment branch |
| `exp002d-powered-clean-verifier` | clean verifier line | frozen negative result |
| `gen001a-nvarc-restoration-preflight` | NVARC restoration preflight | frozen branch |
| `gen002a-program-synthesis-preflight` | first symbolic generator line | frozen negative result |
| `gen002b-dsl-redesign` | redesigned symbolic generator line | frozen negative result |
| `data001a-synthetic-prior` | clean synthetic preflight | redesign required after coverage shortfall |
| `data001b-coverage-curriculum` | coverage-first synthetic redesign | adopted clean synthetic direction for future MODEL001-A |

## How to read the repo

Start here:

1. `README.md`
2. `paper/EXPERIMENT_REGISTRY.md`
3. `paper/CLAIM_LEDGER.md`
4. `docs/PROJECT_STATE.md`

Then follow the experiment branches and their `experiments/<ID>/` directories
for preregistrations, results, and artifacts.

## Workspace structure

```
~/arc-agi-2-2026/                    external workspace, READ ONLY
├── benchmark/ARC-AGI-2/             official benchmark @ f3283f7 (Apache-2.0)
├── competition_2026/extracted/      the six Kaggle JSON files (authoritative)
├── metadata/SOURCE_MANIFEST.tsv     pinned SHA of every reference
├── papers/                          5 PDFs
├── references/
│   ├── 2026_baselines/nvarc_t4x2/   the 2026 T4x2 Kaggle notebook
│   ├── score_winners/               NVARC, ARChitects, Barbadillo
│   └── paper_winners/               TRM, SOAR, CompressARC
└── our_project/                     THIS REPOSITORY
    ├── docs/                        audits and teardowns
    │   ├── PROJECT_STATE.md         Phase 0 freeze: files, schemas, SHAs, gaps
    │   ├── REFERENCE_LICENSE_AUDIT.md
    │   ├── DATASET_AUDIT.md         statistics, duplicates, split policy
    │   ├── systems/                 NVARC, ARCHITECTS, BARBADILLO, MINDSAI, LONNIE
    │   ├── papers/                  TRM, SOAR, COMPRESSARC analyses
    │   ├── NVARC_LINEAGE.md         component provenance
    │   ├── NVARC_COMPONENT_MAP.md   data-flow diagrams
    │   ├── NVARC_2026_T4_BASELINE_AUDIT.md
    │   ├── SYSTEM_COMPARISON.md
    │   ├── BASELINE_SELECTION.md    includes the RUN-001 plan
    │   ├── CANDIDATE_RESEARCH_THESES.md
    │   └── reference_exports/       readable exports, not executed
    ├── paper/                       claim ledger, rubric, related work, taxonomy
    ├── src/
    │   ├── data_audit/              deterministic corpus analysis
    │   └── analysis/                headroom analysis (EXP001)
    ├── experiments/EXP001/          PLAN.md (preregistration) + RESULT.md
    └── artifacts/                   generated reports
```

## Reference-material policy

1. Everything outside `our_project/` is **read only**.
2. **No reference code is copied in before `docs/REFERENCE_LICENSE_AUDIT.md`
   clears it.** NVARC ships no licence and Barbadillo declares "all rights
   reserved"; neither may contribute a file. TRM, SOAR and CompressARC are MIT.
   The ARChitects' code is Apache-2.0 and is the only score-winning source we
   may build on.
3. If we reuse ARChitects-derived code we take it from the ARChitects repository
   and restore its copyright notice, never from the 2026 notebook, which
   redistributes it with the notice stripped.
4. No checkpoint or Kaggle dataset is downloaded until its licence page has been
   read and recorded.

## Data policy

- `competition_2026/extracted/*.json` is authoritative. The GitHub benchmark
  differs on 6 of 120 evaluation tasks and must not be mixed in.
- `arc-agi_test_challenges.json` is a **placeholder**: all 240 tasks are copies
  of public training tasks. It is a pipeline smoke test, never an accuracy
  signal.
- The 120-task public evaluation split is **contaminated** for any
  NVARC-derived checkpoint. `SDG/scripts/build_datasets.py` writes those tasks,
  including their test-pair answers, into the checkpoint's training mix. Any
  number measured there is labelled CONTAMINATED.
- Our own fit/dev split comes from the 1000 training tasks only.

## Reproducing the analysis

CPU only, no network, no downloads.

```bash
python -m src.data_audit        # ~4 s  -> artifacts/data_audit/
python -m src.analysis.headroom # ~20 s -> artifacts/exp001/
```

## Historical baseline note

The material below reflects the original `main`-branch baseline state before
the later `GEN002*` and `DATA001*` research branches were split out.

At that point:

- audit and baseline-selection work were complete;
- `EXP001` Stage A had been measured on CPU;
- no Kaggle notebook had been launched from this clean repo state;
- no checkpoint had been downloaded into the repository.

## Calendar

| Milestone | Date | Days from 2026-07-25 |
| --- | --- | --- |
| ARC-AGI-2 solver deadline | 2026-11-02 | 100 |
| Paper-track deadline | 2026-11-09 | 107 |

About 28 usable 12-hour Kaggle runs in total.

## Kaggle access

Working. `~/.kaggle/credentials.json` holds an OAuth token and Kaggle CLI 2.2.4
at `~/arc-agi-2-2026/.tools/kaggle-venv/bin/kaggle` authenticates. The note at
`metadata/KAGGLE_DOWNLOAD_PENDING.txt` is stale — it tested for the legacy
`kaggle.json` and missed the OAuth credential.

Persona verification may still gate prize eligibility and submission. It does
not gate API access.

## Original next planned step on main

The original next planned step recorded on `main` was **RUN-001**, specified in
`docs/BASELINE_SELECTION.md`. One precondition remained:

- Read and record the licence of the Kaggle model
  `sorokin/qwen3_4b_grids15_sft139` from its web page. The Kaggle API exposes no
  licence field for model instances, so this cannot be automated. Its training
  data (`sorokin/nvarc-*`) is licensed `unknown`, which is a reason for
  pessimism.

RUN-001 would fork the 2026 T4x2 notebook, change nothing about the model, the
test-time training, the decoding or the selection, and add only the persistence
of the per-candidate records the notebook already builds in memory. One 12-hour
run would then support every CPU-only selection experiment that follows.

**Not to be launched without approval.**
