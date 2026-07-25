"""B0 — the frozen NVARC selection, replayed unchanged.

This is what `config.HarnessConfig.frozen_baseline` mode delegates to: with
this verifier, `runner.py`'s top-2 output must equal RUN-001's own
`submission.json` exactly, for every task it was run on
(`experiments/RUN001/VALIDATION_REPORT.md`'s "Selected-grid identity vs
archive" check already proves the archive itself is internally consistent
with the submission; this verifier is what replays that consistency inside
the harness).
"""

from __future__ import annotations

from src.harness.schemas import TaskEvidence, VerificationResult
from src.harness.verifier.base import Verifier, build_result


class OriginalSelectionVerifier(Verifier):
    name = "B0_original_nvarc"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        rank_by_grid = {r.grid_sha1: r.rank for r in evidence.candidate_set.selection}
        if not rank_by_grid:
            return build_result(evidence.task_id, evidence.test_index, {}, self.name)
        # 1/rank is monotonic in the archived rank, so softmax(scores) preserves
        # NVARC's own order exactly; it is a rank-derived proxy, not a claim
        # that NVARC's selector emits calibrated probabilities.
        scores = {sha1: 1.0 / rank for sha1, rank in rank_by_grid.items()}
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)
