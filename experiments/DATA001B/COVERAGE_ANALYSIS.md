# DATA001-B — COVERAGE_ANALYSIS

Coverage is reported with the frozen V2 descriptor system. ACQ-001 and CompressARC comparisons are descriptive/transductive only and do not establish clean generalization.

| Reference set | A unique | A weighted | A mean dist | B pool unique | B pool weighted | B pool mean dist | B selected unique | B selected weighted | B selected mean dist |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARC TRAIN | 0.269 | 0.169 | 1.649 | 0.214 | 0.118 | 1.898 | 0.208 | 0.116 | 1.938 |
| Clean DEV | 0.261 | 0.147 | 1.616 | 0.256 | 0.142 | 1.857 | 0.251 | 0.138 | 1.893 |
| ACQ-001 full | 0.263 | 0.159 | 1.712 | 0.281 | 0.129 | 1.886 | 0.281 | 0.128 | 1.930 |
| CompressARC 129 failures | 0.252 | 0.153 | 1.717 | 0.319 | 0.148 | 1.840 | 0.319 | 0.147 | 1.887 |

## Largest remaining gaps on CompressARC failures

[
  {
    "descriptor": [
      "contract",
      "9-10",
      "11+",
      "affected_4",
      "contain_depth_1"
    ],
    "count": 4
  },
  {
    "descriptor": [
      "same",
      "9-10",
      "11+",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 4
  },
  {
    "descriptor": [
      "same",
      "7-8",
      "7-10",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  },
  {
    "descriptor": [
      "contract",
      "3-4",
      "7-10",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  },
  {
    "descriptor": [
      "same",
      "3-4",
      "2-3",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  },
  {
    "descriptor": [
      "same",
      "7-8",
      "4-6",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  },
  {
    "descriptor": [
      "contract",
      "5-6",
      "7-10",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  },
  {
    "descriptor": [
      "same",
      "5-6",
      "11+",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  }
]

## Largest remaining gaps on ACQ-001

[
  {
    "descriptor": [
      "same",
      "5-6",
      "11+",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 6
  },
  {
    "descriptor": [
      "same",
      "9-10",
      "11+",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 6
  },
  {
    "descriptor": [
      "contract",
      "9-10",
      "11+",
      "affected_4",
      "contain_depth_1"
    ],
    "count": 5
  },
  {
    "descriptor": [
      "contract",
      "5-6",
      "7-10",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 5
  },
  {
    "descriptor": [
      "same",
      "3-4",
      "2-3",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 4
  },
  {
    "descriptor": [
      "same",
      "7-8",
      "4-6",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 4
  },
  {
    "descriptor": [
      "same",
      "7-8",
      "7-10",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  },
  {
    "descriptor": [
      "same",
      "9-10",
      "7-10",
      "affected_4",
      "contain_depth_0"
    ],
    "count": 3
  }
]
