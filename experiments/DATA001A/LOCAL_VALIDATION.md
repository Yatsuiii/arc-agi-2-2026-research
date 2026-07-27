# DATA001-A — LOCAL_VALIDATION

## Checks run

- dataset iteration
- direct-grid and structured-trace example building
- tokenizer-length statistics
- balanced batching
- config hashing and checkpoint stub writing
- candidate export
- mock generation and malformed-output accounting

## Results

| Check | Result |
| --- | --- |
| New DATA001/model001 tests | 5 passed |
| Direct-grid train examples | 4316 |
| Direct+trace train examples | 8632 |
| Validation direct examples | 1684 |
| Direct-grid mean / p95 / max tokens | 2022.19 / 3562 / 5379 |
| Direct+trace mean / p95 / max tokens | 2291.52 / 4007 / 6412 |
| Mock top-1 accuracy on sampled validation | 1.000 |
| Mock malformed outputs | 14 |
| Frozen config hash | `7408a15bfbb7bc7ab7a2235062ec4761d5d2b382a9992103f5675cda31206db9` |

The mock path is intentionally deterministic and local; no substantial model was downloaded or trained.
