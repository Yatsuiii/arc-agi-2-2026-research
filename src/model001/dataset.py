from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

from src.data001.target_formats import direct_grid_record, prompt_text, structured_trace_record
from src.data001.task_schema import ExamplePair, SyntheticTask


@dataclass(frozen=True)
class DatasetExample:
    task_id: str
    split: str
    input_text: str
    target_text: str
    family: str
    curriculum_tier: int
    target_kind: str


def load_synthetic_tasks(path: Path) -> list[SyntheticTask]:
    tasks = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tasks.append(
                SyntheticTask(
                    task_id=row["task_id"],
                    train=[ExamplePair(**pair) for pair in row["train"]],
                    test=[ExamplePair(**pair) for pair in row["test"]],
                    family=row["family"],
                    family_bucket=row["family_bucket"],
                    curriculum_tier=row["curriculum_tier"],
                    program_id=row["program_id"],
                    provenance=row["provenance"],
                    metadata=row["metadata"],
                )
            )
    return tasks


def build_examples(tasks: list[SyntheticTask], programs_by_id: dict[str, object], split: str, include_trace: bool = False) -> list[DatasetExample]:
    examples = []
    for task in tasks:
        prompt = prompt_text(task)
        direct = direct_grid_record(task)
        examples.append(
            DatasetExample(
                task_id=task.task_id,
                split=split,
                input_text=prompt,
                target_text=json.dumps(direct["target_grid"], separators=(",", ":")),
                family=task.family,
                curriculum_tier=task.curriculum_tier,
                target_kind="direct_grid",
            )
        )
        if include_trace:
            trace = structured_trace_record(task, programs_by_id[task.program_id])
            examples.append(
                DatasetExample(
                    task_id=task.task_id,
                    split=split,
                    input_text=prompt,
                    target_text=json.dumps(trace, separators=(",", ":")),
                    family=task.family,
                    curriculum_tier=task.curriculum_tier,
                    target_kind="structured_trace",
                )
            )
    return examples


def length_stats(examples: list[DatasetExample], tokenizer) -> dict:
    lengths = [len(tokenizer.encode(example.input_text + "\n" + example.target_text)) for example in examples]
    if not lengths:
        return {"n_examples": 0, "max": 0, "mean": 0.0, "p95": 0}
    ordered = sorted(lengths)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return {
        "n_examples": len(lengths),
        "min": ordered[0],
        "mean": round(sum(lengths) / len(lengths), 2),
        "p95": p95,
        "max": ordered[-1],
    }

