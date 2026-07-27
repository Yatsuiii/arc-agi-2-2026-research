# DATA001-A — HARDWARE_PROJECTION

## Sequence statistics

- Train direct mean tokens: 2022.19
- Train direct p95 tokens: 3562
- Train direct+trace mean tokens: 2291.52
- Train direct+trace p95 tokens: 4007

## Projected pilot cost

- 3-epoch direct-grid pilot token budget: ~26,183,316 tokenizer-units
- 2-epoch direct+trace pilot token budget: ~39,560,801 tokenizer-units
- Approximate runtime envelope: {"single_24gb_qlora_4b_estimate": "4-8h", "kaggle_2xt4_qlora_4b_estimate": "6-10h", "smaller_control_estimate": "2-4h"}

## Feasibility call

A bounded QLoRA-style 4B-class pilot is operationally feasible once GPU quota is available. The structured-trace track should remain optional because it is materially longer than direct-grid supervision.
