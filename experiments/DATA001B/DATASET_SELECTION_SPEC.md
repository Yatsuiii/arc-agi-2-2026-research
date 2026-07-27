# DATA001-B — DATASET_SELECTION_SPEC

## Selection problem

The pool is not the training corpus. DATA001-B freezes a deterministic
selection objective before coverage is measured.

## Frozen objective

Select a subset `S` from the valid pool that maximizes:

`score(S) = 4.0 * descriptor_coverage(S)
          + 2.5 * family_balance(S)
          + 1.5 * depth_balance(S)
          + 1.5 * diversity_gain(S)
          + 1.0 * difficulty_balance(S)
          - 1.5 * token_cost_penalty(S)
          - 3.0 * near_duplicate_penalty(S)`

under:

- corpus size in `8000-12000`;
- direct-grid token budget under `24,000,000`;
- minimum family quotas;
- minimum depth quotas;
- family-disjoint validation buckets.

## Frozen deterministic algorithm

1. Remove exact and near duplicates.
2. Allocate minimum quotas by family and effective depth.
3. Fill rare descriptor bins first.
4. Within eligible candidates, greedily add the highest marginal
   `score(S ∪ {x}) - score(S)` item.
5. Apply a token penalty that rises after the current mean token cost
   exceeds the frozen target.
6. Freeze when size and token ceilings are met.

## Near-duplicate rule

Two tasks are near-duplicates if they share:

- family bucket;
- effective depth;
- panel mode;
- high-level descriptor bin;
- and their scene-graph / delta / trace signatures agree.

Only one enters the final corpus unless rare-family minimums would
otherwise fail.
