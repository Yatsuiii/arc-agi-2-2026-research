# DATA001-A — SYNTHETIC_SYSTEMS_AUDIT

## Audited lineages

| System | Dataset origin | Representation | Generation mechanism | Curriculum | Dedup / contamination control | Licence / reuse status | Reusable takeaway |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NVARC | Massive synthetic mixture plus contaminated ARC-derived fine-tuning sets | Natural-language summaries plus executable input/output generators | Programmatic SDG with executable checking | Broad synthetic mix, strong scale bias | Some filtering, but clean-room reuse blocked by provenance | Reference only; do not copy data or code into DATA001-A | Executable task generation and validation are the right backbone |
| ARChitects | Synthetic and curated tasks with heavy human/VLM filtering | Visual/program hybrids | Generation plus quality filtering | Less auditable than NVARC | Weak reproducibility; overfitting risk documented by authors | Reference only | Quality gates matter more than volume alone |
| TRM | Generated algorithmic curricula | Direct grid modeling | Generator families designed around recursive reasoning | Strong staged curriculum | Clean evaluation but not an ARC-specific SDG reuse path | Reference only | Small-model pilot should stay tightly scoped |
| SOAR | MIT-licensed synthetic program-synthesis data | Program traces + outputs | Hindsight-relabeled synthetic synthesis tasks | Heavy search/LLM emphasis | Clean provenance, but solve-time architecture mismatched | MIT reference, no direct code reuse needed | Structured auxiliary supervision is viable |
| CompressARC | Real ARC tasks only, no synthetic pipeline | Direct output grids | No synthetic generation | None | Clean evaluation discipline | Reference only | Use as frozen comparison target, not a data source |
| BARC / Barbadillo materials | ARC-like and search-centric corpora | Mixed symbolic representations | Solver-centric, not a clean synthetic curriculum | Limited | Licence restrictions / unavailable assets | Reference only | Object-centric abstractions are useful, but reuse is not clean |

## Decision

Selected architecture: Clean-room structured scene generator + typed transformation AST + executable validation, inspired by NVARC's executable SDG discipline but reimplemented without NVARC code or data reuse.
