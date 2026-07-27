# GEN002-B — LICENSE_AUDIT

GEN002-B reuses no third-party ARC solver code directly.

## References inspected

| Reference | Local path | Licence read | Reuse decision |
| --- | --- | --- | --- |
| SOAR | `references/paper_winners/02_soar/LICENSE.md` | MIT | Not reused: architecture depends on LLM-driven Python synthesis and is outside this phase's constraints |
| Barbadillo `arc25` | `references/score_winners/05_barbadillo/` | No explicit licence file located in the local checkout | Reference-only; clean-room design inspiration only |
| NVARC | `references/score_winners/01_nvarc/` | Mixed competition artifacts, not treated as clean reusable symbolic code | Not reused |
| ARChitects | `references/score_winners/02_architects/` | Report/docs only in local evidence | Not reused |
| CompressARC | `third_party/compressarc/` | MIT | Not rerun or modified for GEN002-B generation; used only as the already-frozen comparison target |

## Conclusion

GEN002-B's `src/gen002b/` is a clean-room implementation. The selected
architectural lineage is concept-level only; no function, class, or code
fragment was copied from Barbadillo, SOAR, NVARC, or ARChitects.
