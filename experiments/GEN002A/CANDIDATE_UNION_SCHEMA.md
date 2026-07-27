# GEN002-A — CANDIDATE_UNION_SCHEMA

Phase 9 defines a generator-neutral candidate-set interface. It does not
run a selector and does not change the Phase 7 result.

## Identity

One union record is identified by:

```
(task_id, test_index, grid_sha1)
```

`grid_sha1` is recomputed from the normalized grid with
`src.run001.archive.grid_digest`; a source-provided digest is never trusted
as grid identity. Exact grid equality is the only merge rule. Similar
grids are not clustered.

## Record

```json
{
  "task_id": "string",
  "test_index": 0,
  "grid": [[0]],
  "grid_sha1": "16 hex characters",
  "provenance": [
    {
      "generator_id": "compressarc | nvarc | gen002_program_synthesis",
      "source_record_id": "source-local identity",
      "metadata": {}
    }
  ]
}
```

When two generators emit an identical grid for the same test-index, one
union record retains both provenance entries. Identical grids on different
test-indices never merge. Source-specific metadata remains namespaced
inside its provenance entry.

## Adapters

`src/gen002/candidate_union.py` provides adapters for the three candidate
record shapes currently relevant to the project:

- CompressARC/ACQ-001: grid field `grid`;
- NVARC/GEN001-A: grid field `grid`;
- GEN002-A program synthesis: grid field `candidate_grid`.

The normalized outer schema has no rank, confidence, native score, or
selected flag. Source scores may remain in provenance metadata for audit,
but the union operation never reads them. Choosing two submission attempts
from a non-empty union is a separate future selection question and is not
smuggled into this phase.
