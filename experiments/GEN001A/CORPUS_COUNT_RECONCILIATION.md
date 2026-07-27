# GEN001-A — CORPUS_COUNT_RECONCILIATION

Reconciles the apparent count discrepancy between ACQ-001's own report and
EXP002-D's report, before any new generator work touches the corpus.

## The three numbers

| Number | Value | Source |
| --- | --- | --- |
| ACQ-001 "archive records" | ~73,489 | acceptance-message framing; not a literal figure printed by any ACQ-001 doc verbatim, reconstructed below |
| EXP002-D "raw candidate records" | 73,147 | `experiments/EXP002D/RESULTS.md`, `artifacts/EXP002D/metrics.json` |
| EXP002-D "unique candidates" | 70,680 | same |

## What the difference is

`artifacts/ACQ001/merged_corpus_manifest.json` records, per shard:

| Shard | `n_candidates` | `n_selection_records` | candidate + selection |
| --- | --- | --- | --- |
| A | 36,208 | 170 | 36,378 |
| B | 36,939 | 172 | 37,111 |
| **Combined** | **73,147** | **342** | **73,489** |

`73,147 + 342 = 73,489` exactly. The 73,489 figure is **every row in the
gzip archive regardless of record kind** — both `kind=candidate` rows (one
per decoded grid) and `kind=selection` rows (one per solver's own frozen
top-2 ranking decision, `src/run001/archive.py::SelectionRecord`). ACQ-001's
own `runtime_summary.{A,B}.json` reports `records_total` this same,
kind-agnostic way (`src/run001/archive.py::CandidateArchive.write_runtime_summary`
sums `self._counts`, which increments per buffered record regardless of
kind), which is why a reader following ACQ-001's own printed totals lands on
73,489, not 73,147.

`experiments/EXP002D/RESULTS.md`'s 73,147 is deliberately **candidate-kind
rows only** — `src/analysis/exp002d/corpus.py::build_canonical_tables`
reads both archives via `read_records`, filters to `kind="candidate"`
before doing anything else, because selection records are a different
entity (a solver's own ranking decision, joined onto candidates later, not
a candidate to be ranked itself) and including them in a "candidate count"
would double-count nothing but silently misdescribe what is being counted.

70,680 is the count of **unique `(task_id, test_index, grid_sha1)` groups**
within those 73,147 candidate rows (96.63% unique — the remaining 3.37% are
exact-duplicate grids produced by different augmented decode paths,
consolidated by `multiplicity` in `canonical_candidate_index.parquet`).

## No record is unaccounted for

- 342 selection records: not lost, not duplicated — they are the solver's
  own top-2 picks (170 for Shard A's 85 test-indices x 2, 172 for Shard B's
  86 x 2), consumed separately by EXP002-D's `native_rank`/`native_selected`
  join (`src/analysis/exp002d/corpus.py`), not part of the candidate count.
- 73,147 candidate records: none malformed, none excluded — EXP002-D's
  `corpus.py::main()` verification step (already run, `experiments/EXP002D/CORPUS_RECONCILIATION.md`)
  confirmed this figure matches ACQ-001's `n_candidates` totals exactly
  before any feature or fold code touched the data.
- 70,680 unique: a derived count (multiplicity-collapsed), not a subset with
  rows dropped — every one of the 73,147 raw rows is still present in
  `canonical_candidate_index.parquet`, contributing to its group's
  `multiplicity`/`beam_score_{best,mean,min}` aggregates.

## Canonical counts for GEN001-A to use going forward

| Quantity | Canonical value |
| --- | --- |
| Raw archive records (candidate + selection) | 73,489 |
| Candidate records | 73,147 |
| Valid candidate records (none excluded — all 73,147 pass schema validation) | 73,147 |
| Unique candidates | 70,680 |
| Selection records | 342 |
| Test-indices | 171 |
| Tasks | 160 |

No historical figure is replaced. 73,489 and 73,147 are both correct,
describing different denominators (all archive rows vs. candidate-kind
rows only); this document is the reference for which one a future table
means when it says "records."
