"""Global scheduler: pick the single best next action across every open task.

Phase 1's requirement is that the allocator "operate globally rather than
independently stopping each task" (Phase 5). This module is that interface —
`best_next_action` looks at every task's current state at once — kept simple
because Gate 1 blocks building real allocation policy around verifier
confidence until EXP002 shows that confidence is decision-useful
(`experiments/EXP002/PLAN.md`). No EXP004 code calls this yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.harness.allocator.marginal_value import marginal_value, rank_actions_by_value
from src.harness.allocator.stopping import StoppingRule
from src.harness.schemas import AllocationAction, AllocationDecision, TaskState


@dataclass
class GlobalScheduler:
    stopping_rule: StoppingRule = field(default_factory=StoppingRule)
    total_budget_seconds: float = 0.0
    spent_seconds: float = 0.0

    @property
    def remaining_seconds(self) -> float:
        return max(self.total_budget_seconds - self.spent_seconds, 0.0)

    def decisions_for(self, task_states: dict[str, TaskState]) -> list[AllocationDecision]:
        """One `StoppingRule` decision per open task, evaluated independently.

        Independent decisions are the input the global step below ranks; they
        are not themselves "global" — see `best_next_action`.
        """
        decisions = []
        for task_id, state in task_states.items():
            if state.stopped:
                continue
            for test_index, verification in state.verification.items():
                decisions.append(
                    self.stopping_rule.decide(task_id, verification, self.remaining_seconds)
                )
        return decisions

    def best_next_action(self, task_states: dict[str, TaskState]) -> AllocationDecision | None:
        """The single highest-marginal-value non-STOP action across all open tasks.

        Returns `None` when every open task's `StoppingRule` says STOP, or
        when no task has an open verification yet — there is nothing left to
        allocate additional compute to.
        """
        decisions = self.decisions_for(task_states)
        actionable = [d for d in decisions if d.action != AllocationAction.STOP]
        if not actionable:
            return None
        ranked = rank_actions_by_value(
            [
                {
                    "task_id": d.task_id,
                    "action": d.action,
                    "value": marginal_value(
                        current_top1_probability=1.0 - d.expected_marginal_value,
                        estimated_probability_after_action=1.0,
                        estimated_cost_seconds=d.estimated_cost_seconds,
                    ),
                    "decision": d,
                }
                for d in actionable
            ]
        )
        return ranked[0]["decision"]
