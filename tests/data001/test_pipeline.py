from __future__ import annotations

import json
from pathlib import Path

from src.data001.executor import execute_program
from src.data001.generator import build_pilot_corpus, generate_task
from src.data001.program import Operation, Program
from src.data001.serialization import parse_grid, serialize_grid


def test_executor_recolor_and_roundtrip():
    program = Program(
        program_id="p",
        family="recolor_primary",
        tier=1,
        operations=[Operation("recolor", {"source_colour": 1, "target_colour": 2})],
        parameter_bindings={},
    )
    output = execute_program(program, [[0, 1], [1, 0]])
    assert output == [[0, 2], [2, 0]]
    assert parse_grid(serialize_grid(output)) == output


def test_generate_task_has_train_and_test():
    bundle = generate_task("translate_to_marker:core", 1)
    assert bundle.task.train
    assert bundle.task.test
    assert bundle.task.family == "translate_to_marker"
    assert len(bundle.program.operations) == 1


def test_build_pilot_corpus_writes_artifacts(tmp_path: Path):
    result = build_pilot_corpus(tmp_path, target_accept=24, max_attempts=48)
    assert result["summary"]["accepted_tasks"] >= 12
    assert (tmp_path / "tasks_train.jsonl.gz").exists()
    assert (tmp_path / "tasks_validation.jsonl.gz").exists()
    assert (tmp_path / "generation_summary.json").exists()
    summary = json.loads((tmp_path / "generation_summary.json").read_text())
    assert summary["accepted_tasks"] == result["summary"]["accepted_tasks"]

