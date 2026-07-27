from __future__ import annotations

from dataclasses import dataclass

from src.gen002 import grid as gridmod
from src.gen002 import objects as objectsmod
from src.gen002b.core import ArcTask, SynthProgram, crop_non_background, infer_background


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    family: str
    cost: int


def _identity(grid):
    return grid


def _rotate_90(grid):
    return tuple(zip(*grid[::-1]))


def _rotate_180(grid):
    return tuple(row[::-1] for row in grid[::-1])


def _rotate_270(grid):
    return tuple(zip(*grid))[::-1]


def _reflect_horizontal(grid):
    return tuple(row[::-1] for row in grid)


def _reflect_vertical(grid):
    return grid[::-1]


def _reflect_diagonal(grid):
    return gridmod.transpose(grid)


WHOLE_GRID_TRANSFORMS = (
    ("identity", _identity),
    ("rotate_90", _rotate_90),
    ("rotate_180", _rotate_180),
    ("rotate_270", _rotate_270),
    ("reflect_horizontal", _reflect_horizontal),
    ("reflect_vertical", _reflect_vertical),
    ("reflect_diagonal", _reflect_diagonal),
)


def whole_grid_programs(task: ArcTask) -> list[SynthProgram]:
    programs = []
    for name, fn in WHOLE_GRID_TRANSFORMS:
        if all(fn(pair.input_grid) == pair.output_grid for pair in task.train_pairs):
            programs.append(
                SynthProgram(
                    stage="S2-A",
                    family="grid_transform",
                    name=name,
                    params=(),
                    cost=1,
                    apply_fn=fn,
                )
            )
    return programs


def crop_programs(task: ArcTask) -> list[SynthProgram]:
    programs = []
    for background in infer_background(task):
        if all(crop_non_background(pair.input_grid, background) == pair.output_grid for pair in task.train_pairs):
            programs.append(
                SynthProgram(
                    stage="S2-A",
                    family="grid_crop",
                    name="crop_non_background",
                    params=(("background", background),),
                    cost=2,
                    apply_fn=lambda grid, bg=background: crop_non_background(grid, bg),
                )
            )
    return programs


def colour_map_programs(task: ArcTask) -> list[SynthProgram]:
    mapping: dict[int, int] = {}
    for pair in task.train_pairs:
        if gridmod.dims(pair.input_grid) != gridmod.dims(pair.output_grid):
            return []
        for in_row, out_row in zip(pair.input_grid, pair.output_grid):
            for in_cell, out_cell in zip(in_row, out_row):
                prev = mapping.setdefault(in_cell, out_cell)
                if prev != out_cell:
                    return []
    if not mapping:
        return []
    return [
        SynthProgram(
            stage="S2-A",
            family="colour_role",
            name="global_colour_map",
            params=(("mapping", tuple(sorted(mapping.items()))),),
            cost=2,
            apply_fn=lambda grid, m=mapping: tuple(tuple(m.get(cell, cell) for cell in row) for row in grid),
        )
    ]


def scale_programs(task: ArcTask) -> list[SynthProgram]:
    factors = set()
    for pair in task.train_pairs:
        ih, iw = gridmod.dims(pair.input_grid)
        oh, ow = gridmod.dims(pair.output_grid)
        if ih == 0 or iw == 0 or oh % ih or ow % iw or oh // ih != ow // iw:
            return []
        factor = oh // ih
        if factor < 1 or factor > 6:
            return []
        factors.add(factor)
        expected = tuple(
            tuple(cell for cell in row for _ in range(factor))
            for row in pair.input_grid
            for _ in range(factor)
        )
        if expected != pair.output_grid:
            return []
    if len(factors) != 1:
        return []
    factor = next(iter(factors))
    return [
        SynthProgram(
            stage="S2-A",
            family="pattern_scale",
            name="uniform_scale",
            params=(("factor", factor),),
            cost=3,
            apply_fn=lambda grid, factor=factor: tuple(
                tuple(cell for cell in row for _ in range(factor))
                for row in grid
                for _ in range(factor)
            ),
        )
    ]


def tile_programs(task: ArcTask) -> list[SynthProgram]:
    tile_rows = set()
    tile_cols = set()
    for pair in task.train_pairs:
        ih, iw = gridmod.dims(pair.input_grid)
        oh, ow = gridmod.dims(pair.output_grid)
        if ih == 0 or iw == 0 or oh % ih or ow % iw:
            return []
        n_rows = oh // ih
        n_cols = ow // iw
        if n_rows < 1 or n_cols < 1 or n_rows > 6 or n_cols > 6:
            return []
        expected = tuple(row * n_cols for row in pair.input_grid) * n_rows
        if expected != pair.output_grid:
            return []
        tile_rows.add(n_rows)
        tile_cols.add(n_cols)
    if len(tile_rows) != 1 or len(tile_cols) != 1:
        return []
    n_rows = next(iter(tile_rows))
    n_cols = next(iter(tile_cols))
    return [
        SynthProgram(
            stage="S2-A",
            family="pattern_tile",
            name="tile_input",
            params=(("n_rows", n_rows), ("n_cols", n_cols)),
            cost=3,
            apply_fn=lambda grid, n_rows=n_rows, n_cols=n_cols: tuple(row * n_cols for row in grid) * n_rows,
        )
    ]


