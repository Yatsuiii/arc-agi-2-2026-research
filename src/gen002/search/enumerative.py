"""S0 — deterministic cost-ordered enumerative program search.

Bottom-up bank construction (Udupa et al. 2013-style bottom-up synthesis;
`experiments/GEN002A/RELATED_SYSTEMS_AUDIT.md` states this is a
clean-room implementation of a published, general technique): maintain a
type-indexed bank of already-constructed terms, and at each depth level
generate every well-typed primitive application over the current bank,
evaluate it, prune, and add survivors to the bank for the next level.

S0 never reorders candidates by training agreement — it processes
primitives in sorted-name order and argument combinations in
canonical-sorted order, deterministically, level by level. This is what
"no heuristic beam" means for a search whose branching factor still
requires *some* enumeration order to be deterministic at all.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

from src.gen002.dsl.primitives import PRIMITIVES
from src.gen002.dsl.program import Program, make_call, make_input, make_literal
from src.gen002.dsl.types import DIRECTIONS, Coordinate, Grid, Type
from src.gen002.search.cache import SearchCache
from src.gen002.search.pruning import LITERAL_POOLS, MAX_DEPTH, within_budget

COORDINATE_LITERALS: tuple[Coordinate, ...] = (Coordinate(0, 0),)
"""Deliberately a single literal — a richer coordinate pool multiplies
branching factor by up to 900 (30x30 grids) for one primitive
(`draw_line`). Declared here, not silently sized down elsewhere."""


@dataclass
class SearchResult:
    exact_programs: list[Program] = field(default_factory=list)
    states_explored: int = 0
    n_dead: int = 0
    n_duplicate: int = 0
    n_out_of_budget: int = 0
    timed_out: bool = False
    elapsed_s: float = 0.0


def literal_bank() -> dict[Type, list[Program]]:
    bank: dict[Type, list[Program]] = {t: [] for t in Type}
    for colour in LITERAL_POOLS[Type.COLOUR]:
        bank[Type.COLOUR].append(make_literal(colour, Type.COLOUR))
    for n in LITERAL_POOLS[Type.INTEGER]:
        bank[Type.INTEGER].append(make_literal(n, Type.INTEGER))
    for direction in DIRECTIONS:
        bank[Type.DIRECTION].append(make_literal(direction, Type.DIRECTION))
    for coord in COORDINATE_LITERALS:
        bank[Type.COORDINATE].append(make_literal(coord, Type.COORDINATE))
    bank[Type.GRID].append(make_input())
    return bank


def _arg_combinations(bank: dict[Type, list[Program]], params: tuple[Type, ...]):
    pools = [sorted(bank[t], key=lambda p: p.canonical()) for t in params]
    if any(not pool for pool in pools):
        return
    yield from itertools.product(*pools)


def _candidates_for_primitive(name: str, bank: dict[Type, list[Program]]):
    primitive = PRIMITIVES[name]
    for args in _arg_combinations(bank, primitive.params):
        candidate = make_call(name, args)
        if within_budget(candidate.cost(), candidate.depth()):
            yield candidate


def generate_level_candidates(bank: dict[Type, list[Program]]):
    """Every well-typed, in-budget candidate reachable by applying one
    primitive to the current bank — deterministic order (sorted primitive
    name, canonical-sorted arguments), shared by S0 and S1
    (`search/best_first.py` reorders this same universe by priority; it
    does not generate a different one)."""
    for name in sorted(PRIMITIVES):
        yield from _candidates_for_primitive(name, bank)


def is_exact_match(program: Program, cache: SearchCache, train_outputs: tuple[Grid, ...]) -> bool:
    if program.type_ != Type.GRID:
        return False
    results = cache.evaluate_on_all(program)
    if len(results) != len(train_outputs):
        return False
    return all(status == "ok" and value == target for (status, value), target in zip(results, train_outputs))


def search_enumerative(
    train_inputs: tuple[Grid, ...],
    train_outputs: tuple[Grid, ...],
    *,
    max_states: int,
    timeout_s: float,
) -> SearchResult:
    result = SearchResult()
    cache = SearchCache(train_inputs)
    bank = literal_bank()
    seen_signatures: set[tuple] = set()
    start = time.monotonic()

    for _depth in range(1, MAX_DEPTH + 1):
        new_bank: dict[Type, list[Program]] = {t: [] for t in Type}
        for candidate in generate_level_candidates(bank):
            if time.monotonic() - start > timeout_s:
                result.timed_out = True
                break
            if result.states_explored >= max_states:
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

            new_bank[candidate.type_].append(candidate)
            if is_exact_match(candidate, cache, train_outputs):
                result.exact_programs.append(candidate)
        else:
            for t in Type:
                bank[t].extend(new_bank[t])
            result.elapsed_s = time.monotonic() - start
            continue
        break

    result.elapsed_s = time.monotonic() - start
    return result
