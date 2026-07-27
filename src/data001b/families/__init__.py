from __future__ import annotations

import json
import random
from dataclasses import dataclass

from src.data001.program import Operation, Program
from src.data001.provenance import GENERATOR_VERSION, sha256_text, stable_seed, task_hash
from src.data001.task_schema import ExamplePair, SyntheticTask

from src.data001b.scenes import (
    Scene,
    add_container,
    blank,
    clone_grid,
    make_container_scene,
    make_large_scene,
    make_panel_scene,
    make_sequence_scene,
    place_object,
    shape,
)


@dataclass(frozen=True)
class FamilySpec:
    family_id: str
    display_name: str
    canonical_family: str
    effective_depth: int
    validation_variant: str
    scene_modes: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class FamilyBundle:
    task: SyntheticTask
    program: Program
    trace: dict
    validation_bucket: str
    syntactic_depth: int
    effective_depth: int


FAMILY_SPECS: dict[str, FamilySpec] = {
    "F1": FamilySpec("F1", "multi_object_shape_preserving_movement", "F1_multi_move", 1, "anchor_markers", ("large_sparse", "large_dense"), ("movement", "shape_preserve", "multi_object")),
    "F2": FamilySpec("F2", "object_correspondence", "F2_correspondence", 2, "paired_markers", ("large_sparse", "high_object"), ("correspondence", "copy", "move")),
    "F3": FamilySpec("F3", "relational_selection", "F3_relational_selection", 2, "containment", ("large_dense", "containers"), ("relational", "selection", "recolour")),
    "F4": FamilySpec("F4", "dense_object_rearrangement", "F4_dense_rearrangement", 2, "pack_columns", ("large_dense",), ("sort", "pack", "recompose")),
    "F5": FamilySpec("F5", "panel_transformation", "F5_panel_transform", 2, "column_panels", ("panels",), ("panels", "transfer", "recompose")),
    "F6": FamilySpec("F6", "large_output_construction", "F6_large_output", 2, "vertical_tiling", ("sequence", "panels"), ("output_expand", "tile", "concatenate")),
    "F7": FamilySpec("F7", "multicolour_role_mapping", "F7_colour_roles", 1, "dense_palette", ("large_dense", "high_colour"), ("colour_roles", "permutation")),
    "F8": FamilySpec("F8", "container_content_transformation", "F8_container_content", 2, "nested_containers", ("containers",), ("containment", "content_transform")),
    "F9": FamilySpec("F9", "pattern_sequence_completion", "F9_sequence_completion", 1, "vertical_sequence", ("sequence",), ("pattern", "completion", "sequence")),
    "F10": FamilySpec("F10", "graph_rewrite", "F10_graph_rewrite", 2, "degree_recolour", ("large_dense",), ("graph", "rewrite", "connect")),
    "F11": FamilySpec("F11", "occlusion_completion", "F11_occlusion_completion", 2, "partial_symmetry", ("sequence", "large_sparse"), ("partial_shape", "completion")),
    "F12": FamilySpec("F12", "conditional_multistage_composition", "F12_conditional_composition", 3, "panel_then_recolour", ("panels", "containers"), ("conditional", "composition", "multi_stage")),
}


def _program(seed: int, spec: FamilySpec, operations: list[Operation], params: dict, variant: str) -> Program:
    return Program(
        program_id=f"data001b-{spec.family_id.lower()}-{sha256_text(f'{seed}-{variant}')[:10]}",
        family=spec.canonical_family,
        tier=min(spec.effective_depth + 1, 5),
        operations=operations,
        parameter_bindings=params,
        labels=list(spec.tags) + [variant],
        version="data001b.v1",
    )


def _task(seed: int, spec: FamilySpec, variant: str, train: list[ExamplePair], test: list[ExamplePair], program: Program, trace: dict) -> SyntheticTask:
    metadata = {
        "syntactic_depth": len(program.operations),
        "effective_depth": spec.effective_depth,
        "variant": variant,
        "trace": trace,
        "size_relation": _size_relation([p.input for p in train + test], [p.output for p in train + test]),
        "composition_depth": spec.effective_depth,
        "family_id": spec.family_id,
    }
    provenance = {
        "seed": seed,
        "generator_version": "data001b.v1",
        "program_version": program.version,
        "family_id": spec.family_id,
        "variant": variant,
    }
    task = SyntheticTask(
        task_id=f"data001b-{sha256_text(f'{spec.family_id}-{variant}-{seed}')[:12]}",
        train=train,
        test=test,
        family=spec.canonical_family,
        family_bucket=f"{spec.family_id}:{variant}",
        curriculum_tier=min(spec.effective_depth + 1, 5),
        program_id=program.program_id,
        provenance=provenance,
        metadata=metadata,
    )
    task.provenance["task_hash"] = task_hash(task)
    return task


