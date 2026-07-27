# GEN002-A — BASELINE_SPEC

Frozen inputs and reference numbers, restated from already-validated
artifacts, none recomputed by this phase.

## Pilot corpus (read-only, shared with GEN001-A)

| Field | Value | Source |
| --- | --- | --- |
| Pilot test-indices | 24 | `artifacts/GEN001A/pilot_manifest.json` |
| Group A (CompressARC generation failures) | 12 | same |
| Group B (oracle success, selection failure) | 6 | same |
| Group C (native success) | 6 | same |
| Full corpus this pilot is drawn from | 160 tasks, 171 test-indices | `artifacts/ACQ001/merged_corpus_manifest.json` |
| CompressARC candidate oracle (full corpus) | 24.56% | `experiments/EXP002D/BASELINE_SPEC.md` |
| CompressARC native top-2 (full corpus) | 13.45% | same |
| Generation-failure test-indices (full corpus) | 129/171 (75.44%) | `experiments/EXP002D/ERROR_ANALYSIS.md` |

## What "the CompressARC oracle" means on the 24-index pilot specifically

By construction (`experiments/GEN001A/PILOT_SAMPLE.md`'s selection rule):
Group A has 0/12 CompressARC oracle hits, Group B has 6/6, Group C has 6/6
— so the pilot-subset CompressARC oracle is fixed at 12/24 (50%) before
any program synthesis runs. This is not a number GEN002-A discovers; it is
inherited by construction from how the sample was frozen.

## The comparison this phase makes

Not "does program synthesis beat CompressARC" — the pilot subset is
stratified specifically so that comparison is meaningless (Group A is
defined as CompressARC's own failure set). The comparison is set
complementarity, same shape as `experiments/GEN001A/GENERATOR_COMPARISON.md`:
does the program-synthesis candidate set contain correct grids on
Group-A indices, where CompressARC's contains none.

## No archive regeneration

`artifacts/ACQ001/shard_{a,b}_output/.../candidates.{A,B}.jsonl.gz` are
read (for demonstration pairs and, only after generation, for offline
oracle comparison) but never written to. CompressARC is not rerun.
