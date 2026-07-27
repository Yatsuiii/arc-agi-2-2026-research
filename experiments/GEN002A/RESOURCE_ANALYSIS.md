# GEN002-A — RESOURCE_ANALYSIS

GEN002-A consumed local CPU only: no Kaggle session, GPU, paid API, or
network service.

| Stage | Measured work |
| --- | ---: |
| S0 search, sum over 24 tasks | 23.565 CPU-seconds |
| S1 search, sum over 24 tasks | 31.537 CPU-seconds |
| Parallel Phase 6 pilot wall-clock | 16.11 seconds |
| Phase 8 diagnostic rerun wall-clock | approximately 35 seconds |
| Candidate artifacts | 0 records (two valid empty gzip streams) |
| Search states | 960,000 total (20,000 x 24 x 2 policies) |
| Wall-clock timeouts | 0/48 |

The search state cap bound compute much more tightly than the declared
20s/45s wall-clock caps. Maximum observed per-task runtime was 2.605s for
S0 and 4.977s for S1. The pilot therefore used under 1% of its 26-minute
aggregate worst-case wall-clock envelope.

The Phase 8 diagnostic rerun repeats only S1 with identical frozen search
parameters and records training-agreement summaries. It does not generate
a new candidate corpus or access ground truth during search.
