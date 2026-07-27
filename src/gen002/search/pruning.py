"""Frozen search-budget constants and the pruning checks both S0 and S1 share.

Every constant here is fixed by `experiments/GEN002A/SEARCH_PROTOCOL.md`,
committed before Phase 6 ran.
"""

from __future__ import annotations

from src.gen002.dsl.types import Type

MAX_DEPTH = 3
MAX_COST = 12

LITERAL_POOLS: dict[Type, tuple] = {
    Type.COLOUR: tuple(range(10)),
    Type.INTEGER: (1, 2, 3),
}
"""Literal value pools for leaf-node construction. `Coordinate` and
`Direction` literal pools live in `enumerative.py` (they need
`dsl.types.DIRECTIONS` and a small coordinate set) — kept there rather
than duplicated here since nothing else needs them."""


def within_budget(program_cost: int, program_depth: int) -> bool:
    return program_cost <= MAX_COST and program_depth <= MAX_DEPTH


def shape_agreement(predicted_shape: tuple[int, int], target_shape: tuple[int, int]) -> bool:
    return predicted_shape == target_shape


def colour_set_agreement(predicted_colours: frozenset[int], target_colours: frozenset[int]) -> float:
    if not target_colours:
        return 1.0 if not predicted_colours else 0.0
    return len(predicted_colours & target_colours) / len(target_colours)


def pixel_agreement(predicted, target) -> float:
    """Fraction of cells that match, over the *target's* shape. A shape
    mismatch is scored 0.0 rather than raising — this is a priority-score
    input, not a correctness check (Phase 5's exact-match gate is
    separate, `search/enumerative.py::is_exact_match`)."""
    if len(predicted) != len(target) or (predicted and len(predicted[0]) != len(target[0])):
        return 0.0
    total = sum(len(row) for row in target)
    if total == 0:
        return 1.0
    matches = sum(
        1 for pr, tr in zip(predicted, target) for pc, tc in zip(pr, tr) if pc == tc
    )
    return matches / total
