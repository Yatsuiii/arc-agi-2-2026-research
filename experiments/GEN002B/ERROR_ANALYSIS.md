# GEN002-B — ERROR_ANALYSIS

Fresh validation classification is derived from
`artifacts/GEN002B/offline_analysis.json`.

## Counts

| Category | Count |
| --- | ---: |
| Missing language | **22** |
| Search failure | **2** |
| Generalization failure | 0 |
| Representation failure | 0 |
| Success | 0 |

## Group breakdown

| Group | Missing language | Search failure | Success |
| --- | ---: | ---: | ---: |
| A2 | 12 | 0 | 0 |
| B2 | 4 | 2 | 0 |
| C2 | 6 | 0 | 0 |

The only bounded-search signal was in two Group-B2 indices
(`88a62173`, `c8b7cc0f`). No validation task produced an exact
demonstration-consistent program, so there is no generalization bucket to
study and no representation failure independently isolated by this pass.

## Outcome

The fresh validation null is therefore dominated by the same broad cause
as GEN002-A's old development pilot: language reachability, not candidate
ranking.
