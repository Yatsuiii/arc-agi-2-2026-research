from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from src.gen002.grid import Grid, background_candidates, bounding_region, dims, from_nested_list, to_nested_list


@dataclass(frozen=True)
class TrainPair:
    input_grid: Grid
    output_grid: Grid


@dataclass(frozen=True)
class ArcTask:
    task_id: str
    train_pairs: tuple[TrainPair, ...]
    test_inputs: tuple[Grid, ...]


@dataclass(frozen=True)
class SynthProgram:
    stage: str
    family: str
    name: str
    params: tuple[tuple[str, object], ...]
    cost: int
    apply_fn: Callable[[Grid], Grid]

    def canonical(self) -> str:
        parts = ", ".join(f"{k}={json.dumps(v, sort_keys=True)}" for k, v in self.params)
        return f"{self.stage}:{self.family}:{self.name}({parts})"

    def apply(self, grid: Grid) -> Grid:
        return self.apply_fn(grid)


@dataclass
class StageSummary:
    stage: str
    states_explored: int = 0
    exact_programs: list[SynthProgram] = field(default_factory=list)
    best_n_solved: int = 0
    best_pixel_agreement: float = 0.0
    template_usage: Counter = field(default_factory=Counter)
    representation_warnings: int = 0


@dataclass
class TaskRun:
    task_id: str
    exact_programs: list[SynthProgram]
    candidates_by_index: dict[int, list[dict]]
    stage_summaries: dict[str, StageSummary]
    elapsed_s: float


def grid_sha1(grid: Grid) -> str:
    payload = json.dumps(to_nested_list(grid), sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def pixel_agreement(predicted: Grid, target: Grid) -> float:
    ph, pw = dims(predicted)
    th, tw = dims(target)
    if ph != th or pw != tw:
        return 0.0
    total = ph * pw
    if total == 0:
        return 1.0
    same = 0
    for prow, trow in zip(predicted, target):
        same += sum(1 for a, b in zip(prow, trow) if a == b)
    return same / total


def n_solved(program: SynthProgram, train_pairs: tuple[TrainPair, ...]) -> tuple[int, float]:
    solved = 0
    best_pixel = 0.0
    for pair in train_pairs:
        try:
            predicted = program.apply(pair.input_grid)
        except Exception:  # noqa: BLE001
            continue
        if predicted == pair.output_grid:
            solved += 1
        best_pixel = max(best_pixel, pixel_agreement(predicted, pair.output_grid))
    return solved, best_pixel


def exact_on_train(program: SynthProgram, train_pairs: tuple[TrainPair, ...]) -> bool:
    return all(program.apply(pair.input_grid) == pair.output_grid for pair in train_pairs)


def infer_background(task: ArcTask) -> tuple[int, ...]:
    counts: Counter[int] = Counter()
    for pair in task.train_pairs:
        for bg in background_candidates(pair.input_grid)[:2]:
            counts[bg] += 1
    ordered = [colour for colour, _count in counts.most_common()]
    return tuple(ordered[:2] or [0])


def crop_non_background(grid: Grid, background: int) -> Grid:
    region = bounding_region(grid, background=background)
    if region is None:
        return grid
    r0, c0, r1, c1 = region
    return tuple(row[c0 : c1 + 1] for row in grid[r0 : r1 + 1])


def load_task(task_id: str, task_payload: dict) -> ArcTask:
    return ArcTask(
        task_id=task_id,
        train_pairs=tuple(
            TrainPair(from_nested_list(pair["input"]), from_nested_list(pair["output"]))
            for pair in task_payload["train"]
        ),
        test_inputs=tuple(from_nested_list(pair["input"]) for pair in task_payload["test"]),
    )
