"""Loading ARC corpora from either on-disk layout.

The Kaggle competition stores a split as a challenges file plus a separate
solutions file; the ARC-AGI-2 GitHub repository stores it as one JSON per task
with outputs inline. Callers should not have to know which they are reading, so
both are loaded into the same `Corpus` and every later stage of the audit works
on that type alone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

Grid = list[list[int]]


@dataclass(frozen=True)
class Pair:
    """One demonstration or test pair. `output` is None only for a hidden test."""

    input: Grid
    output: Grid | None


@dataclass(frozen=True)
class Task:
    task_id: str
    train: list[Pair]
    test: list[Pair]


@dataclass(frozen=True)
class Corpus:
    """A named split. `source` records where it came from, for provenance."""

    name: str
    source: str
    tasks: dict[str, Task]

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self):
        return iter(self.tasks.values())


def load_kaggle(
    challenges_path: Path, solutions_path: Path | None, name: str
) -> Corpus:
    """Load a Kaggle split. Test outputs stay None when no solutions file exists."""
    challenges = json.loads(challenges_path.read_text())
    solutions = json.loads(solutions_path.read_text()) if solutions_path else {}
    tasks = {}
    for task_id, task in challenges.items():
        outputs = solutions.get(task_id, [])
        tasks[task_id] = Task(
            task_id=task_id,
            train=[Pair(p["input"], p["output"]) for p in task["train"]],
            test=[
                Pair(p["input"], outputs[i] if i < len(outputs) else None)
                for i, p in enumerate(task["test"])
            ],
        )
    return Corpus(name=name, source=str(challenges_path), tasks=tasks)


def load_github(directory: Path, name: str) -> Corpus:
    """Load an ARC-AGI-2 repository split, one JSON per task, outputs inline."""
    tasks = {}
    for path in sorted(directory.glob("*.json")):
        task = json.loads(path.read_text())
        tasks[path.stem] = Task(
            task_id=path.stem,
            train=[Pair(p["input"], p["output"]) for p in task["train"]],
            test=[Pair(p["input"], p.get("output")) for p in task["test"]],
        )
    return Corpus(name=name, source=str(directory), tasks=tasks)
