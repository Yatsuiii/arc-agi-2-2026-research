# GEN002-B — LEAKAGE_POLICY

## Allowed information during development

GEN002-B may use:

- ARC TRAIN and DEV tasks and outputs;
- the completed GEN002-A pilot only as development diagnostics;
- ACQ-001 metadata needed to freeze the fresh validation manifest;
- archived execution traces and bounded-search diagnostics from GEN002-A;
- local papers, reports, and code from mature symbolic systems;
- legal ground truth only after fresh validation generation completes.

## Forbidden information during generation

GEN002-B generation may not use:

- hidden outputs from the fresh 24-index validation manifest;
- GEN002-B validation correctness while tuning the DSL or search;
- any rerun of CompressARC on the validation sample;
- any learned verifier, correctness classifier, or confidence router;
- any Kaggle or external paid API service.

## Development-set conversion

The original GEN002-A 24-index pilot is labelled
`GEN002B_DEV_DIAGNOSTIC`. It may be used for:

- failure-family analysis;
- template design pressure;
- bounded-search diagnostics;
- runtime budgeting;
- negative engineering examples.

It may not be used as fresh held-out evidence for GEN002-B performance.

## Freeze points

1. Planning docs committed before implementation.
2. Fresh validation manifest committed before DSL redesign.
3. Frozen GEN002-B configuration committed after TRAIN/DEV benchmarking
   and before validation.
4. No DSL/search change after validation correctness is viewed.

## Auditability

Every generated artifact must carry enough metadata to reconstruct:

- which manifest was used;
- which frozen configuration ran;
- which indices completed;
- which candidates were emitted;
- how failures were categorized offline.
