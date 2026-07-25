from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.allocator.actions import (  # noqa: E402
    EXECUTABLE_ACTIONS,
    ActionNotExecutable,
    require_executable,
)
from src.harness.allocator.global_scheduler import GlobalScheduler  # noqa: E402
from src.harness.allocator.marginal_value import (  # noqa: E402
    gain_per_cost,
    marginal_value,
    rank_actions_by_value,
)
from src.harness.allocator.stopping import StoppingRule  # noqa: E402
from src.harness.schemas import AllocationAction, TaskState, VerificationResult  # noqa: E402


# -- actions ---------------------------------------------------------------------


def test_only_stop_is_executable():
    assert EXECUTABLE_ACTIONS == frozenset({AllocationAction.STOP})


def test_require_executable_passes_for_stop():
    require_executable(AllocationAction.STOP)  # must not raise


def test_require_executable_raises_for_everything_else():
    with pytest.raises(ActionNotExecutable):
        require_executable(AllocationAction.RUN_TRM)


# -- stopping ----------------------------------------------------------------------


def make_verification(top1, margin):
    return VerificationResult(
        task_id="t",
        test_index=0,
        ranked_grid_shas=["a", "b"],
        probability_correct={"a": top1, "b": top1 - margin},
        uncertainty=1 - margin,
        confidence_margin=margin,
    )


def test_stopping_rule_stops_when_confident_and_clear_margin():
    rule = StoppingRule(confidence_threshold=0.8, margin_threshold=0.1)
    decision = rule.decide("t", make_verification(0.9, 0.3), remaining_budget_seconds=100)
    assert decision.action == AllocationAction.STOP


def test_stopping_rule_continues_when_unsure():
    rule = StoppingRule(confidence_threshold=0.8, margin_threshold=0.1)
    decision = rule.decide("t", make_verification(0.4, 0.05), remaining_budget_seconds=100)
    assert decision.action == AllocationAction.MORE_NVARC


def test_stopping_rule_stops_when_out_of_budget_regardless_of_confidence():
    rule = StoppingRule()
    decision = rule.decide("t", make_verification(0.1, 0.0), remaining_budget_seconds=0)
    assert decision.action == AllocationAction.STOP


def test_stopping_rule_handles_no_ranked_candidates():
    verification = VerificationResult(
        task_id="t", test_index=0, ranked_grid_shas=[], probability_correct={},
        uncertainty=1.0, confidence_margin=0.0,
    )
    rule = StoppingRule()
    decision = rule.decide("t", verification, remaining_budget_seconds=100)
    assert decision.action == AllocationAction.MORE_NVARC


# -- marginal value ------------------------------------------------------------------


def test_marginal_value_none_for_zero_cost():
    assert marginal_value(0.5, 0.9, 0.0) is None


def test_marginal_value_positive_gain():
    assert marginal_value(0.5, 0.9, 4.0) == pytest.approx(0.1)


def test_gain_per_cost_none_for_zero_cost():
    assert gain_per_cost(0.4, 0.0) is None


def test_gain_per_cost_matches_marginal_value_for_the_same_gain():
    assert gain_per_cost(0.4, 4.0) == marginal_value(0.5, 0.9, 4.0)


def test_rank_actions_by_value_sorts_descending_and_none_last():
    candidates = [
        {"value": 0.1}, {"value": 0.9}, {"value": None}, {"value": 0.5},
    ]
    ranked = rank_actions_by_value(candidates)
    assert [c["value"] for c in ranked] == [0.9, 0.5, 0.1, None]


# -- global scheduler ------------------------------------------------------------------


def test_global_scheduler_returns_none_when_all_tasks_confident():
    scheduler = GlobalScheduler(stopping_rule=StoppingRule(confidence_threshold=0.5, margin_threshold=0.0))
    state = TaskState(task_id="t", verification={0: make_verification(0.9, 0.5)})
    assert scheduler.best_next_action({"t": state}) is None


def test_global_scheduler_returns_a_decision_when_uncertain():
    scheduler = GlobalScheduler(
        stopping_rule=StoppingRule(confidence_threshold=0.99, margin_threshold=0.99),
        total_budget_seconds=1000,
    )
    state = TaskState(task_id="t", verification={0: make_verification(0.4, 0.1)})
    decision = scheduler.best_next_action({"t": state})
    assert decision is not None
    assert decision.task_id == "t"


def test_global_scheduler_ignores_stopped_tasks():
    scheduler = GlobalScheduler(stopping_rule=StoppingRule(confidence_threshold=0.99, margin_threshold=0.99))
    state = TaskState(task_id="t", verification={0: make_verification(0.4, 0.1)}, stopped=True)
    assert scheduler.best_next_action({"t": state}) is None


def test_global_scheduler_remaining_seconds_never_negative():
    scheduler = GlobalScheduler(total_budget_seconds=10, spent_seconds=50)
    assert scheduler.remaining_seconds == 0.0
