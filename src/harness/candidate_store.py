"""In-memory, solver-agnostic container for candidates and task demonstrations.

`CandidateStore` is what `adapters/*.py` populate and what `features/*.py`,
`verifier/*.py` and `runner.py` read from. It never touches a file or a
solver-specific schema itself — that translation is exactly what makes a
module an adapter rather than part of the store.
"""

from __future__ import annotations

from src.harness.schemas import Candidate, CandidateSet, SelectionRecord

Grid = list[list[int]]


class CandidateStore:
    """Every `CandidateSet` seen so far, keyed by (task_id, test_index)."""

    def __init__(self) -> None:
        self._sets: dict[tuple[str, int], CandidateSet] = {}

    def _get_or_create(self, task_id: str, test_index: int) -> CandidateSet:
        key = (task_id, test_index)
        if key not in self._sets:
            self._sets[key] = CandidateSet(task_id=task_id, test_index=test_index)
        return self._sets[key]

    def append_candidates(self, candidates: list[Candidate]) -> None:
        for candidate in candidates:
            self._get_or_create(candidate.task_id, candidate.test_index).candidates.append(
                candidate
            )

    def append_selection(self, records: list[SelectionRecord]) -> None:
        for record in records:
            self._get_or_create(record.task_id, record.test_index).selection.append(record)

    def get(self, task_id: str, test_index: int) -> CandidateSet | None:
        return self._sets.get((task_id, test_index))

    def all(self) -> list[CandidateSet]:
        return list(self._sets.values())

    def task_ids(self) -> list[str]:
        seen: dict[str, None] = {}
        for task_id, _ in self._sets:
            seen.setdefault(task_id, None)
        return list(seen)

    def __len__(self) -> int:
        return len(self._sets)


def demonstration_pairs(challenge: dict) -> list[tuple[Grid, Grid]]:
    """A task's `train` pairs as `(input, output)` tuples, in the competition's own order."""
    return [(pair["input"], pair["output"]) for pair in challenge.get("train", [])]


def test_inputs(challenge: dict) -> list[Grid]:
    """A task's test input grids, in test-index order."""
    return [pair["input"] for pair in challenge.get("test", [])]
