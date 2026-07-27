# DATA001-A — TARGET_REPRESENTATION

## T0 — Direct grid target

- Input: visible demonstration pairs plus one test input serialized as deterministic ARC text.
- Output: one exact test-output grid serialized as JSON nested lists.
- Primary use: candidate generation and top-k decoding.

## T1 — Structured trace auxiliary target

- Input: the same prompt context.
- Output: typed operation sequence, parameter bindings, and intermediate grids derived from the synthetic program.
- Primary use: optional multitask supervision.

## Serialization

- Grids: canonical JSON nested lists.
- Tasks: canonical JSON records.
- Programs: typed operation dictionaries; no free-form Python target is used.
