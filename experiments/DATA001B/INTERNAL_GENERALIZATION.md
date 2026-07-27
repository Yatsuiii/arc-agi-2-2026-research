# DATA001-B — INTERNAL_GENERALIZATION

## Result

- Train/validation family-bucket disjointness: True
- Train buckets: 11
- Validation buckets: 11
- Validation tasks: 1250
- Direct-grid and trace parsing: PASS
- Provenance present on all selected tasks: True
- Family label consistency: True

The frozen split holds out family variants, scene seeds, and parameter draws through disjoint family buckets rather than random pair-level sampling. No near-duplicate train/validation admission was found under the frozen signatures.
