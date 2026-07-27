"""Generator-neutral candidate union schema.

This module merges candidate *sets*. It does not score, rank, select, or read
ground truth. Exact grid equality is the only deduplication rule, and every
source contribution remains attached to the merged record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable

from src.run001.archive import grid_digest, to_grid


@dataclass(frozen=True)
class CandidateProvenance:
    generator_id: str
    source_record_id: str
    metadata: dict = field(default_factory=dict)


@dataclass
class UnionCandidate:
    task_id: str
    test_index: int
    grid: list[list[int]]
    grid_sha1: str
    provenance: list[CandidateProvenance] = field(default_factory=list)

    def to_record(self) -> dict:
        return {
            "task_id": self.task_id,
            "test_index": self.test_index,
            "grid": self.grid,
            "grid_sha1": self.grid_sha1,
            "provenance": [asdict(item) for item in self.provenance],
        }


def _validated_grid(value) -> list[list[int]]:
    grid = to_grid(value)
    if not grid or not grid[0]:
        raise ValueError("candidate grid must be non-empty")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("candidate grid must be rectangular")
    if any(cell < 0 or cell > 9 for row in grid for cell in row):
        raise ValueError("candidate grid cells must be colours 0..9")
    return grid


def normalize_candidate(
    record: dict,
    *,
    generator_id: str,
    grid_field: str = "grid",
    source_record_id: str | None = None,
) -> UnionCandidate:
    """Normalize one source record without assigning it a union rank."""
    grid = _validated_grid(record[grid_field])
    digest = grid_digest(grid)
    record_id = source_record_id or str(
        record.get("grid_sha1")
        or record.get("canonical_ast")
        or record.get("program_source")
        or digest
    )
    metadata = {
        key: value
        for key, value in record.items()
        if key
        not in {
            "task_id",
            "test_index",
            "grid",
            "candidate_grid",
            "grid_sha1",
        }
    }
    return UnionCandidate(
        task_id=str(record["task_id"]),
        test_index=int(record["test_index"]),
        grid=grid,
        grid_sha1=digest,
        provenance=[
            CandidateProvenance(
                generator_id=generator_id,
                source_record_id=record_id,
                metadata=metadata,
            )
        ],
    )


def normalize_compressarc(record: dict) -> UnionCandidate:
    return normalize_candidate(record, generator_id="compressarc")


def normalize_nvarc(record: dict) -> UnionCandidate:
    return normalize_candidate(record, generator_id="nvarc")


def normalize_gen002(record: dict) -> UnionCandidate:
    return normalize_candidate(
        record,
        generator_id="gen002_program_synthesis",
        grid_field="candidate_grid",
    )


def union_candidates(
    candidates: Iterable[UnionCandidate],
) -> list[UnionCandidate]:
    """Deduplicate by `(task_id, test_index, grid_sha1)`, preserving sources."""
    merged: dict[tuple[str, int, str], UnionCandidate] = {}
    for candidate in candidates:
        expected_digest = grid_digest(_validated_grid(candidate.grid))
        if expected_digest != candidate.grid_sha1:
            raise ValueError("grid_sha1 does not match candidate grid")
        key = (candidate.task_id, candidate.test_index, candidate.grid_sha1)
        if key not in merged:
            merged[key] = UnionCandidate(
                task_id=candidate.task_id,
                test_index=candidate.test_index,
                grid=candidate.grid,
                grid_sha1=candidate.grid_sha1,
                provenance=list(candidate.provenance),
            )
        else:
            seen = {
                (item.generator_id, item.source_record_id)
                for item in merged[key].provenance
            }
            for item in candidate.provenance:
                provenance_key = (item.generator_id, item.source_record_id)
                if provenance_key not in seen:
                    merged[key].provenance.append(item)
                    seen.add(provenance_key)
    return list(merged.values())
