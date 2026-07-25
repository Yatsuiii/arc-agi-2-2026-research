"""value(task, action) = expected probability-of-correctness gain / expected seconds.

The Phase-5 scheduling objective, implemented once so `global_scheduler.py`
and any future EXP004 code share one formula rather than reimplementing it.
"""

from __future__ import annotations


def marginal_value(
    current_top1_probability: float,
    estimated_probability_after_action: float,
    estimated_cost_seconds: float,
) -> float | None:
    """Expected accuracy gain per second of additional compute.

    `None` when `estimated_cost_seconds <= 0` — a free action has an
    undefined value-per-second, not infinite value, and callers must not
    treat `None` as "always do this."
    """
    if estimated_cost_seconds <= 0:
        return None
    gain = estimated_probability_after_action - current_top1_probability
    return gain / estimated_cost_seconds


def rank_actions_by_value(candidates: list[dict]) -> list[dict]:
    """Sort `{"task_id", "action", "value", ...}` dicts by value, best first.

    Entries whose `"value"` is `None` (undefined marginal value) sort last,
    never first — an undefined value must not be preferred over a measured
    one just because `None` compares oddly.
    """
    return sorted(candidates, key=lambda c: (c["value"] is None, -(c["value"] or 0.0)))
