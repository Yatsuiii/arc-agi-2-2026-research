from __future__ import annotations

from dataclasses import dataclass

from src.gen002b.core import ArcTask, infer_background


@dataclass(frozen=True)
class SearchConstraints:
    background_hypotheses: tuple[int, ...]
    connectivity_hypotheses: tuple[int, ...]
    exact_dimension_relation: str | None


def derive_constraints(task: ArcTask) -> SearchConstraints:
    relations = set()
    for pair in task.train_pairs:
        ih, iw = len(pair.input_grid), len(pair.input_grid[0]) if pair.input_grid else 0
        oh, ow = len(pair.output_grid), len(pair.output_grid[0]) if pair.output_grid else 0
        if (ih, iw) == (oh, ow):
            relations.add("same")
        elif oh * ow > ih * iw:
            relations.add("larger")
        else:
            relations.add("smaller")
    relation = next(iter(relations)) if len(relations) == 1 else None
    return SearchConstraints(
        background_hypotheses=infer_background(task),
        connectivity_hypotheses=(4, 8),
        exact_dimension_relation=relation,
    )
