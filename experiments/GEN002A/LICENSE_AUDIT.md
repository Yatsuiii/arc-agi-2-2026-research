# GEN002-A — LICENSE_AUDIT

Licence status of every reference consulted in `RELATED_SYSTEMS_AUDIT.md`,
restated from `docs/REFERENCE_LICENSE_AUDIT.md` (project-wide, not
re-audited here) plus SOAR's own licence (not previously catalogued there,
added below).

| Reference | Licence | Class | Consequence for GEN002-A |
| --- | --- | --- | --- |
| Barbadillo `arc25` | `setup.py:20 license='All rights reserved'` | `RESEARCH REFERENCE ONLY` | May read and cite concepts (`RELATED_SYSTEMS_AUDIT.md`); no code, class, or function signature copied. |
| SOAR | `LICENSE.md`, MIT, Copyright (c) 2024 Julien Pourcel | `REUSABLE WITH ATTRIBUTION` | Permissively licensed, but not applicable — SOAR is an LLM-driven system and the acceptance message prohibits an LLM in this phase, so nothing from it is reused regardless of licence permissiveness. |
| ARChitects | Apache-2.0 (`docs/REFERENCE_LICENSE_AUDIT.md` §2) | `REUSABLE WITH ATTRIBUTION` | Not applicable (neural, not symbolic); no code reused. |
| NVARC | No LICENSE file | `RESEARCH REFERENCE ONLY` | Not applicable (neural, not symbolic); no code reused. |
| CompressARC | MIT, already vendored (`third_party/compressarc/`) | `REUSABLE WITH ATTRIBUTION` | Not imported by `src/gen002/` — GEN002-A never calls into CompressARC; the vendored copy is untouched by this phase. |
| BARC `seeds/common.py` | Unknown, not fetched into this workspace | `UNAVAILABLE` | Cannot be consulted or copied; not attempted. |
| Textbook algorithms (connected-component labelling, A*/best-first search, MDL, type-directed synthesis) | Public-domain algorithmic knowledge, not source-code-specific | n/a | Freely implementable from published descriptions; this is exactly the `RELATED_SYSTEMS_AUDIT.md` distinction between an idea and an expression. |

## Consolidated position

`src/gen002/` is a clean-room implementation. No line of code in this
package originates in any licensed-restrictively (or unverified-licence)
reference; every reused element is a general algorithmic technique
published outside any single local reference's specific codebase, per
`docs/REFERENCE_LICENSE_AUDIT.md`'s own `CLEAN-ROOM REIMPLEMENTATION
REQUIRED` category for `RESEARCH REFERENCE ONLY` material. This
classification is stronger than GEN001-A's position (which additionally
had to track a contaminated pretrained checkpoint's own licence) — there
is no checkpoint here, so there is no additional licence gate beyond
"was any code copied," and the answer is no.
