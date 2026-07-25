# RUN-001 — results

RUN-001 is dataset acquisition plus a competition-baseline capture, not a
hypothesis test (`PLAN.md`). It produced the candidate archive that EXP001-B and
the selection ablations need, and one contaminated, partial baseline score.

## Headline

| | |
| --- | --- |
| Kernel | `redlotusthepotus/run001-nvarc-t4x2-baseline` v1 |
| Built from commit | `131eba8` |
| Hardware | 2x Tesla T4 (sm75), pinned reference docker image |
| Wall clock | ~11 h 43 m (pushed 00:45 IST, complete 12:28 IST) |
| Terminal status | `COMPLETE`, 0 tracebacks, 0 OOM |
| Coverage | 77/120 tasks reached, 72 with candidates, 43 never reached |
| Classification | **TIMED_OUT** (budget drained; 41/77 hit the per-task guard) |

## Score — COMPETITION-ONLY, SCIENTIFICALLY CONTAMINATED BASELINE

The notebook self-scores in interactive mode against
`arc-agi_evaluation_solutions.json`.

| Denominator | Correct (fractional) | Rate |
| --- | --- | --- |
| Full 120-task eval split | 16.83 | **14.0%** |
| 72 tasks that produced candidates | 16.8 | 23.4% |
| 172 test-inputs (exact-match top-2) | 23 | 13.4% |

**This number is not evidence of generalisation and must never be presented as
such.** Two independent reasons:

1. **Contaminated.** The checkpoint `qwen3_4b_grids15_sft139` was trained on
   these exact 120 evaluation tasks, including their test-pair answers, at 6
   augmented copies each (`docs/systems/NVARC.md` §9). The model may be recalling
   training data.
2. **Partial.** Only 77/120 tasks were reached before the 11 h 40 m budget
   drained. The 43 unreached tasks scored 0 by placeholder. A full run would
   score higher.

For reference, NVARC's contaminated local number for this checkpoint was 30/120
(`nvarc_2025.pdf` Table 2) over a full 12 h on 4x L4. Our 14.0% over 77/120 tasks
on 2x T4 is consistent with the compute story in
`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §11: roughly a quarter of the per-task
compute and a looser DFS cutoff, run partially.

## Selection ablation — first data point on a number NVARC never published

The notebook's own `benchmark_selection_algos`, over the 72 tasks with
candidates:

| Selection algorithm | Score / 72 |
| --- | --- |
| `score_kgmon` (NVARC `score_agg`) | **16.8** |
| `score_full_probmul_3` (ARChitects 2024 PoE) | 16.3 |

`score_kgmon` edges the 2024 product-of-experts by 0.5 tasks here. NVARC called
`score_agg` "better" with no isolated number (`docs/systems/NVARC.md` §26); this
is a first, tiny, contaminated data point. **AB-S1** now has real per-candidate
`beam_score` and `score_aug[8]` to do this properly and offline.

## Selection-headroom preview — the reason this archive exists

Computed locally from `candidates.jsonl.gz` against ground truth, over the 94
test-inputs that produced candidates:

| Quantity | Count | Rate |
| --- | --- | --- |
| Correct grid present among candidates (oracle) | 30 | 31.9% |
| Correct grid selected into submitted top-2 (realised) | 23 | 24.5% |
| **Selection headroom (generated, not selected)** | **7** | **7.4pp** |

This is the first direct measurement of selection headroom on **ARC-AGI-2**
candidates from a real transduction solver. It points the same direction as
EXP001-A on ARC-AGI-1 (14.25pp), which is what claim C2 predicts.

**It is a preview, not the EXP001-B result.** It is contaminated and covers only
94/172 test-inputs. The contamination inflates both oracle and realised together,
so the *difference* is the more robust quantity — the same argument as
`experiments/EXP001/PLAN.md` §10-11 — but a clean EXP001-B still needs the full
analysis pipeline over this archive plus, ideally, a second solver's vectors.

## Artifacts

`artifacts/run001/run001/`, hashes in `ARTIFACT_MANIFEST.tsv`:

- `candidates.jsonl.gz` — 1129 per-candidate records: grid, `beam_score`,
  `score_aug[8]`, augmentation key + inverse, generation order, latency, GPU.
- `candidates.ranking.jsonl.gz` — 595 post-aggregation ranking records.
- `task_summary.csv` — 77 rows: timings, guard hits, peak memory.
- `submission.json`, `runtime_summary.json`, `run_manifest.json`, worker shards.

## What this unblocks

1. **EXP001-B** — the ARC-AGI-2 replication of the headroom analysis, now with a
   real archive. The preview above is a positive early signal.
2. **AB-S1 / AB-S2** — selection-algorithm and augmentation-count ablations,
   CPU-only, offline, from the stored `score_aug[8]`.

## What it does not do

It selects no thesis, supports no contribution claim, and is not a leaderboard
submission. RUN-002 is not started.

## Instrumentation gaps to fix before any rerun

1. Pass `manifest=` to `CandidateArchive` so the manifest is emitted live, not
   reconstructed.
2. Call `write_runtime_summary` per worker (the merged `runtime_summary.json`
   has `shards: []`).
3. `peak_mem_train_mib` is empty in the summary — only inference peak was
   captured at flush. Capture the training peak too.

None affects the integrity of what was captured; all are completeness
improvements.
