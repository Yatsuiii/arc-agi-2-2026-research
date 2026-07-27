"""Per-task memoized execution and semantic hashing.

One `SearchCache` instance per task (`SEARCH_PROTOCOL.md`'s "no shared
mutable state across workers" — each worker constructs its own cache, never
shared across processes or tasks).
"""

from __future__ import annotations

from src.gen002.dsl.program import Program, evaluate
from src.gen002.dsl.types import Grid, ProgramError


class SearchCache:
    def __init__(self, train_inputs: tuple[Grid, ...]):
        self.train_inputs = train_inputs
        self._eval_cache: dict[tuple[str, int], object] = {}
        self.n_evaluations = 0

    def evaluate_on_all(self, program: Program) -> tuple[object, ...]:
        """Evaluate `program` on every training input, memoized per
        (canonical serialization, input index) — a subprogram that recurs
        across many candidate expansions (common in bottom-up synthesis,
        since later levels reuse earlier levels' terms) is evaluated once
        per training input, not once per candidate that contains it."""
        canonical = program.canonical()
        results = []
        for i, grid in enumerate(self.train_inputs):
            key = (canonical, i)
            if key not in self._eval_cache:
                self.n_evaluations += 1
                try:
                    self._eval_cache[key] = ("ok", evaluate(program, grid))
                except ProgramError as exc:
                    self._eval_cache[key] = ("error", str(exc))
            results.append(self._eval_cache[key])
        return tuple(results)

    def semantic_signature(self, program: Program) -> tuple:
        """Observational-equivalence key: two programs with the same
        signature behave identically on every training input this task
        has, and are therefore interchangeable for this task's search —
        only one is kept (`enumerative.py`'s dedup)."""
        return self.evaluate_on_all(program)

    def is_dead(self, program: Program) -> bool:
        """True if `program` raises `ProgramError` on any training input —
        dropped immediately, never expanded further (`SEARCH_PROTOCOL.md`
        pruning item 7)."""
        return any(status == "error" for status, _ in self.evaluate_on_all(program))
