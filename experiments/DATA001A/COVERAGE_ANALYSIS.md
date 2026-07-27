# DATA001-A — COVERAGE_ANALYSIS

## Summary

Synthetic descriptor coverage is measured against legal offline descriptors only.

| Reference set | Unique descriptor coverage | Weighted descriptor coverage | Mean nearest-structure distance |
| --- | ---: | ---: | ---: |
| ARC TRAIN | 0.117 | 0.145 | 1.754 |
| ACQ-001 held-out | 0.140 | 0.087 | 1.910 |
| CompressARC 129 generation-failure indices | 0.111 | 0.047 | 1.977 |
| CompressARC 42 oracle-hit indices | 0.156 | 0.214 | 1.714 |

## Interpretation

- The synthetic pilot covers a broader descriptor surface than the frozen symbolic line because it spans 11 executable families, 4 curriculum tiers in the accepted set, and both 1-step and 2-step compositions.
- Coverage remains best on `same` and moderate-size object-centric tasks.
- The main uncovered held-out descriptors are still larger output expansions, high-colour-count scenes, and denser multi-object layouts.

## Largest remaining gaps

[
  {
    "descriptor": [
      "same",
      "145+",
      "7+",
      "7+",
      "shape-preserve"
    ],
    "count": 15
  },
  {
    "descriptor": [
      "same",
      "145+",
      "7+",
      "4-6",
      "shape-preserve"
    ],
    "count": 11
  },
  {
    "descriptor": [
      "smaller",
      "145+",
      "7+",
      "7+",
      "output-change"
    ],
    "count": 11
  },
  {
    "descriptor": [
      "same",
      "145+",
      "3-4",
      "7+",
      "shape-preserve"
    ],
    "count": 10
  },
  {
    "descriptor": [
      "same",
      "145+",
      "5-6",
      "7+",
      "shape-preserve"
    ],
    "count": 8
  }
]
