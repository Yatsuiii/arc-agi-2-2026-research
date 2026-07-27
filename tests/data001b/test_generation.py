from __future__ import annotations

from pathlib import Path

from src.data001.program import Operation, Program
from src.data001b.descriptors import coverage_report, describe_task
from src.data001b.families import generate_family_task
from src.data001b.selection import generate_pool, parse_task_row, select_dataset


def test_family_generator_produces_nonempty_task():
    bundle = generate_family_task("F6", 1, "horizontal_tiling")
    assert bundle.task.train
    assert bundle.task.test
    assert bundle.effective_depth >= 1
    desc = describe_task(bundle.task)
    assert "grid_scale" in desc


def test_pool_and_selection_smoke(tmp_path: Path):
    pool_dir = tmp_path / "pool"
    result = generate_pool(pool_dir, attempt_budget=120, target_valid=90)
    assert result["summary"]["accepted_pool"] >= 60
    tasks = [parse_task_row(row) for row in result["tasks"]]
    programs = {
        row["program_id"]: Program(
            program_id=row["program_id"],
            family=row["family"],
            tier=row["tier"],
            operations=[Operation(**op) for op in row["operations"]],
            parameter_bindings=row["parameter_bindings"],
            labels=row.get("labels", []),
            version=row.get("version", "data001b.v1"),
        )
        for row in result["programs"]
    }
    selected = select_dataset(tasks, programs, tmp_path / "selected", target_size=40, token_budget=200000)
    assert selected["manifest"]["selected_total"] > 0
    report = coverage_report([describe_task(tasks[0])], [describe_task(task) for task in selected["train"] + selected["validation"]])
    assert report["weighted_descriptor_coverage"] >= 0.0
