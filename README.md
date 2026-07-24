# ARC-AGI-2 2026 Research

Independent ARC-AGI-2 solver and paper-track project for ARC Prize 2026.

Developed paper-first: every experiment is preregistered before it runs, and
failed hypotheses stay in the record.

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

## Current phase

**Audit complete. Baseline selected. EXP001 Stage A measured. No thesis
committed yet.**

Phases 0-12 of the evidence study are done. EXP001 Stage A ran on CPU against
CompressARC's published traces and reproduced its headline numbers exactly,
which verifies the analysis pipeline. On the held-out ARC-AGI-1 evaluation split
it found 14.25pp of selection headroom and an 8x compute reduction available to
an oracle allocator. Both surviving theses keep their premises.

Nothing has been trained. No GPU notebook has been launched. No checkpoint has
been downloaded.

## Exact next step

**RUN-001**, specified in `docs/BASELINE_SELECTION.md`, blocked on two things:

1. Kaggle credentials (`~/.kaggle/kaggle.json`), currently absent — see
   `metadata/KAGGLE_DOWNLOAD_PENDING.txt`.
2. Reading and recording the licence of the Kaggle model
   `sorokin/qwen3_4b_grids15_sft139`.

RUN-001 forks the 2026 T4x2 notebook, changes nothing about the model, the
test-time training, the decoding or the selection, and adds only the persistence
of the per-candidate records the notebook already builds in memory. One 12-hour
run then supports every CPU-only selection experiment that follows.

**Not to be launched without approval.**