def _size_relation(inputs: list[list[list[int]]], outputs: list[list[list[int]]]) -> str:
    rel = set()
    for inp, out in zip(inputs, outputs):
        ishape = shape(inp)
        oshape = shape(out)
        if ishape == oshape:
            rel.add("same")
        elif oshape[0] >= ishape[0] and oshape[1] >= ishape[1]:
            rel.add("larger")
        elif oshape[0] <= ishape[0] and oshape[1] <= ishape[1]:
            rel.add("smaller")
        else:
            rel.add("mixed")
    return rel.pop() if len(rel) == 1 else "inconsistent"


def _translate_cells(cells: tuple[tuple[int, int], ...], dr: int, dc: int) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((r + dr, c + dc) for r, c in cells))


def _repaint(grid, old_cells, new_cells, colour, background=0):
    out = clone_grid(grid)
    for r, c in old_cells:
        out[r][c] = background
    for r, c in new_cells:
        if 0 <= r < len(out) and 0 <= c < len(out[0]):
            out[r][c] = colour
    return out


def _pair_from_scene(scene: Scene, output) -> ExamplePair:
    return ExamplePair(input=scene.grid, output=output)


def _family_scene(seed: int, spec: FamilySpec, variant: str, pair_index: int) -> Scene:
    local = stable_seed("data001b-scene", spec.family_id, variant, pair_index, seed)
    if spec.family_id in {"F1", "F2", "F7", "F10"}:
        return make_large_scene(local, dense=spec.family_id in {"F7", "F10"}, high_colour=True, high_objects=True)
    if spec.family_id in {"F3", "F8"}:
        return make_container_scene(local, nested=variant == spec.validation_variant or spec.family_id == "F8")
    if spec.family_id in {"F5", "F12"}:
        return make_panel_scene(local, orientation="cols" if variant == spec.validation_variant else "rows", uneven=True)
    if spec.family_id in {"F6", "F9", "F11"}:
        return make_sequence_scene(local, axis="vertical" if variant == spec.validation_variant else "horizontal", missing=True)
    return make_large_scene(local, dense=True, high_colour=False, high_objects=True)


def _build_family(seed: int, spec: FamilySpec, variant: str) -> FamilyBundle:
    rng = random.Random(seed)
    train = []
    trace = {"family_id": spec.family_id, "variant": variant, "examples": []}
    n_train = rng.randint(2, 4)
    program_ops = [Operation(kind=spec.canonical_family, params={"variant": variant})]
    params = {"variant": variant}
    if spec.effective_depth >= 2:
        program_ops.append(Operation(kind="stage_two", params={"family": spec.family_id}))
    if spec.effective_depth >= 3:
        program_ops.append(Operation(kind="stage_three", params={"family": spec.family_id}))
    program = _program(seed, spec, program_ops, params, variant)
    for idx in range(n_train + 1):
        scene = _family_scene(seed, spec, variant, idx)
        output, example_trace = _apply_family(spec, variant, scene)
        pair = _pair_from_scene(scene, output)
        if idx < n_train:
            train.append(pair)
        else:
            test = [pair]
        trace["examples"].append(example_trace)
    task = _task(seed, spec, variant, train, test, program, trace)
    return FamilyBundle(
        task=task,
        program=program,
        trace=trace,
        validation_bucket=f"{spec.family_id}:{spec.validation_variant}",
        syntactic_depth=len(program_ops),
        effective_depth=spec.effective_depth,
    )


