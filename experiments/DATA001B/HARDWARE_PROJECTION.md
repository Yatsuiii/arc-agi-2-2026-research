# DATA001-B — HARDWARE_PROJECTION

## Sequence statistics

- Direct-grid tokens: mean 3413.29, median 3221, p90 4571, p95 4922, max 6421
- Structured-trace tokens: mean 3011.79, median 2777, p90 4157, p95 4527, max 5824

## 4B QLoRA projection

- Training tokens, direct-grid train split: 20399491
- Training tokens, direct+trace train split: 18071336
- Expected VRAM: 15-16 GiB
- Single T4 direct-grid epoch-equivalent runtime: ~4.72 hours
- Two T4 direct-grid epoch-equivalent runtime: ~2.7 hours
- Single T4 direct+trace epoch-equivalent runtime: ~8.91 hours
- Checkpoint storage allowance: ~5.5 GiB

This remains operationally feasible for a bounded future 4B-class QLoRA pilot once quota is available.
