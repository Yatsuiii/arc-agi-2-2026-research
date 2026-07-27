from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from src.data_audit.corpus import load_kaggle
from src.data_audit.statistics import describe

from .provenance import (
    d4_normalized_grid_hash,
    grid_hash,
    normalized_grid_hash,
    pair_hash,
)
from .task_schema import SyntheticTask

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT.parent


@dataclass(frozen=True)
class ReferenceEntry:
    source: str
    task_id: str
    exact_task_signature: str
    structural_signature: str
    descriptor: dict


def _task_statistics_by_id() -> dict[str, dict]:
    path = REPO_ROOT / "artifacts" / "data_audit" / "task_statistics.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {row["task_id"]: row for row in reader}


def _build_reference_entry(source: str, task_id: str, task_dict: dict) -> ReferenceEntry:
    train = task_dict["train"]
    test = task_dict["test"]
    exact_parts = []
    for pair in train + test:
        exact_parts.append(
            pair_hash(
                {
                    "input": pair["input"],
                    "output": pair.get("output"),
                }
            )
        )
    stats = _task_statistics_by_id().get(task_id)
    descriptor = {
        "source": source,
        "task_id": task_id,
        "n_train": len(train),
        "n_test": len(test),
        "input_dims": tuple((len(pair["input"]), len(pair["input"][0])) for pair in train + test),
        "output_dims": tuple(
            (len(pair["output"]), len(pair["output"][0]))
            for pair in train
            if pair.get("output") is not None
        ),
        "size_relation": stats["size_relation"] if stats else "unknown",
        "n_input_colours": int(float(stats["n_input_colours"])) if stats else 0,
        "objects_input_mean": float(stats["objects_input_mean"]) if stats else 0.0,
        "output_cells_max": int(float(stats["output_cells_max"])) if stats else 0,
    }
    structural_signature = json.dumps(
        {
            "size_relation": descriptor["size_relation"],
            "input_dims": descriptor["input_dims"],
            "output_dims": descriptor["output_dims"],
            "n_input_colours": descriptor["n_input_colours"],
            "objects_input_mean_bin": round(descriptor["objects_input_mean"]),
        },
        sort_keys=True,
    )
    return ReferenceEntry(
        source=source,
        task_id=task_id,
        exact_task_signature="|".join(sorted(exact_parts)),
        structural_signature=structural_signature,
        descriptor=descriptor,
    )


def load_reference_index() -> dict[str, list[ReferenceEntry]]:
    kaggle_root = DATA_ROOT / "competition_2026" / "extracted"
    training = json.loads((kaggle_root / "arc-agi_training_challenges.json").read_text())
    evaluation = json.loads((kaggle_root / "arc-agi_evaluation_challenges.json").read_text())
    folds = json.loads((REPO_ROOT / "artifacts" / "ACQ001" / "folds.json").read_text())
    held_out = set(folds["test_task_ids"])

    index = defaultdict(list)
    for source_name, corpus in (
        ("arc_agi_2_train", training),
        ("arc_agi_2_eval", evaluation),
    ):
        for task_id, task in corpus.items():
            index["all"].append(_build_reference_entry(source_name, task_id, task))
            if source_name == "arc_agi_2_train":
                index["arc_train"].append(_build_reference_entry(source_name, task_id, task))
                if task_id in held_out:
                    index["acq001_held_out"].append(_build_reference_entry("acq001_held_out", task_id, task))
    return dict(index)


def synthetic_descriptor(task: SyntheticTask) -> dict:
    inputs = [pair.input for pair in task.train + task.test]
    outputs = [pair.output for pair in task.train + task.test]
    input_dims = tuple((len(grid), len(grid[0])) for grid in inputs)
    output_dims = tuple((len(grid), len(grid[0])) for grid in outputs)
    colour_counts = sorted({len(set(cell for row in grid for cell in row)) for grid in inputs})
    return {
        "family": task.family,
        "family_bucket": task.family_bucket,
        "curriculum_tier": task.curriculum_tier,
        "input_dims": input_dims,
        "output_dims": output_dims,
        "size_relation": task.metadata["size_relation"],
        "n_input_colours": max(colour_counts) if colour_counts else 0,
        "objects_input_mean_bin": round(task.metadata["objects_input_mean"]),
        "composition_depth": task.metadata["composition_depth"],
    }


def synthetic_exact_signature(task: SyntheticTask) -> str:
    parts = []
    for pair in task.train + task.test:
        parts.append(pair_hash({"input": pair.input, "output": pair.output}))
    return "|".join(sorted(parts))


def synthetic_structural_signature(task: SyntheticTask) -> str:
    descriptor = synthetic_descriptor(task)
    return json.dumps(
        {
            "size_relation": descriptor["size_relation"],
            "input_dims": descriptor["input_dims"],
            "output_dims": descriptor["output_dims"],
            "n_input_colours": descriptor["n_input_colours"],
            "objects_input_mean_bin": descriptor["objects_input_mean_bin"],
        },
        sort_keys=True,
    )


def compare_against_references(task: SyntheticTask, reference_index: dict[str, list[ReferenceEntry]]) -> dict:
    exact_signature = synthetic_exact_signature(task)
    structural_signature = synthetic_structural_signature(task)
    exact_hits = []
    structural_hits = []
    descriptor = synthetic_descriptor(task)
    for entry in reference_index["all"]:
        if entry.exact_task_signature == exact_signature:
            exact_hits.append({"source": entry.source, "task_id": entry.task_id, "kind": "exact_task"})
        if entry.structural_signature == structural_signature:
            structural_hits.append({"source": entry.source, "task_id": entry.task_id, "kind": "structural_signature"})
    suspicious = exact_hits or len(structural_hits) >= 2
    return {
        "exact_hits": exact_hits,
        "structural_hits": structural_hits[:5],
        "suspicious": bool(suspicious),
        "descriptor": descriptor,
    }


def descriptor_bins(rows: list[dict]) -> dict[str, set]:
    bins = defaultdict(set)
    for row in rows:
        bins["size_relation"].add(row["size_relation"])
        bins["input_dims"].add(tuple(row["input_dims"]))
        bins["output_dims"].add(tuple(row["output_dims"]))
        bins["n_input_colours"].add(row["n_input_colours"])
        bins["objects_input_mean_bin"].add(round(float(row["objects_input_mean"])) if "objects_input_mean" in row else row["objects_input_mean_bin"])
    return dict(bins)