def _apply_family(spec: FamilySpec, variant: str, scene: Scene) -> tuple[list[list[int]], dict]:
    if spec.family_id == "F1":
        objects = [o for o in scene.objects if o.role == "object"][: min(4, len(scene.objects))]
        dr, dc = (1, 1) if variant == "anchor_markers" else (-1, 2)
        out = clone_grid(scene.grid)
        for obj in objects:
            out = _repaint(out, obj.cells, _translate_cells(obj.cells, dr, dc), obj.colour, scene.background)
        return out, {"move_vector": [dr, dc], "n_selected": len(objects)}

    if spec.family_id == "F2":
        objects = [o for o in scene.objects if o.role == "object"][: min(5, len(scene.objects))]
        out = clone_grid(scene.grid)
        for idx, obj in enumerate(objects):
            dr = 0 if idx % 2 == 0 else 2
            dc = 3 if idx % 2 == 0 else 0
            for r, c in _translate_cells(obj.cells, dr, dc):
                if 0 <= r < len(out) and 0 <= c < len(out[0]):
                    out[r][c] = obj.colour
        return out, {"correspondence_count": len(objects), "mode": "copy_to_marker"}

    if spec.family_id == "F3":
        out = clone_grid(scene.grid)
        target_colour = 9
        selected = [o for o in scene.objects if o.role in {"contained", "container"} and o.shape_name != "container"][:6]
        for obj in selected:
            for r, c in obj.cells:
                out[r][c] = target_colour
        return out, {"predicate": "contained", "affected": len(selected)}

    if spec.family_id == "F4":
        movable = [o for o in scene.objects if o.role == "object"]
        ordered = sorted(movable, key=lambda o: (len(o.cells), o.colour))
        out = blank(len(scene.grid), len(scene.grid[0]), scene.background)
        cursor_r, cursor_c = 1, 1
        for obj in ordered:
            min_r = min(r for r, _ in obj.cells)
            min_c = min(c for _, c in obj.cells)
            norm = sorted((r - min_r, c - min_c) for r, c in obj.cells)
            height = max(r for r, _ in norm) + 1
            width = max(c for _, c in norm) + 1
            if cursor_c + width >= len(out[0]):
                cursor_r += 4
                cursor_c = 1
            for dr, dc in norm:
                if cursor_r + dr < len(out) and cursor_c + dc < len(out[0]):
                    out[cursor_r + dr][cursor_c + dc] = obj.colour
            cursor_c += width + 1
        return out, {"sort_key": "area_then_colour", "n_objects": len(ordered)}

    if spec.family_id == "F5":
        grid = scene.grid
        sep = scene.metadata["separator_colour"]
        if scene.metadata["orientation"] == "rows":
            panels = []
            current = []
            for row in grid:
                if all(cell == sep for cell in row):
                    if current:
                        panels.append(current)
                        current = []
                else:
                    current.append(list(row))
            if current:
                panels.append(current)
            transformed = [list(reversed(panel)) for panel in panels]
            out = []
            for idx, panel in enumerate(transformed):
                out.extend(panel)
                if idx < len(transformed) - 1:
                    out.append([sep] * len(panel[0]))
            return out, {"panels": len(panels), "operation": "vertical_flip_each_panel"}
        sep_col = scene.metadata["separator_colour"]
        cols = len(grid[0])
        split_cols = [c for c in range(cols) if all(grid[r][c] == sep_col for r in range(len(grid)))]
        pieces = []
        start = 0
        for col in split_cols + [cols]:
            if start < col:
                pieces.append([row[start:col] for row in grid])
            start = col + 1
        pieces = [list(reversed(piece)) for piece in pieces]
        out = []
        for r in range(len(grid)):
            row = []
            for idx, piece in enumerate(pieces):
                row.extend(piece[r])
                if idx < len(pieces) - 1:
                    row.append(sep_col)
            out.append(row)
        return out, {"panels": len(pieces), "operation": "horizontal_flip_each_panel"}

    if spec.family_id == "F6":
        motif_cells = [o for o in scene.objects if o.role == "motif"]
        if not motif_cells:
            return scene.grid, {"repeat_count": 1}
        motif = motif_cells[0]
        min_r = min(r for r, _ in motif.cells)
        min_c = min(c for _, c in motif.cells)
        norm = sorted((r - min_r, c - min_c) for r, c in motif.cells)
        height = max(r for r, _ in norm) + 1
        width = max(c for _, c in norm) + 1
        repeat = scene.metadata["count"]
        if variant == spec.validation_variant:
            out = blank(repeat * (height + 1), width + 2, scene.background)
            for idx in range(repeat):
                for dr, dc in norm:
                    out[idx * (height + 1) + dr][1 + dc] = motif.colour
        else:
            out = blank(height + 2, repeat * (width + 1), scene.background)
            for idx in range(repeat):
                for dr, dc in norm:
                    out[1 + dr][idx * (width + 1) + dc] = motif.colour
        return out, {"repeat_count": repeat, "expand": True}

    if spec.family_id == "F7":
        colours = sorted({o.colour for o in scene.objects if o.role == "object"})
        mapping = {colour: colours[-(idx + 1)] for idx, colour in enumerate(colours)}
        out = clone_grid(scene.grid)
        for r, row in enumerate(out):
            for c, cell in enumerate(row):
                if cell in mapping:
                    out[r][c] = mapping[cell]
        return out, {"mapping_size": len(mapping), "mode": "role_permutation"}

    if spec.family_id == "F8":
        out = clone_grid(scene.grid)
        containers = [o for o in scene.objects if o.role == "container"]
        contained = [o for o in scene.objects if o.role == "contained"]
        for idx, container in enumerate(containers[:2]):
            colour = container.colour
            min_r = min(r for r, _ in container.cells)
            max_r = max(r for r, _ in container.cells)
            min_c = min(c for _, c in container.cells)
            max_c = max(c for _, c in container.cells)
            for r in range(min_r + 1, max_r):
                for c in range(min_c + 1, max_c):
                    out[r][c] = colour if idx == 0 else out[r][c]
        for obj in contained[:2]:
            for r, c in obj.cells:
                if r + 1 < len(out):
                    out[r + 1][c] = obj.colour
        return out, {"containers": len(containers), "contained": len(contained)}

    if spec.family_id == "F9":
        axis = scene.metadata["axis"]
        motif_name = scene.metadata["motif_name"]
        colour = next((o.colour for o in scene.objects if o.role == "motif"), 1)
        grid = clone_grid(scene.grid)
        count = scene.metadata["count"]
        if axis == "horizontal":
            left = 1 + (count - 1) * 3
            place_object(grid, motif_name, colour, 2, left, role="motif", variant=0)
        else:
            top = 1 + (count - 1) * 3
            place_object(grid, motif_name, colour, top, 3, role="motif", variant=0)
        return grid, {"axis": axis, "completed_count": count}

    if spec.family_id == "F10":
        out = clone_grid(scene.grid)
        objects = [o for o in scene.objects if o.role == "object"]
        if not objects:
            return out, {"affected": 0}
        anchor = objects[0]
        for obj in objects[1:6]:
            ar = sum(r for r, _ in anchor.cells) // len(anchor.cells)
            ac = sum(c for _, c in anchor.cells) // len(anchor.cells)
            br = sum(r for r, _ in obj.cells) // len(obj.cells)
            bc = sum(c for _, c in obj.cells) // len(obj.cells)
            steps = max(abs(br - ar), abs(bc - ac))
            for step in range(steps + 1):
                rr = ar + round((br - ar) * step / max(steps, 1))
                cc = ac + round((bc - ac) * step / max(steps, 1))
                out[rr][cc] = obj.colour
        return out, {"anchor_colour": anchor.colour, "connected": min(5, len(objects) - 1)}

    if spec.family_id == "F11":
        out = clone_grid(scene.grid)
        rows, cols = len(out), len(out[0])
        for r in range(rows):
            for c in range(cols // 2):
                if out[r][c] != scene.background and out[r][cols - 1 - c] == scene.background:
                    out[r][cols - 1 - c] = out[r][c]
        return out, {"completion": "horizontal_mirror"}

    if spec.family_id == "F12":
        grid, trace = _apply_family(F5_spec(), variant, scene) if "panels" in scene.mode else _apply_family(F8_spec(), variant, scene)
        temp_scene = Scene(grid=grid, mode=scene.mode, background=scene.background, objects=scene.objects, metadata=scene.metadata)
        recoloured, trace2 = _apply_family(F7_spec(), variant, temp_scene)
        return recoloured, {"stage1": trace, "stage2": trace2, "branch": "panel" if "panel" in scene.mode else "container"}

    return scene.grid, {"noop": True}


def F5_spec() -> FamilySpec:
    return FAMILY_SPECS["F5"]


def F7_spec() -> FamilySpec:
    return FAMILY_SPECS["F7"]


def F8_spec() -> FamilySpec:
    return FAMILY_SPECS["F8"]


def generate_family_task(family_id: str, serial: int, variant: str | None = None) -> FamilyBundle:
    spec = FAMILY_SPECS[family_id]
    variant = variant or spec.validation_variant
    seed = stable_seed("data001b", family_id, variant, serial)
    return _build_family(seed, spec, variant)


def family_variants(spec: FamilySpec) -> list[str]:
    base = {
        "F1": ["shared_vector", "anchor_markers"],
        "F2": ["order_pairing", "paired_markers"],
        "F3": ["touching", "containment"],
        "F4": ["pack_rows", "pack_columns"],
        "F5": ["row_panels", "column_panels"],
        "F6": ["horizontal_tiling", "vertical_tiling"],
        "F7": ["role_swap", "dense_palette"],
        "F8": ["container_fill", "nested_containers"],
        "F9": ["horizontal_sequence", "vertical_sequence"],
        "F10": ["anchor_connect", "degree_recolour"],
        "F11": ["repeat_completion", "partial_symmetry"],
        "F12": ["container_then_move", "panel_then_recolour"],
    }
    return base[spec.family_id]

