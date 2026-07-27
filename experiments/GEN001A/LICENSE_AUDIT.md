# GEN001-A — LICENSE_AUDIT

Licence status specific to the restored NVARC-lineage branch
(`NVARC_LINEAGE_AUDIT.md`), extracted and cross-referenced from the
project-wide `docs/REFERENCE_LICENSE_AUDIT.md` (§1, §6, §9) — not a
re-audit, a restatement scoped to exactly the components GEN001-A touches.

| Component | Licence | Class | Consequence for GEN001-A |
| --- | --- | --- | --- |
| NVARC repository (`references/score_winners/01_nvarc`) | No LICENSE file, no SPDX, no per-file header | `RESEARCH REFERENCE ONLY` / `CLEAN-ROOM REIMPLEMENTATION REQUIRED` | May read and cite for lineage/audit purposes (done, `NVARC_LINEAGE_AUDIT.md`); **no code from it may enter `src/gen001/`**. |
| ARChitects-derived `arc_loader.py` inside the 2026 T4x2 notebook | Apache-2.0 at the ARChitects source, **notice stripped** in the notebook | `REUSABLE WITH ATTRIBUTION` at the true source, licence-hygiene violation as shipped | If GEN001-A's adapter needs equivalent loading logic, it is written fresh against `src/harness/schemas.py`'s own types, not copied from the notebook. |
| Base model, Qwen3-4B-Thinking-2507 | Apache-2.0 (Alibaba) | `REUSABLE WITH ATTRIBUTION` | Clean at the base-model layer. |
| Fine-tuned checkpoint `sorokin/qwen3_4b_grids15_sft139` | **No licence field exposed by the Kaggle API for model instances** | `UNCLEAR — NEEDS AUTHOR CLARIFICATION` (per `docs/REFERENCE_LICENSE_AUDIT.md` §9 item 18) | **Blocking for any paper publication claim built on this checkpoint's outputs**; not blocking for a private, unpublished pilot run. |
| 2026 T4x2 baseline notebook itself | No licence statement in notebook or `kernel-metadata.json` | `UNCLEAR` | Same as above — private-use only until resolved. |
| Offline-wheel dependency notebook (`sorokin/pip-install-unsloth-flash-patch`) | Not stated | `UNCLEAR` | Contents audited, not vendored; not redistributed by GEN001-A. |
| TRM (not used — branch 1 only, `NVARC_LINEAGE_AUDIT.md`) | MIT | n/a | Not applicable; TRM branch is absent from the restored configuration. |
| Unsloth, xformers, bitsandbytes, torch | Respective upstream OSS licences | `REUSABLE WITH ATTRIBUTION` (standard OSS dependency use) | Not modified, used as pinned by the Kaggle image. |

## Consolidated position for this phase

1. Static analysis, lineage documentation, and a **private, unpublished**
   pilot build/run are permitted under the existing `RESEARCH REFERENCE
   ONLY` classification — this mirrors exactly how `docs/NVARC_2026_T4_BASELINE_AUDIT.md`
   and RUN-001 itself were already conducted and is not a new policy.
2. **No result derived from this checkpoint may be presented as clean paper
   evidence** until the checkpoint's own licence is resolved — this is
   independent of, and additive to, the contamination gate in
   `CONTAMINATION_POLICY.md`. Either gate alone is sufficient to block a
   paper claim; both currently apply.
3. No code is copied from `references/score_winners/01_nvarc` or the 2026
   T4x2 notebook into `src/gen001/`. The adapter (Phase 6) is original code
   against this repository's own `Candidate`/`CandidateArchive` schema,
   parametrised by configuration (checkpoint path, generation parameters)
   rather than by copied solver logic.

No new licence finding changes any existing entry in
`docs/REFERENCE_LICENSE_AUDIT.md`; this document only scopes those findings
to what GEN001-A specifically needs to track before building a pilot.
