# ACQ-001 — FINAL_CORPUS_REPORT

**Status: COMPLETE.** Both shards of the pre-registered 171-index clean
ARC-AGI-2 candidate corpus have been acquired, validated, and merged.

## Corpus composition

| | Shard A | Shard B | Combined |
| --- | --- | --- | --- |
| Tasks | 80 | 80 | **160** |
| Test-indices | 85 | 86 | **171** |
| Kernel | `redlotusthepotus/acq001-shard-a` v1 | `redlotusthepotus/acq001-shard-b` v1 | — |
| Status | COMPLETE, 80/80 | COMPLETE, 80/80 | 160/160 tasks, 0 failures |

Task-ID sets are **disjoint** (verified) and their union equals the frozen
TEST corpus's 160 task IDs / 171 test-indices exactly
(`artifacts/ACQ001/corpus_manifest.json`,
`artifacts/ACQ001/merged_corpus_manifest.json`).

## Leakage controls (established pre-generation, restated)

0 exact-duplicate, 0 canonical-duplicate (D4 + colour relabelling), 0
shared-demonstration-pair hits across TRAIN/DEV/TEST
(`experiments/ACQ001/SPLIT_MANIFEST.md`). No ground truth or public
evaluation-split answers were used during fold construction or
generation.

## Combined archive

| Metric | Shard A | Shard B | Combined |
| --- | --- | --- | --- |
| Archive records | 36,378 | 37,111 | 73,489 |
| Candidate records | 36,208 | 36,939 | 73,147 |
| Selection records | 170 | 172 | 342 |
| Unique grids (by `grid_sha1`) | 35,270 | 35,410 | 70,680 |
| Unique-candidate fraction | 97.41% | 95.86% | **96.63%** |
| Mean candidates/test-index | 426.0 | 429.5 | 427.8 |

Both archives kept as two separate per-shard files
(`candidates.A.jsonl.gz`, `candidates.B.jsonl.gz`) — no collision is
possible since task sets are disjoint, matching `CandidateArchive`'s
per-shard schema and the RUN-001/EXP002-C2 precedent of never producing a
single merged file. `artifacts/ACQ001/merged_corpus_manifest.json` is the
single source of truth for the combined totals and both shards'
checksums.

## Combined offline oracle analysis

Computed separately per shard (`src/analysis/acq001_oracle.py`, legal
training-split ground truth, run only after generation, no tuning
performed on the result):

| Metric | Shard A | Shard B | Combined (n=171) |
| --- | --- | --- | --- |
| Full-candidate-set oracle coverage | 27.06% (23/85) | 22.09% (19/86) | **24.56% (42/171)** |
| Top-2 selection accuracy | 15.29% (13/85) | 11.63% (10/86) | **13.45% (23/171)** |

The combined 11.1pp gap between full-candidate-set oracle coverage
(24.56%) and CompressARC's own top-2 selection (13.45%) is directionally
consistent with the RUN-001 preview (7.4pp) and both shards individually,
and is the kind of recoverable-selection headroom claim C2
(`paper/CLAIM_LEDGER.md`) needs evidence for. n=171 now meets the
pre-registered power floor for this claim
(`experiments/EXP002B/CORPUS_REQUIREMENTS.md`: 170-500 test-indices to
detect 25-50 discordant pairs at 80% power). **No verifier tuning or
further analysis was performed on this result** — resolving C2 is a
separate, not-yet-started task (EXP001-B / an EXP002-B-style redesign
over this new clean corpus).

## Compute

| | Shard A | Shard B | Combined |
| --- | --- | --- | --- |
| Wall-clock | 33,899.85s (9.417h) | 33,901.05s (9.417h) | 67,800.9s (18.83h) |
| Kaggle-quota GPU-hours (wall-clock x 2) | 18.83 | 18.83 | **37.67** |

This lands almost exactly on the pre-registered ~38 GPU-hour estimate for
the 170-test-index power floor
(`experiments/EXP002C3/CORPUS_ACQUISITION_DECISION.md`) — no material
revision needed.

## Suitability for independent verifier research

**Yes.** 96.63% combined candidate diversity, a measured 11.1pp
oracle/top-2 gap, and n=171 test-indices meeting the pre-registered power
floor together give a clean, leakage-checked, non-contaminated corpus
ready for the next phase of verifier work (EXP001-B or an EXP002-B-style
redesign). This corpus supersedes RUN-001's contaminated preview for that
purpose.

## Stop point

Per the explicit instruction accompanying Shard B's approval: **this task
stops here.** No verifier training, no MODEL-001, no RUN-002, and no
further GPU work of any kind followed corpus ingestion, validation,
merge, and this report.
