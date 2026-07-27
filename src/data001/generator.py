from __future__ import annotations

import csv
import gzip
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from src.harness.features.structural import connected_components, is_valid_grid

from .executor import blank, execute_program, shape
from .leakage import compare_against_references, load_reference_index
from .program import Operation, Program
from .provenance import GENERATOR_VERSION, sha256_text, stable_seed, task_hash
from .task_schema import ExamplePair, SyntheticTask

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class GeneratedBundle:
    task: SyntheticTask
    program: Program


class RejectTask(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _rect(grid, top: int, left: int, height: int, width: int, colour: int) -> None:
    for r in range(top, top + height):
        for c in range(left, left + width):
            grid[r][c] = colour


def _border_box(grid, top: int, left: int, height: int, width: int, colour: int) -> None:
    for c in range(left, left + width):
        grid[top][c] = colour
        grid[top + height - 1][c] = colour
    for r in range(top, top + height):
        grid[r][left] = colour
        grid[r][left + width - 1] = colour


def _line(grid, r0: int, c0: int, r1: int, c1: int, colour: int) -> None:
    if r0 == r1:
        for c in range(min(c0, c1), max(c0, c1) + 1):
            grid[r0][c] = colour
        return
    if c0 == c1:
        for r in range(min(r0, r1), max(r0, r1) + 1):
            grid[r][c0] = colour
        return
    dr = 1 if r1 > r0 else -1
    dc = 1 if c1 > c0 else -1
    r, c = r0, c0
    while True:
        grid[r][c] = colour
        if (r, c) == (r1, c1):
            break
        if r != r1:
            r += dr
        if c != c1:
            c += dc


def _count_objects(grid) -> int:
    return len(connected_components(grid, background=0))


def _size_relation(inputs: list[list[list[int]]], outputs: list[list[list[int]]]) -> str:
    relations = set()
    for input_grid, output_grid in zip(inputs, outputs):
        ishape = shape(input_grid)
        oshape = shape(output_grid)
        if ishape == oshape:
            relations.add("same")
        elif oshape[0] <= ishape[0] and oshape[1] <= ishape[1]:
            relations.add("smaller")
        elif oshape[0] >= ishape[0] and oshape[1] >= ishape[1]:
            relations.add("larger")
        else:
            relations.add("mixed")
    return relations.pop() if len(relations) == 1 else "inconsistent"


def _pairs(task_seed: int, min_pairs: int = 2, max_pairs: int = 5) -> int:
    return random.Random(task_seed).randint(min_pairs, max_pairs)


def _choose_colours(rng: random.Random, n: int) -> list[int]:
    palette = list(range(1, 10))
    rng.shuffle(palette)
    return palette[:n]


def _build_recolor(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    source_colour, target_colour = _choose_colours(rng, 2)
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(6, 12)
        w = rng.randint(6, 12)
        grid = blank(h, w, 0)
        _rect(grid, rng.randint(1, h - 4), rng.randint(1, w - 4), rng.randint(2, 3), rng.randint(2, 3), source_colour)
        if rng.random() < 0.5:
            _rect(grid, rng.randint(0, h - 2), rng.randint(0, w - 2), 1, 1, _choose_colours(rng, 1)[0])
        program = Program(
            program_id=f"prog-{seed}",
            family="recolor_primary",
            tier=1,
            operations=[Operation("recolor", {"source_colour": source_colour, "target_colour": target_colour})],
            parameter_bindings={"source_colour": source_colour, "target_colour": target_colour},
            labels=["grid_op", "colour_role"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "recolor_primary", family_bucket, 1, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_translate(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    object_colour, marker_colour = _choose_colours(rng, 2)
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(8, 14)
        w = rng.randint(8, 14)
        grid = blank(h, w, 0)
        oh, ow = rng.randint(2, 3), rng.randint(2, 3)
        top, left = rng.randint(1, h - oh - 2), rng.randint(1, w - ow - 2)
        _rect(grid, top, left, oh, ow, object_colour)
        marker_r, marker_c = rng.randint(0, h - oh), rng.randint(0, w - ow)
        grid[marker_r][marker_c] = marker_colour
        program = Program(
            program_id=f"prog-{seed}",
            family="translate_to_marker",
            tier=2,
            operations=[Operation("translate_to_marker", {"object_colour": object_colour, "marker_colour": marker_colour, "keep_marker": False})],
            parameter_bindings={"object_colour": object_colour, "marker_colour": marker_colour},
            labels=["object_op", "parameter_inference"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "translate_to_marker", family_bucket, 2, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_mirror(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    colour = _choose_colours(rng, 1)[0]
    axis = "vertical" if "vertical" in family_bucket else "horizontal"
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(7, 12)
        w = rng.randint(7, 12)
        grid = blank(h, w, 0)
        if axis == "vertical":
            _rect(grid, rng.randint(1, h - 3), rng.randint(0, max(0, w // 2 - 2)), rng.randint(2, 3), rng.randint(1, 2), colour)
        else:
            _rect(grid, rng.randint(0, max(0, h // 2 - 2)), rng.randint(1, w - 3), rng.randint(1, 2), rng.randint(2, 3), colour)
        program = Program(
            program_id=f"prog-{seed}",
            family="symmetry_completion",
            tier=1,
            operations=[Operation("mirror", {"colour": colour, "axis": axis})],
            parameter_bindings={"colour": colour, "axis": axis},
            labels=["pattern", "symmetry"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "symmetry_completion", family_bucket, 1, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_crop(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    colour = _choose_colours(rng, 1)[0]
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(8, 14)
        w = rng.randint(8, 14)
        grid = blank(h, w, 0)
        _rect(grid, rng.randint(1, h - 4), rng.randint(1, w - 4), rng.randint(2, 4), rng.randint(2, 4), colour)
        program = Program(
            program_id=f"prog-{seed}",
            family="crop_to_content",
            tier=1,
            operations=[Operation("crop_to_content", {})],
            parameter_bindings={},
            labels=["grid_op", "output_layout"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "crop_to_content", family_bucket, 1, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_duplicate(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    object_colour, marker_colour = _choose_colours(rng, 2)
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(10, 16)
        w = rng.randint(10, 16)
        grid = blank(h, w, 0)
        _rect(grid, 1, 1, rng.randint(2, 3), rng.randint(2, 3), object_colour)
        n_markers = rng.randint(2, 4)
        for _ in range(n_markers):
            grid[rng.randint(0, h - 3)][rng.randint(0, w - 3)] = marker_colour
        program = Program(
            program_id=f"prog-{seed}",
            family="duplicate_to_markers",
            tier=2,
            operations=[Operation("duplicate_to_markers", {"object_colour": object_colour, "marker_colour": marker_colour, "keep_markers": False})],
            parameter_bindings={"object_colour": object_colour, "marker_colour": marker_colour},
            labels=["object_op", "count_inference"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "duplicate_to_markers", family_bucket, 2, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_connect(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    marker_colour, line_colour = _choose_colours(rng, 2)
    axis = "horizontal" if "horizontal" in family_bucket else "vertical"
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(8, 12)
        w = rng.randint(8, 12)
        grid = blank(h, w, 0)
        if axis == "horizontal":
            row = rng.randint(1, h - 2)
            c0, c1 = sorted(rng.sample(range(1, w - 1), 2))
            grid[row][c0] = marker_colour
            grid[row][c1] = marker_colour
        else:
            col = rng.randint(1, w - 2)
            r0, r1 = sorted(rng.sample(range(1, h - 1), 2))
            grid[r0][col] = marker_colour
            grid[r1][col] = marker_colour
        program = Program(
            program_id=f"prog-{seed}",
            family="connect_markers",
            tier=3,
            operations=[Operation("connect_markers", {"marker_colour": marker_colour, "line_colour": line_colour, "retain_markers": True})],
            parameter_bindings={"marker_colour": marker_colour, "line_colour": line_colour},
            labels=["relational", "line"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "connect_markers", family_bucket, 3, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_container(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    border_colour, fill_colour = _choose_colours(rng, 2)
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(8, 14)
        w = rng.randint(8, 14)
        grid = blank(h, w, 0)
        box_h, box_w = rng.randint(4, 6), rng.randint(4, 6)
        top = rng.randint(1, h - box_h - 1)
        left = rng.randint(1, w - box_w - 1)
        _border_box(grid, top, left, box_h, box_w, border_colour)
        program = Program(
            program_id=f"prog-{seed}",
            family="fill_container",
            tier=3,
            operations=[Operation("fill_container", {"border_colour": border_colour, "fill_colour": fill_colour})],
            parameter_bindings={"border_colour": border_colour, "fill_colour": fill_colour},
            labels=["container", "region_fill"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "fill_container", family_bucket, 3, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_delete_smallest(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    colours = _choose_colours(rng, 3)
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(8, 12)
        w = rng.randint(8, 12)
        grid = blank(h, w, 0)
        _rect(grid, 1, 1, 3, 3, colours[0])
        _rect(grid, h - 3, w - 3, 2, 2, colours[1])
        _rect(grid, 1, w - 2, 1, 1, colours[2])
        program = Program(
            program_id=f"prog-{seed}",
            family="delete_smallest_object",
            tier=2,
            operations=[Operation("delete_smallest_object", {})],
            parameter_bindings={},
            labels=["object_op", "selection"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "delete_smallest_object", family_bucket, 2, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_tile(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    motif_colour, marker_colour = _choose_colours(rng, 2)
    axis = "horizontal" if "horizontal" in family_bucket else "vertical"
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(5, 6)
        w = rng.randint(5, 6)
        grid = blank(h, w, 0)
        _rect(grid, 1, 1, 2, 2, motif_colour)
        if axis == "horizontal":
            row = h - 2
            slots = [c for c in range(1, w - 1, 2)]
            count = min(len(slots), rng.randint(3, 4))
            for c in slots[:count]:
                grid[row][c] = marker_colour
        else:
            col = w - 2
            slots = [r for r in range(1, h - 1, 2)]
            count = min(len(slots), rng.randint(3, 4))
            for r in slots[:count]:
                grid[r][col] = marker_colour
        program = Program(
            program_id=f"prog-{seed}",
            family="tile_by_markers",
            tier=2,
            operations=[Operation("tile_by_markers", {"motif_colour": motif_colour, "marker_colour": marker_colour, "axis": axis, "spacing": 2})],
            parameter_bindings={"motif_colour": motif_colour, "marker_colour": marker_colour, "axis": axis, "spacing": 2},
            labels=["pattern", "tiling", "count_inference"],
        )
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "tile_by_markers", family_bucket, 2, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_compose_translate_recolor(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    object_colour, marker_colour, target_colour = _choose_colours(rng, 3)
    train = []
    program = Program(
        program_id=f"prog-{seed}",
        family="translate_then_recolor",
        tier=4,
        operations=[
            Operation("translate_to_marker", {"object_colour": object_colour, "marker_colour": marker_colour, "keep_marker": False}),
            Operation("recolor", {"source_colour": object_colour, "target_colour": target_colour}),
        ],
        parameter_bindings={"object_colour": object_colour, "marker_colour": marker_colour, "target_colour": target_colour},
        labels=["composition", "object_op", "colour_role"],
    )
    for _ in range(_pairs(seed)):
        h = rng.randint(8, 13)
        w = rng.randint(8, 13)
        grid = blank(h, w, 0)
        _rect(grid, rng.randint(1, h - 4), rng.randint(1, w - 4), 2, 2, object_colour)
        grid[rng.randint(0, h - 3)][rng.randint(0, w - 3)] = marker_colour
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "translate_then_recolor", family_bucket, 4, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


def _build_compose_duplicate_crop(seed: int, family_bucket: str) -> GeneratedBundle:
    rng = random.Random(seed)
    object_colour, marker_colour = _choose_colours(rng, 2)
    program = Program(
        program_id=f"prog-{seed}",
        family="duplicate_then_crop",
        tier=4,
        operations=[
            Operation("duplicate_to_markers", {"object_colour": object_colour, "marker_colour": marker_colour, "keep_markers": False}),
            Operation("crop_to_content", {}),
        ],
        parameter_bindings={"object_colour": object_colour, "marker_colour": marker_colour},
        labels=["composition", "object_op", "output_layout"],
    )
    train = []
    for _ in range(_pairs(seed)):
        h = rng.randint(10, 16)
        w = rng.randint(10, 16)
        grid = blank(h, w, 0)
        _rect(grid, 1, 1, 2, 2, object_colour)
        for _ in range(rng.randint(2, 3)):
            grid[rng.randint(0, h - 3)][rng.randint(0, w - 3)] = marker_colour
        output = execute_program(program, grid)
        train.append(ExamplePair(grid, output))
    test_input = train[-1].input
    test_output = execute_program(program, test_input)
    task = _finalize_task(seed, "duplicate_then_crop", family_bucket, 4, train, [ExamplePair(test_input, test_output)], program)
    return GeneratedBundle(task, program)


FAMILY_BUILDERS = {
    "recolor_primary:core": _build_recolor,
    "translate_to_marker:core": _build_translate,
    "symmetry_completion:vertical": _build_mirror,
    "symmetry_completion:horizontal": _build_mirror,
    "crop_to_content:core": _build_crop,
    "duplicate_to_markers:core": _build_duplicate,
    "connect_markers:horizontal": _build_connect,
    "connect_markers:vertical": _build_connect,
    "fill_container:core": _build_container,
    "delete_smallest_object:core": _build_delete_smallest,
    "tile_by_markers:horizontal": _build_tile,
    "tile_by_markers:vertical": _build_tile,
    "translate_then_recolor:core": _build_compose_translate_recolor,
    "duplicate_then_crop:core": _build_compose_duplicate_crop,
}


VALIDATION_BUCKETS = {
    "symmetry_completion:horizontal",
    "connect_markers:vertical",
    "tile_by_markers:vertical",
    "duplicate_then_crop:core",
}


def _finalize_task(
    seed: int,
    family: str,
    family_bucket: str,
    tier: int,
    train: list[ExamplePair],
    test: list[ExamplePair],
    program: Program,
) -> SyntheticTask:
    inputs = [pair.input for pair in train + test]
    outputs = [pair.output for pair in train + test]
    for pair in train + test:
        if is_valid_grid(pair.input) != 1.0 or is_valid_grid(pair.output) != 1.0:
            raise RejectTask("invalid_grid")
    if all(pair.input == pair.output for pair in train + test):
        raise RejectTask("identity_task")
    if len({json.dumps(pair.output) for pair in train}) == 1 and len({json.dumps(pair.input) for pair in train}) > 1:
        raise RejectTask("trivial_constant_output")
    objects_input_mean = sum(_count_objects(grid) for grid in inputs) / len(inputs)
    metadata = {
        "n_train": len(train),
        "n_test": len(test),
        "size_relation": _size_relation(inputs, outputs),
        "objects_input_mean": round(objects_input_mean, 3),
        "composition_depth": len(program.operations),
        "input_dims": [shape(grid) for grid in inputs],
        "output_dims": [shape(grid) for grid in outputs],
    }
    provenance = {
        "seed": seed,
        "generator_version": GENERATOR_VERSION,
        "program_version": program.version,
        "family_bucket": family_bucket,
    }
    task_stub = SyntheticTask(
        task_id=f"data001a-{sha256_text(f'{family_bucket}-{seed}')[:12]}",
        train=train,
        test=test,
        family=family,
        family_bucket=family_bucket,
        curriculum_tier=tier,
        program_id=program.program_id,
        provenance=provenance,
        metadata=metadata,
    )
    provenance["task_hash"] = task_hash(task_stub)
    return task_stub


def generate_task(family_bucket: str, serial: int) -> GeneratedBundle:
    seed = stable_seed("data001a", family_bucket, serial)
    return FAMILY_BUILDERS[family_bucket](seed, family_bucket)


def write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_pilot_corpus(
    out_dir: Path,
    target_accept: int = 6000,
    max_attempts: int = 9000,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    reference_index = load_reference_index()
    accepted_train: list[GeneratedBundle] = []
    accepted_validation: list[GeneratedBundle] = []
    quarantined: list[dict] = []
    programs: list[dict] = []
    rejection_counts = Counter()
    seen_task_hashes = set()
    attempts = 0
    serial = 0
    while attempts < max_attempts and (len(accepted_train) + len(accepted_validation)) < target_accept:
        family_bucket = list(FAMILY_BUILDERS)[serial % len(FAMILY_BUILDERS)]
        attempts += 1
        serial += 1
        try:
            bundle = generate_task(family_bucket, serial)
            thash = bundle.task.provenance["task_hash"]
            if thash in seen_task_hashes:
                raise RejectTask("duplicate_task_hash")
            overlap = compare_against_references(bundle.task, reference_index)
            if overlap["suspicious"]:
                quarantined.append(
                    {
                        "task_id": bundle.task.task_id,
                        "family": bundle.task.family,
                        "family_bucket": bundle.task.family_bucket,
                        "reason": "reference_overlap",
                        "overlap": overlap,
                    }
                )
                rejection_counts["quarantined_reference_overlap"] += 1
                continue
            seen_task_hashes.add(thash)
            if family_bucket in VALIDATION_BUCKETS:
                accepted_validation.append(bundle)
            else:
                accepted_train.append(bundle)
            programs.append(bundle.program.to_dict())
        except RejectTask as exc:
            rejection_counts[exc.reason] += 1

    train_rows = [bundle.task.to_dict() for bundle in accepted_train]
    validation_rows = [bundle.task.to_dict() for bundle in accepted_validation]
    write_jsonl_gz(out_dir / "tasks_train.jsonl.gz", train_rows)
    write_jsonl_gz(out_dir / "tasks_validation.jsonl.gz", validation_rows)
    write_jsonl_gz(out_dir / "programs.jsonl.gz", programs)
    with (out_dir / "quarantined_tasks.jsonl").open("w", encoding="utf-8") as handle:
        for row in quarantined:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    family_counts = Counter(bundle.task.family for bundle in accepted_train + accepted_validation)
    bucket_counts = Counter(bundle.task.family_bucket for bundle in accepted_train + accepted_validation)
    tier_counts = Counter(str(bundle.task.curriculum_tier) for bundle in accepted_train + accepted_validation)
    composition_depth_counts = Counter(str(bundle.task.metadata["composition_depth"]) for bundle in accepted_train + accepted_validation)
    size_relation_counts = Counter(bundle.task.metadata["size_relation"] for bundle in accepted_train + accepted_validation)
    accepted = accepted_train + accepted_validation
    generation_summary = {
        "generator_version": GENERATOR_VERSION,
        "attempts": attempts,
        "accepted_tasks": len(accepted),
        "accepted_train": len(accepted_train),
        "accepted_validation": len(accepted_validation),
        "rejected_tasks": attempts - len(accepted),
        "quarantined_tasks": len(quarantined),
        "rejection_reasons": dict(rejection_counts),
        "family_distribution": dict(family_counts),
        "family_bucket_distribution": dict(bucket_counts),
        "curriculum_distribution": dict(tier_counts),
        "composition_depth_distribution": dict(composition_depth_counts),
        "size_relation_distribution": dict(size_relation_counts),
        "throughput_tasks_per_attempt": round(len(accepted) / attempts, 4) if attempts else 0.0,
    }
    dataset_manifest = {
        "dataset_name": "DATA001A synthetic pilot",
        "generator_version": GENERATOR_VERSION,
        "train_records": len(accepted_train),
        "validation_records": len(accepted_validation),
        "program_records": len(programs),
        "family_disjoint_validation_buckets": sorted(VALIDATION_BUCKETS),
        "target_accept": target_accept,
        "max_attempts": max_attempts,
    }
    family_manifest = {
        "train_buckets": sorted(set(bundle.task.family_bucket for bundle in accepted_train)),
        "validation_buckets": sorted(set(bundle.task.family_bucket for bundle in accepted_validation)),
        "family_counts": dict(family_counts),
        "bucket_counts": dict(bucket_counts),
    }
    (out_dir / "generation_summary.json").write_text(json.dumps(generation_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "dataset_manifest.json").write_text(json.dumps(dataset_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "family_manifest.json").write_text(json.dumps(family_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "train": accepted_train,
        "validation": accepted_validation,
        "programs": programs,
        "summary": generation_summary,
        "manifest": dataset_manifest,
        "family_manifest": family_manifest,
        "quarantined": quarantined,
    }
