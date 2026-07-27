from __future__ import annotations

import json


def parse_grid_prediction(text: str):
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, list):
        return None
    try:
        return [[int(cell) for cell in row] for row in value]
    except Exception:
        return None


def evaluate_topk(examples, predictions_by_task: dict[str, list[str]]) -> dict:
    total = len(examples)
    exact_top1 = 0
    oracle = 0
    malformed = 0
    for example in examples:
        predictions = predictions_by_task.get(example.task_id, [])
        parsed = [parse_grid_prediction(text) for text in predictions]
        malformed += sum(1 for item in parsed if item is None)
        gold = parse_grid_prediction(example.target_text)
        if parsed and parsed[0] == gold:
            exact_top1 += 1
        if any(item == gold for item in parsed):
            oracle += 1
    return {
        "n_examples": total,
        "top1_accuracy": exact_top1 / total if total else 0.0,
        "oracle_accuracy": oracle / total if total else 0.0,
        "malformed_outputs": malformed,
    }

