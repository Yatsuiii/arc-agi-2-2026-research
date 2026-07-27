# GEN002-B — RESULTS

## Verdict

**FREEZE SYMBOLIC RESEARCH**

GEN002-B froze a fresh 24-index validation manifest, replaced GEN002-A's
flat DSL surface with a narrow typed V2 plus template-first search, and
evaluated that frozen configuration exactly once on the fresh held-out
pilot. It still emitted zero candidates, found zero exact
demonstration-consistent programs, rescued zero Group-A2 generation
failures, and left the CompressARC union oracle unchanged at 12/24.

This does **not** reject program synthesis as a family. It rejects the
executed GEN002-B redesign under its frozen CPU-only language and search
configuration.

## Primary metrics

| Metric | Result |
| --- | ---: |
| Validation indices completed | 24/24 |
| Indices producing candidates | 0/24 |
| Exact programs discovered | 0 |
| Unique candidates | 0 |
| Group-A2 rescues | 0/12 |
| Group-B2 rescues | 0/6 |
| Group-C2 successes | 0/6 |
| GEN002-B oracle | 0/24 |
| CompressARC oracle | 12/24 |
| CompressARC + GEN002-B union oracle | 12/24 |
| Incremental solved indices | 0 |

## Benchmark context

Before validation, the frozen 50-train / 25-dev benchmark already showed a
weak expressivity surface:

- 2/75 tasks with any exact program;
- 2/95 held-out benchmark test indices solved;
- 85 benchmark misses classified `missing_language`;
- 8 benchmark misses classified `search_failure`.

Only one exact hit came from the new template surface (`uniform_scale`);
the other came from the bounded legacy fallback search.

## Interpretation

The fresh validation outcome is a clean null:

- candidates emitted for fewer than 4/24 indices;
- zero Group-A2 rescues;
- missing-language still dominant.

That matches the preregistered null criterion exactly. No further
language-expansion or search-tuning iteration is justified on this branch.
