from __future__ import annotations

import json

from .program import Program
from .task_schema import SyntheticTask


def serialize_grid(grid: list[list[int]]) -> str:
    return json.dumps(grid, separators=(",", ":"))


def parse_grid(text: str) -> list[list[int]]:
    value = json.loads(text)
    return [[int(cell) for cell in row] for row in value]


def serialize_program(program: Program) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def serialize_task(task: SyntheticTask) -> str:
    return json.dumps(task.to_dict(), sort_keys=True, separators=(",", ":"))


def parse_task(text: str) -> dict:
    return json.loads(text)

