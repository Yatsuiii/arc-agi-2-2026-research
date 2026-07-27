from __future__ import annotations

import csv
import gzip
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Iterable

from src.data001.task_schema import ExamplePair, SyntheticTask
from src.data_audit.corpus import load_kaggle

Grid = list[list[int]]
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT.parent


def shape(grid: Grid) -> tuple[int, int]:
    return (len(grid), len(grid[0]) if grid else 0)


def colour_counts(grid: Grid) -> Counter:
    return Counter(cell for row in grid for cell in row)


def most_common_colour(grid: Grid) -> int:
    return colour_counts(grid).most_common(1)[0][0] if grid else 0


def connected_components(grid: Grid, connectivity: int = 4, background: int | None = None) -> list[dict]:
    if not grid or not grid[0]:
        return []
    background = most_common_colour(grid) if background is None else background
    neighbours = ((1, 0), (-1, 0), (0, 1), (0, -1))
    if connectivity == 8:
        neighbours += ((1, 1), (1, -1), (-1, 1), (-1, -1))
    seen = set()
    rows, cols = shape(grid)
    comps = []
    for r in range(rows):
        for c in range(cols):
            colour = grid[r][c]
            if colour == background or (r, c) in seen:
                continue
            queue = deque([(r, c)])
            seen.add((r, c))
            cells = set()
            while queue:
                cr, cc = queue.popleft()
                cells.add((cr, cc))
                for dr, dc in neighbours:
                    nr, nc = cr + dr, cc + dc
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and (nr, nc) not in seen
                        and grid[nr][nc] == colour
                    ):
                        seen.add((nr, nc))
                        queue.append((nr, nc))
            comps.append({"colour": colour, "cells": cells, "size": len(cells)})
    return comps


