"""S1 — constraint-guided best-first search.

Shares S0's exact candidate universe (`enumerative.generate_level_candidates`
— same primitives, same bank, same deterministic base ordering) and its
exact-match criterion. The one real difference: at every depth level, only
the top `BEAM_WIDTH` newly-discovered terms *by priority* are carried into
the bank for the next level's expansions, rather than S0's unconstrained
growth. Under a fixed state budget this means S1 spends its deeper-level
budget on the most training-agreement-promising subprograms first, which is
exactly what "best-first" means for a search whose per-candidate cost
already requires full evaluation to score (`pruning.py`'s priority inputs
are computed from training agreement, not a cheap static heuristic).

Priority (lexicographic, all computed from training demonstrations only,
never a test output): (1) demonstrations exactly solved, descending;
(2) mean pixel agreement, descending; (3) dimension agreement fraction,
descending; (4) colour-set agreement, descending; (5) program cost,
ascending; (6) canonical serialization, ascending (deterministic
tie-break).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.gen002.dsl.program import Program
from src.gen002.dsl.types import Grid, Type
from src.gen002.search.cache import SearchCache
from src.gen002.search.enumerative import (
    SearchResult,
    generate_level_candidates,
    is_exact_match,
    literal_bank,
)
from src.gen002.search.pruning import MAX_DEPTH, colour_set_agreement, pixel_agreement

BEAM_WIDTH = 25


def _priority(program: Program, cache: SearchCache, train_outputs: tuple[Grid, ...]) -> tuple:
    if program.type_ != Type.GRID:
        # Non-Grid terms (ObjectSet, Colour, ...) cannot be scored against a
        # Grid target directly; ranked after every scoreable Grid candidate,
        # deterministically among themselves by cost then canonical form.
        return (-1, 0.0, 0.0, 0.0, -program.cost(), program.canonical())

    results = cache.evaluate_on_all(program)
    n_solved = 0
    pixel_scores = []
    dim_scores = []
    colour_scores = []
    for (status, value), target in zip(results, train_outputs):
        if status != "ok":
            pixel_scores.append(0.0)
            dim_scores.append(0.0)
            colour_scores.append(0.0)
            continue
        if value == target:
            n_solved += 1
        pixel_scores.append(pixel_agreement(value, target))
        same_shape = len(value) == len(target) and (not value or len(value[0]) == len(target[0]))
        dim_scores.append(1.0 if same_shape else 0.0)
        predicted_colours = frozenset(c for row in value for c in row)
        target_colours = frozenset(c for row in target for c in row)
        colour_scores.append(colour_set_agreement(predicted_colours, target_colours))

    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0  # noqa: E731 - local, one-line, not exported
    return (
        n_solved,
        mean(pixel_scores),
        mean(dim_scores),
        mean(colour_scores),
        -program.cost(),
        program.canonical(),
    )


@dataclass
class BestFirstResult(SearchResult):
    beam_sizes_by_depth: list[int] = field(default_factory=list)


def search_best_first(
    train_inputs: tuple[Grid, ...],
    train_outputs: tuple[Grid, ...],
    *,
    max_states: int,
    timeout_s: float,
) -> BestFirstResult:
    result = BestFirstResult()
    cache = SearchCache(train_inputs)
    bank = literal_bank()
    seen_signatures: set[tuple] = set()
    start = time.monotonic()

    for _depth in range(1, MAX_DEPTH + 1):
        scored: list[tuple[tuple, Program]] = []
        timed_out_this_level = False
        for candidate in generate_level_candidates(bank):
            if time.monotonic() - start > timeout_s:
                result.timed_out = True
                timed_out_this_level = True
                break
            if result.states_explored >= max_states:
                timed_out_this_level = True
                break
            result.states_explored += 1

            if cache.is_dead(candidate):
                result.n_dead += 1
                continue
            signature = cache.semantic_signature(candidate)
            if signature in seen_signatures:
                result.n_duplicate += 1
                continue
            seen_signatures.add(signature)

            if is_exact_match(candidate, cache, train_outputs):
                result.exact_programs.append(candidate)
            priority = _priority(candidate, cache, train_outputs)
            scored.append((priority, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        kept = scored[:BEAM_WIDTH]
        result.beam_sizes_by_depth.append(len(kept))
        for _priority_key, candidate in kept:
            bank[candidate.type_].append(candidate)

        if timed_out_this_level:
            break

    result.elapsed_s = time.monotonic() - start
    return result
