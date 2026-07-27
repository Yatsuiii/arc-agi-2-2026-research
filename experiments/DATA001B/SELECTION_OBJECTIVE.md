# DATA001-B — SELECTION_OBJECTIVE

Frozen objective: `frozen_greedy_quota_diversity_token_penalty_v1`

Selection operates on the generated pool under a direct-grid token budget of `24000000` tokens. The deterministic greedy score combines:

1. family quotas;
2. depth quotas with target accepted mix 40% depth-1 / 40% depth-2 / 20% depth-3;
3. descriptor diversity pressure;
4. near-duplicate rejection;
5. token-cost penalty;
6. minimum representation of rarer executable families;
7. fixed validation-family buckets disjoint from train buckets.

The frozen execution selected `7031` tasks (`5781` train / `1250` validation) at `23998861` direct-grid tokens and `21175872` trace tokens.