def bbox(cells: Iterable[tuple[int, int]]) -> tuple[int, int, int, int]:
    cells = list(cells)
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def normalize_shape(cells: set[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    r0, _, c0, _ = bbox(cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))


def separator_structure(grid: Grid) -> tuple[int, int]:
    rows, cols = shape(grid)
    row_sep = 0
    col_sep = 0
    for r in range(rows):
        if len(set(grid[r])) == 1:
            row_sep += 1
    for c in range(cols):
        if len({grid[r][c] for r in range(rows)}) == 1:
            col_sep += 1
    return row_sep, col_sep


def panel_count(grid: Grid) -> int:
    row_sep, col_sep = separator_structure(grid)
    return max(1, (row_sep + 1) * (col_sep + 1))


def entropy_from_counts(counts: Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return -sum((count / total) * math.log(count / total + 1e-12, 2) for count in counts.values())


def touches(a: set[tuple[int, int]], b: set[tuple[int, int]]) -> bool:
    for r, c in a:
        for nr in range(r - 1, r + 2):
            for nc in range(c - 1, c + 2):
                if (nr, nc) in b:
                    return True
    return False


def contains(container: set[tuple[int, int]], other: set[tuple[int, int]]) -> bool:
    r0, r1, c0, c1 = bbox(container)
    return all(r0 <= r <= r1 and c0 <= c <= c1 for r, c in other)


def background_confidence(grid: Grid) -> float:
    counts = colour_counts(grid)
    total = sum(counts.values())
    return counts.most_common(1)[0][1] / total if total else 1.0


def aspect_bin(grid: Grid) -> str:
    rows, cols = shape(grid)
    if not rows or not cols:
        return "empty"
    ratio = rows / cols
    if ratio < 0.67:
        return "wide"
    if ratio > 1.5:
        return "tall"
    return "balanced"


def scale_bin(cells: int) -> str:
    if cells < 36:
        return "xs"
    if cells < 100:
        return "sm"
    if cells < 145:
        return "md"
    if cells < 225:
        return "lg"
    return "xl"


def colour_bin(n: int) -> str:
    if n <= 2:
        return "1-2"
    if n <= 4:
        return "3-4"
    if n <= 6:
        return "5-6"
    if n <= 8:
        return "7-8"
    return "9-10"


def object_bin(n: int) -> str:
    if n <= 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 6:
        return "4-6"
    if n <= 10:
        return "7-10"
    return "11+"


def density_bin(value: float) -> str:
    if value < 0.12:
        return "very_sparse"
    if value < 0.28:
        return "sparse"
    if value < 0.45:
        return "medium"
    return "dense"


def bg_conf_bin(value: float) -> str:
    if value > 0.75:
        return "high"
    if value > 0.55:
        return "medium"
    return "low"


def delta_relation_bin(train: list[ExamplePair]) -> str:
    rels = set()
    for pair in train:
        in_shape, out_shape = shape(pair.input), shape(pair.output)
        if in_shape == out_shape:
            rels.add("same")
        elif out_shape[0] >= in_shape[0] and out_shape[1] >= in_shape[1]:
            rels.add("expand")
        elif out_shape[0] <= in_shape[0] and out_shape[1] <= in_shape[1]:
            rels.add("contract")
        else:
            rels.add("mixed")
    return rels.pop() if len(rels) == 1 else "inconsistent"


def infer_transform_tags(task: SyntheticTask | dict) -> tuple[str, ...]:
    if isinstance(task, SyntheticTask):
        family = task.family
        mapping = {
            "F1_multi_move": ("movement", "shape_preserve"),
            "F2_correspondence": ("correspondence", "copy"),
            "F3_relational_selection": ("relational", "recolour"),
            "F4_dense_rearrangement": ("rearrange", "pack"),
            "F5_panel_transform": ("panels", "recompose"),
            "F6_large_output": ("output_expand", "tile"),
            "F7_colour_roles": ("colour_mapping",),
            "F8_container_content": ("containment", "content_transform"),
            "F9_sequence_completion": ("pattern", "completion"),
            "F10_graph_rewrite": ("graph", "rewrite"),
            "F11_occlusion_completion": ("completion", "symmetry"),
            "F12_conditional_composition": ("conditional", "composition"),
        }
        return mapping.get(family, ("unknown",))
    row = task
    rel = delta_relation_bin(row["train"])
    tags = ["shape_preserve" if rel == "same" else "output_expand" if rel == "larger" else "contract"]
    in_colours = set(cell for pair in row["train"] for grid in [pair.input] for row_ in grid for cell in row_)
    out_colours = set(cell for pair in row["train"] for grid in [pair.output] for row_ in grid for cell in row_)
    if out_colours - in_colours:
        tags.append("colour_mapping")
    in_objects = sum(len(connected_components(pair.input)) for pair in row["train"])
    out_objects = sum(len(connected_components(pair.output)) for pair in row["train"])
    if out_objects > in_objects:
        tags.append("copy")
    return tuple(sorted(set(tags)))


def task_from_json(task_id: str, raw: dict) -> dict:
    return {
        "task_id": task_id,
        "train": [ExamplePair(input=pair["input"], output=pair["output"]) for pair in raw["train"]],
        "test": [ExamplePair(input=pair["input"], output=pair.get("output")) for pair in raw["test"]],
    }


def describe_task(task: SyntheticTask | dict) -> dict:
    if isinstance(task, SyntheticTask):
        train = task.train
        test = task.test
        task_id = task.task_id
        family = task.family
        effective_depth = int(task.metadata.get("effective_depth", task.metadata.get("composition_depth", 1)))
        inferred_params = len(task.metadata.get("trace", {}).get("examples", [{}])[0]) if task.metadata.get("trace") else len(task.provenance)
        distractors = 1 if "dense" in task.family_bucket or "panels" in task.family_bucket else 0
    else:
        train = task["train"]
        test = task["test"]
        task_id = task["task_id"]
        family = "reference"
        effective_depth = 1
        inferred_params = 1
        distractors = 0

    known_pairs = train + [pair for pair in test if pair.output is not None]
    input_grids = [pair.input for pair in train + test]
    output_grids = [pair.output for pair in known_pairs]
    in_rows = [shape(grid)[0] for grid in input_grids]
    in_cols = [shape(grid)[1] for grid in input_grids]
    out_rows = [shape(grid)[0] for grid in output_grids]
    out_cols = [shape(grid)[1] for grid in output_grids]
    input_cells = max(r * c for r, c in map(shape, input_grids))
    output_cells = max(r * c for r, c in map(shape, output_grids))
    colours_in = set(cell for grid in input_grids for row in grid for cell in row)
    colours_out = set(cell for grid in output_grids for row in grid for cell in row)
    bg_conf = background_confidence(input_grids[0])
    comps4 = connected_components(input_grids[0], connectivity=4)
    comps8 = connected_components(input_grids[0], connectivity=8)
    shapes4 = [normalize_shape(comp["cells"]) for comp in comps4]
    repeated_shape_count = sum(count for count in Counter(shapes4).values() if count > 1)
    touching_edges = 0
    contain_edges = 0
    for idx, a in enumerate(comps4):
        for b in comps4[idx + 1:]:
            if touches(a["cells"], b["cells"]):
                touching_edges += 1
            if contains(a["cells"], b["cells"]) or contains(b["cells"], a["cells"]):
                contain_edges += 1
    pair_interactions = touching_edges + contain_edges
    separator_rows, separator_cols = separator_structure(input_grids[0])
    role_entropy = entropy_from_counts(colour_counts(input_grids[0]))
    preservation = len(colours_in & colours_out) / max(1, len(colours_in | colours_out))
    affects = sum(1 for i, o in zip(train, train) if i.input != o.output)
    ambiguous = 1.0 if len(train) <= 2 and delta_relation_bin(train) == "same" else 0.0
    demo_diversity = len({json.dumps(pair.input, separators=(",", ":")) for pair in train}) / max(1, len(train))
    holes = sum(1 for comp in comps4 if _component_has_hole(input_grids[0], comp["cells"]))
    alignments = _alignment_count(comps4)
    nearest_pattern = _nearest_signature(comps4)
    return {
        "task_id": task_id,
        "family": family,
        "grid_scale": (
            scale_bin(input_cells),
            scale_bin(output_cells),
            delta_relation_bin(train),
            aspect_bin(input_grids[0]),
            "multi_panel" if panel_count(input_grids[0]) > 1 else "single_panel",
            f"sep_r{min(separator_rows,3)}_c{min(separator_cols,3)}",
        ),
        "colour_structure": (
            colour_bin(len(colours_in)),
            bg_conf_bin(bg_conf),
            "low_entropy" if role_entropy < 1.5 else "mid_entropy" if role_entropy < 2.5 else "high_entropy",
            "high_preserve" if preservation > 0.75 else "mid_preserve" if preservation > 0.45 else "low_preserve",
            f"intro_{min(len(colours_out - colours_in),3)}",
            f"rm_{min(len(colours_in - colours_out),3)}",
        ),
        "object_structure": (
            object_bin(len(comps4)),
            object_bin(len(comps8)),
            "repeat_none" if repeated_shape_count == 0 else "repeat_some",
            "shape_low" if len(set(shapes4)) <= 2 else "shape_high",
            density_bin(sum(comp["size"] for comp in comps4) / max(1, input_cells)),
            "containment" if contain_edges else "flat",
            f"holes_{min(holes,2)}",
            f"touch_{min(touching_edges,3)}",
        ),
        "relational_structure": (
            f"align_{min(alignments,3)}",
            nearest_pattern,
            f"corr_{min(len(comps4),4)}",
            f"contain_depth_{1 if contain_edges else 0}",
            f"pair_{min(pair_interactions,4)}",
            f"deg_{min(_graph_degree_bucket(comps4),4)}",
        ),
        "transformation_structure": (
            f"affected_{min(_affected_objects(train),4)}",
            "shape_preserve" if delta_relation_bin(train) == "same" else "output_expand" if delta_relation_bin(train) == "expand" else "contract_or_mixed",
            *infer_transform_tags(task)[:2],
            f"depth_{min(effective_depth,3)}",
        ),
        "complexity": (
            scale_bin(input_cells + output_cells),
            f"params_{min(inferred_params,4)}",
            f"distractors_{min(distractors,3)}",
            "ambiguous" if ambiguous > 0 else "clear",
            "demo_low" if demo_diversity < 0.6 else "demo_high",
            f"min_examples_{2 if len(train)<=2 else 3 if len(train)<=4 else 4}",
        ),
        "legacy_descriptor": _legacy_descriptor(input_cells, len(colours_in), len(comps4), delta_relation_bin(train)),
        "token_cost_hint": int((input_cells + output_cells) * max(1, len(train))),
        "effective_depth": effective_depth,
    }


def _legacy_descriptor(input_cells: int, n_colours: int, n_objects: int, size_relation: str) -> tuple[str, str, str, str, str]:
    return (
        size_relation if size_relation in {"same", "larger", "smaller"} else "same",
        scale_bin(input_cells),
        colour_bin(n_colours),
        object_bin(n_objects),
        "output-change" if size_relation != "same" else "shape-preserve",
    )


def _component_has_hole(grid: Grid, cells: set[tuple[int, int]]) -> bool:
    r0, r1, c0, c1 = bbox(cells)
    if r1 - r0 < 2 or c1 - c0 < 2:
        return False
    colour = grid[next(iter(cells))[0]][next(iter(cells))[1]]
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if (r, c) not in cells and grid[r][c] != colour:
                return True
    return False


def _alignment_count(comps: list[dict]) -> int:
    count = 0
    centers = []
    for comp in comps:
        rs = [r for r, _ in comp["cells"]]
        cs = [c for _, c in comp["cells"]]
        centers.append((round(sum(rs) / len(rs), 1), round(sum(cs) / len(cs), 1)))
    for idx, (r1, c1) in enumerate(centers):
        for r2, c2 in centers[idx + 1:]:
            if r1 == r2 or c1 == c2:
                count += 1
    return count


def _nearest_signature(comps: list[dict]) -> str:
    if len(comps) < 2:
        return "isolated"
    centers = []
    for comp in comps:
        rs = [r for r, _ in comp["cells"]]
        cs = [c for _, c in comp["cells"]]
        centers.append((sum(rs) / len(rs), sum(cs) / len(cs)))
    dists = []
    for idx, (r1, c1) in enumerate(centers):
        best = 999.0
        for jdx, (r2, c2) in enumerate(centers):
            if idx == jdx:
                continue
            best = min(best, abs(r2 - r1) + abs(c2 - c1))
        dists.append(best)
    mean = sum(dists) / len(dists)
    if mean < 3:
        return "tight"
    if mean < 7:
        return "medium"
    return "loose"


def _graph_degree_bucket(comps: list[dict]) -> int:
    if len(comps) < 2:
        return 0
    degrees = []
    for idx, a in enumerate(comps):
        degree = 0
        for jdx, b in enumerate(comps):
            if idx == jdx:
                continue
            if touches(a["cells"], b["cells"]) or contains(a["cells"], b["cells"]) or contains(b["cells"], a["cells"]):
                degree += 1
        degrees.append(degree)
    return round(sum(degrees) / len(degrees))


def _affected_objects(train: list[ExamplePair]) -> int:
    counts = []
    for pair in train:
        before = len(connected_components(pair.input))
        after = len(connected_components(pair.output))
        counts.append(abs(after - before) + (1 if pair.input != pair.output else 0))
    return max(counts, default=0)


def descriptor_signature(desc: dict) -> tuple:
    return (
        desc["grid_scale"],
        desc["colour_structure"],
        desc["object_structure"],
        desc["relational_structure"],
        desc["transformation_structure"],
        desc["complexity"],
    )


def descriptor_distance(a: dict, b: dict) -> float:
    da = descriptor_signature(a)
    db = descriptor_signature(b)
    distance = 0.0
    for ga, gb in zip(da, db):
        distance += sum(0 if x == y else 1 for x, y in zip(ga, gb)) / max(1, len(ga))
    return round(distance, 4)


def load_reference_tasks() -> dict[str, list[dict]]:
    kaggle_root = DATA_ROOT / "competition_2026" / "extracted"
    training = json.loads((kaggle_root / "arc-agi_training_challenges.json").read_text())
    folds = json.loads((REPO_ROOT / "artifacts" / "ACQ001" / "folds.json").read_text())
    train_ids = set(folds["train_task_ids"])
    dev_ids = set(folds["dev_task_ids"])
    test_ids = set(folds["test_task_ids"])
    grouped = {"arc_train": [], "clean_dev": [], "acq001_full": []}
    for task_id, raw in training.items():
        record = task_from_json(task_id, raw)
        desc = describe_task(record)
        if task_id in train_ids:
            grouped["arc_train"].append(desc)
        if task_id in dev_ids:
            grouped["clean_dev"].append(desc)
        if task_id in test_ids:
            grouped["acq001_full"].append(desc)
    taxonomy_rows = list(csv.DictReader((REPO_ROOT / "artifacts" / "EXP002D" / "error_taxonomy.csv").open(newline="", encoding="utf-8")))
    failure_ids = [row["task_id"] for row in taxonomy_rows if row["category"] == "1_generation_failure"]
    grouped["compressarc_failures"] = [desc for desc in grouped["acq001_full"] if desc["task_id"] in failure_ids]
    return grouped


def load_synthetic_descriptors(path: Path) -> list[dict]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            task = SyntheticTask(
                task_id=raw["task_id"],
                train=[ExamplePair(**pair) for pair in raw["train"]],
                test=[ExamplePair(**pair) for pair in raw["test"]],
                family=raw["family"],
                family_bucket=raw["family_bucket"],
                curriculum_tier=raw["curriculum_tier"],
                program_id=raw["program_id"],
                provenance=raw["provenance"],
                metadata=raw["metadata"],
            )
            rows.append(describe_task(task))
    return rows


def coverage_report(reference: list[dict], dataset: list[dict]) -> dict:
    keys = ("grid_scale", "colour_structure", "object_structure", "relational_structure", "transformation_structure", "complexity")
    dataset_sigs = {descriptor_signature(desc) for desc in dataset}
    dataset_group_bins = {key: {desc[key] for desc in dataset} for key in keys}
    ref_sigs = [descriptor_signature(desc) for desc in reference]
    per_row_hits = []
    unique_hit_count = 0
    for desc in reference:
        matches = sum(1 for key in keys if desc[key] in dataset_group_bins[key])
        per_row_hits.append((matches / len(keys)) ** 3)
        if matches >= 4:
            unique_hit_count += 1
    unique_ref = len(set(ref_sigs))
    unique_cov = unique_hit_count / len(reference) if reference else 0.0
    weighted_cov = sum(per_row_hits) / len(per_row_hits) if per_row_hits else 0.0
    nearest = []
    for ref in reference:
        best = min((descriptor_distance(ref, cand) for cand in dataset), default=6.0)
        nearest.append(best)
    occupancy = {key: len(value) for key, value in dataset_group_bins.items()}
    return {
        "unique_descriptor_coverage": round(unique_cov, 4),
        "weighted_descriptor_coverage": round(weighted_cov, 4),
        "mean_nearest_distance": round(sum(nearest) / len(nearest), 4) if nearest else 0.0,
        "descriptor_bin_occupancy": occupancy,
    }
