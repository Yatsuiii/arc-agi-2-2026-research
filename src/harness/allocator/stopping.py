"""Per-task stopping rule: does this `VerificationResult` justify STOP?

A simple, fully specified rule-based policy, deliberately not learned —
`experiments/EXP002/PLAN.md` Gate 1 forbids building allocator policy around
verifier confidence before EXP002 has shown that confidence is decision-useful
at all. This module is the interface Phase 1 asks for; EXP003 is where a
stopping rule actually gets evaluated against replayed budget snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.harness.schemas import AllocationAction, AllocationDecision, VerificationResult


@dataclass
class StoppingRule:
    confidence_threshold: float = 0.8
    margin_threshold: float = 0.15

    def decide(
        self, task_id: str, verification: VerificationResult, remaining_budget_seconds: float
    ) -> AllocationDecision:
        top1 = verification.probability_correct.get(
            verification.ranked_grid_shas[0], 0.0
        ) if verification.ranked_grid_shas else 0.0
        confident = top1 >= self.confidence_threshold
        clear_margin = verification.confidence_margin >= self.margin_threshold

        if confident and clear_margin:
            return AllocationDecision(
                task_id=task_id,
                action=AllocationAction.STOP,
                expected_marginal_value=0.0,
                estimated_cost_seconds=0.0,
                reason=(
                    f"top1 P(correct)={top1:.3f} >= {self.confidence_threshold}, "
                    f"margin={verification.confidence_margin:.3f} >= {self.margin_threshold}"
                ),
            )
        if remaining_budget_seconds <= 0:
            return AllocationDecision(
                task_id=task_id,
                action=AllocationAction.STOP,
                expected_marginal_value=0.0,
                estimated_cost_seconds=0.0,
                reason="no remaining budget",
            )
        return AllocationDecision(
            task_id=task_id,
            action=AllocationAction.MORE_NVARC,
            expected_marginal_value=1.0 - top1,
            estimated_cost_seconds=remaining_budget_seconds,
            reason=(
                f"top1 P(correct)={top1:.3f} below threshold or margin unclear "
                "(interface-only: MORE_NVARC has no executor, see allocator/actions.py)"
            ),
        )
