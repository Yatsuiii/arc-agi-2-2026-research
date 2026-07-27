from __future__ import annotations

from .executor import execute_program
from .serialization import serialize_grid
from .task_schema import SyntheticTask


def direct_grid_record(task: SyntheticTask) -> dict:
    return {
        "task_id": task.task_id,
        "family": task.family,
        "curriculum_tier": task.curriculum_tier,
        "train": [{"input": pair.input, "output": pair.output} for pair in task.train],
        "test": [{"input": pair.input, "output": pair.output} for pair in task.test],
        "target_grid": task.test[0].output,
    }


def structured_trace_record(task: SyntheticTask, program, include_intermediates: bool = True) -> dict:
    output, trace = execute_program(program, task.test[0].input, with_trace=True)
    payload = {
        "task_id": task.task_id,
        "family": task.family,
        "curriculum_tier": task.curriculum_tier,
        "program_id": program.program_id,
        "operation_sequence": trace.operations,
        "parameters": dict(program.parameter_bindings),
        "target_grid": output,
    }
    if include_intermediates:
        payload["intermediate_grids"] = trace.intermediate_grids
    return payload


def prompt_text(task: SyntheticTask) -> str:
    lines = [f"TASK {task.task_id}", f"FAMILY {task.family}", "TRAIN"]
    for idx, pair in enumerate(task.train):
        lines.append(f"PAIR {idx} IN {serialize_grid(pair.input)} OUT {serialize_grid(pair.output)}")
    lines.append("TEST")
    lines.append(f"INPUT {serialize_grid(task.test[0].input)}")
    return "\n".join(lines)