def symmetry_completion_programs(task: ArcTask) -> list[SynthProgram]:
    programs = []
    for axis, fn in (("vertical", _reflect_horizontal), ("horizontal", _reflect_vertical)):
        if all(
            tuple(
                tuple(max(a, b) for a, b in zip(in_row, mir_row))
                for in_row, mir_row in zip(pair.input_grid, fn(pair.input_grid))
            )
            == pair.output_grid
            for pair in task.train_pairs
        ):
            programs.append(
                SynthProgram(
                    stage="S2-A",
                    family="symmetry_completion",
                    name=f"overlay_{axis}_mirror",
                    params=(("axis", axis),),
                    cost=4,
                    apply_fn=lambda grid, mirror=fn: tuple(
                        tuple(max(a, b) for a, b in zip(in_row, mir_row))
                        for in_row, mir_row in zip(grid, mirror(grid))
                    ),
                )
            )
    return programs


def _extract_single_object(grid, background: int, connectivity: int):
    objs = objectsmod.extract_objects(grid, background=background, connectivity=connectivity)
    if len(objs) != 1:
        return None
    return objs[0]


def single_object_translation_programs(task: ArcTask) -> list[SynthProgram]:
    programs = []
    for background in infer_background(task):
        for connectivity in (4, 8):
            deltas = set()
            colours = set()
            shape_ids = set()
            for pair in task.train_pairs:
                in_obj = _extract_single_object(pair.input_grid, background, connectivity)
                out_obj = _extract_single_object(pair.output_grid, background, connectivity)
                if in_obj is None or out_obj is None:
                    deltas = set()
                    break
                if in_obj.shape_id != out_obj.shape_id:
                    deltas = set()
                    break
                shape_ids.add(in_obj.shape_id)
                colours.add(tuple(sorted(in_obj.colour_set)))
                ir0, ic0, *_ = in_obj.bbox
                or0, oc0, *_ = out_obj.bbox
                deltas.add((or0 - ir0, oc0 - ic0))
            if len(deltas) == 1 and len(shape_ids) == 1 and len(colours) == 1:
                dr, dc = next(iter(deltas))

                def _translate_single(grid, bg=background, conn=connectivity, dr=dr, dc=dc):
                    obj = _extract_single_object(grid, bg, conn)
                    if obj is None:
                        raise ValueError("no single object")
                    h, w = gridmod.dims(grid)
                    out = [[bg] * w for _ in range(h)]
                    for (r, c), colour in obj.colours:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            out[nr][nc] = colour
                    return tuple(tuple(row) for row in out)

                if all(_translate_single(pair.input_grid) == pair.output_grid for pair in task.train_pairs):
                    programs.append(
                        SynthProgram(
                            stage="S2-B",
                            family="object_correspondence",
                            name="single_object_translate",
                            params=(("background", background), ("connectivity", connectivity), ("delta", (dr, dc))),
                            cost=5,
                            apply_fn=_translate_single,
                        )
                    )
    return programs


def largest_object_crop_programs(task: ArcTask) -> list[SynthProgram]:
    programs = []
    for background in infer_background(task):
        for connectivity in (4, 8):
            def _largest_crop(grid, bg=background, conn=connectivity):
                objs = objectsmod.extract_objects(grid, background=bg, connectivity=conn)
                if not objs:
                    raise ValueError("no objects")
                obj = max(objs, key=lambda o: (o.area, -o.bbox[0], -o.bbox[1]))
                r0, c0, r1, c1 = obj.bbox
                return tuple(row[c0 : c1 + 1] for row in grid[r0 : r1 + 1])

            try:
                matches = all(_largest_crop(pair.input_grid) == pair.output_grid for pair in task.train_pairs)
            except Exception:  # noqa: BLE001
                matches = False
            if matches:
                programs.append(
                    SynthProgram(
                        stage="S2-B",
                        family="object_selection",
                        name="largest_object_crop",
                        params=(("background", background), ("connectivity", connectivity)),
                        cost=4,
                        apply_fn=_largest_crop,
                    )
                )
    return programs


TEMPLATE_SPECS = (
    TemplateSpec("whole_grid", "grid_transform", 1),
    TemplateSpec("crop_non_background", "grid_crop", 2),
    TemplateSpec("global_colour_map", "colour_role", 2),
    TemplateSpec("uniform_scale", "pattern_scale", 3),
    TemplateSpec("tile_input", "pattern_tile", 3),
    TemplateSpec("overlay_symmetry", "symmetry_completion", 4),
    TemplateSpec("single_object_translate", "object_correspondence", 5),
    TemplateSpec("largest_object_crop", "object_selection", 4),
)
