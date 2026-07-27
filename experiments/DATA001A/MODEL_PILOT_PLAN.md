# DATA001-A — MODEL_PILOT_PLAN

## MODEL001-A (prepared, not launched)

Compare exactly three tracks later, after quota resets:

1. one clean approximately 4B-class open model under direct-grid supervision;
2. one smaller clean control;
3. the historical NVARC Qwen3-4B lineage only as a contamination-labelled competition control.

## Primary evaluation

- clean task-grouped validation split;
- candidate oracle;
- top-1 and top-2 exact-grid accuracy;
- malformed-output rate;
- incremental coverage over CompressARC;
- runtime / VRAM / cost.

## Training variants

- direct-grid only;
- direct-grid plus structured-trace auxiliary supervision.
