from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass

Grid = list[list[int]]


SHAPES: dict[str, list[tuple[int, int]]] = {
    "square2": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "rect3": [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)],
    "line3h": [(0, 0), (0, 1), (0, 2)],
    "line3v": [(0, 0), (1, 0), (2, 0)],
    "l3": [(0, 0), (1, 0), (2, 0), (2, 1)],
    "plus5": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],
    "zig4": [(0, 0), (0, 1), (1, 1), (1, 2)],
    "diag3": [(0, 0), (1, 1), (2, 2)],
    "frame3": [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)],
    "tee4": [(0, 0), (0, 1), (0, 2), (1, 1)],
}


@dataclass(frozen=True)
class SceneObject:
    shape_name: str
    colour: int
    top: int
    left: int
    cells: tuple[tuple[int, int], ...]
    role: str


@dataclass(frozen=True)
class Scene:
    grid: Grid
    mode: str
    background: int
    objects: tuple[SceneObject, ...]
    metadata: dict


def blank(height: int, width: int, fill: int = 0) -> Grid:
    return [[fill for _ in range(width)] for _ in range(height)]


def clone_grid(grid: Grid) -> Grid:
    return [list(row) for row in grid]


def shape(grid: Grid) -> tuple[int, int]:
    return (len(grid), len(grid[0]) if grid else 0)


def sample_palette(rng: random.Random, n: int, background: int | None = None) -> list[int]:
    palette = list(range(10))
    rng.shuffle(palette)
    if background is not None and background in palette:
        palette.remove(background)
    return palette[:n]


def normalize_cells(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return sorted((r - min_r, c - min_c) for r, c in cells)


def rotate_shape(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return normalize_cells([(c, -r) for r, c in cells])


def reflect_shape(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return normalize_cells([(r, -c) for r, c in cells])


def orient_shape(shape_name: str, variant: int) -> list[tuple[int, int]]:
    cells = list(SHAPES[shape_name])
    v = variant % 8
    if v >= 4:
        cells = reflect_shape(cells)
    for _ in range(v % 4):
        cells = rotate_shape(cells)
    return cells


def bbox(cells: list[tuple[int, int]]) -> tuple[int, int]:
    max_r = max(r for r, _ in cells)
    max_c = max(c for _, c in cells)
    return (max_r + 1, max_c + 1)


def can_place(
    grid: Grid,
    cells: list[tuple[int, int]],
    top: int,
    left: int,
    allow_touching: bool,
    allow_overlap: bool,
) -> bool:
    rows, cols = shape(grid)
    for dr, dc in cells:
        r, c = top + dr, left + dc
        if not (0 <= r < rows and 0 <= c < cols):
            return False
        if not allow_overlap and grid[r][c] != 0:
            return False
        if not allow_touching:
            for nr in range(r - 1, r + 2):
                for nc in range(c - 1, c + 2):
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != 0:
                        if (nr, nc) != (r, c):
                            return False
    return True


def place_object(
    grid: Grid,
    shape_name: str,
    colour: int,
    top: int,
    left: int,
    role: str = "object",
    variant: int = 0,
) -> SceneObject:
    cells = orient_shape(shape_name, variant)
    for dr, dc in cells:
        grid[top + dr][left + dc] = colour
    abs_cells = tuple(sorted((top + dr, left + dc) for dr, dc in cells))
    return SceneObject(
        shape_name=shape_name,
        colour=colour,
        top=top,
        left=left,
        cells=abs_cells,
        role=role,
    )


def add_separator_row(grid: Grid, row: int, colour: int) -> None:
    for c in range(len(grid[0])):
        grid[row][c] = colour


def add_separator_col(grid: Grid, col: int, colour: int) -> None:
    for r in range(len(grid)):
        grid[r][col] = colour


def add_container(grid: Grid, top: int, left: int, height: int, width: int, colour: int) -> SceneObject:
    cells = []
    for c in range(left, left + width):
        grid[top][c] = colour
        grid[top + height - 1][c] = colour
        cells.append((top, c))
        cells.append((top + height - 1, c))
    for r in range(top + 1, top + height - 1):
        grid[r][left] = colour
        grid[r][left + width - 1] = colour
        cells.append((r, left))
        cells.append((r, left + width - 1))
    return SceneObject(
        shape_name="container",
        colour=colour,
        top=top,
        left=left,
        cells=tuple(sorted(set(cells))),
        role="container",
    )


def occupied_fraction(grid: Grid, background: int = 0) -> float:
    total = len(grid) * len(grid[0])
    occupied = sum(1 for row in grid for cell in row if cell != background)
    return occupied / total if total else 0.0


def background_confidence(grid: Grid) -> float:
    counts = Counter(cell for row in grid for cell in row)
    total = sum(counts.values())
    return counts.most_common(1)[0][1] / total if total else 1.0


def _place_many_objects(
    grid: Grid,
    rng: random.Random,
    n_objects: int,
    palette: list[int],
    shape_names: list[str],
    allow_touching: bool,
    allow_overlap: bool,
    roles: list[str] | None = None,
) -> list[SceneObject]:
    placed: list[SceneObject] = []
    roles = roles or ["object"] * n_objects
    for index in range(n_objects):
        shape_name = shape_names[index % len(shape_names)]
        colour = palette[index % len(palette)]
        variant = rng.randint(0, 7)
        cells = orient_shape(shape_name, variant)
        h, w = bbox(cells)
        for _ in range(60):
            top = rng.randint(0, max(0, len(grid) - h))
            left = rng.randint(0, max(0, len(grid[0]) - w))
            if can_place(grid, cells, top, left, allow_touching, allow_overlap):
                placed.append(
                    place_object(
                        grid,
                        shape_name=shape_name,
                        colour=colour,
                        top=top,
                        left=left,
                        role=roles[index],
                        variant=variant,
                    )
                )
                break
    return placed


def make_large_scene(seed: int, dense: bool, high_colour: bool, high_objects: bool) -> Scene:
    rng = random.Random(seed)
    rows = rng.randint(12, 18)
    cols = rng.randint(12, 20)
    background = rng.choice([0, rng.randint(1, 2)])
    grid = blank(rows, cols, background)
    palette = sample_palette(rng, rng.randint(7, 9) if high_colour else rng.randint(4, 6), background)
    n_objects = rng.randint(10, 18) if high_objects else rng.randint(6, 10)
    shapes = list(SHAPES)
    rng.shuffle(shapes)
    objects = _place_many_objects(
        grid,
        rng,
        n_objects=n_objects,
        palette=palette,
        shape_names=shapes,
        allow_touching=dense,
        allow_overlap=False,
    )
    return Scene(
        grid=grid,
        mode="large_dense" if dense else "large_sparse",
        background=background,
        objects=tuple(objects),
        metadata={
            "rows": rows,
            "cols": cols,
            "n_objects": len(objects),
            "n_colours": len(set(cell for row in grid for cell in row)),
            "occupied_fraction": round(occupied_fraction(grid, background), 4),
            "background_confidence": round(background_confidence(grid), 4),
        },
    )


def make_panel_scene(seed: int, orientation: str, uneven: bool) -> Scene:
    rng = random.Random(seed)
    background = 0
    sep_colour = rng.randint(1, 3)
    if orientation == "rows":
        heights = [rng.randint(4, 6), rng.randint(4, 6)]
        if uneven:
            heights.append(rng.randint(3, 7))
        rows = sum(heights) + len(heights) - 1
        cols = rng.randint(10, 16)
        grid = blank(rows, cols, background)
        objects = []
        cursor = 0
        for idx, height in enumerate(heights):
            sub = blank(height, cols, background)
            palette = sample_palette(rng, rng.randint(4, 7), background)
            objs = _place_many_objects(
                sub, rng, n_objects=rng.randint(3, 6), palette=palette,
                shape_names=list(SHAPES), allow_touching=True, allow_overlap=False
            )
            for r in range(height):
                grid[cursor + r] = sub[r]
            objects.extend(
                SceneObject(
                    shape_name=o.shape_name,
                    colour=o.colour,
                    top=o.top + cursor,
                    left=o.left,
                    cells=tuple((r + cursor, c) for r, c in o.cells),
                    role="panel_object",
                )
                for o in objs
            )
            cursor += height
            if idx < len(heights) - 1:
                add_separator_row(grid, cursor, sep_colour)
                cursor += 1
        return Scene(
            grid=grid,
            mode="panels_rows",
            background=background,
            objects=tuple(objects),
            metadata={"panels": len(heights), "separator_colour": sep_colour, "orientation": orientation},
        )

    widths = [rng.randint(4, 6), rng.randint(4, 6)]
    if uneven:
        widths.append(rng.randint(3, 7))
    cols = sum(widths) + len(widths) - 1
    rows = rng.randint(10, 16)
    grid = blank(rows, cols, background)
    objects = []
    cursor = 0
    for idx, width in enumerate(widths):
        sub = blank(rows, width, background)
        palette = sample_palette(rng, rng.randint(4, 7), background)
        objs = _place_many_objects(
            sub, rng, n_objects=rng.randint(3, 6), palette=palette,
            shape_names=list(SHAPES), allow_touching=True, allow_overlap=False
        )
        for r in range(rows):
            for c in range(width):
                grid[r][cursor + c] = sub[r][c]
        objects.extend(
            SceneObject(
                shape_name=o.shape_name,
                colour=o.colour,
                top=o.top,
                left=o.left + cursor,
                cells=tuple((r, c + cursor) for r, c in o.cells),
                role="panel_object",
            )
            for o in objs
        )
        cursor += width
        if idx < len(widths) - 1:
            add_separator_col(grid, cursor, sep_colour)
            cursor += 1
    return Scene(
        grid=grid,
        mode="panels_cols",
        background=background,
        objects=tuple(objects),
        metadata={"panels": len(widths), "separator_colour": sep_colour, "orientation": orientation},
    )


def make_container_scene(seed: int, nested: bool) -> Scene:
    rng = random.Random(seed)
    rows = rng.randint(12, 18)
    cols = rng.randint(12, 18)
    background = 0
    grid = blank(rows, cols, background)
    palette = sample_palette(rng, 8, background)
    objects: list[SceneObject] = []
    n_containers = 2 if not nested else 3
    for idx in range(n_containers):
        ch = rng.randint(4, 6)
        cw = rng.randint(4, 7)
        top = 1 + idx * (ch + 1)
        left = 1 + (idx % 2) * (cw + 2)
        if top + ch >= rows or left + cw >= cols:
            break
        container = add_container(grid, top, left, ch, cw, palette[idx])
        objects.append(container)
        inner_count = rng.randint(1, 3)
        for j in range(inner_count):
            shape_name = rng.choice(list(SHAPES))
            cells = orient_shape(shape_name, rng.randint(0, 7))
            h, w = bbox(cells)
            if ch - 2 - h < 0 or cw - 2 - w < 0:
                continue
            inner_top = rng.randint(top + 1, top + ch - h - 1)
            inner_left = rng.randint(left + 1, left + cw - w - 1)
            obj = place_object(
                grid,
                shape_name=shape_name,
                colour=palette[(idx + j + 3) % len(palette)],
                top=inner_top,
                left=inner_left,
                role="contained",
                variant=rng.randint(0, 7),
            )
            objects.append(obj)
        if nested and idx == 0 and top + 2 < rows and left + 2 < cols:
            nested_box = add_container(grid, top + 1, left + 1, ch - 2, cw - 2, palette[-1])
            objects.append(nested_box)
    return Scene(
        grid=grid,
        mode="containers_nested" if nested else "containers_flat",
        background=background,
        objects=tuple(objects),
        metadata={"nested": nested, "n_objects": len(objects)},
    )


def make_sequence_scene(seed: int, axis: str, missing: bool) -> Scene:
    rng = random.Random(seed)
    background = 0
    count = rng.randint(4, 6)
    step = 3
    if axis == "horizontal":
        rows = rng.randint(8, 12)
        cols = max(rng.randint(12, 18), 4 + count * step)
    else:
        rows = max(rng.randint(8, 12), 3 + count * step)
        cols = rng.randint(12, 18)
    grid = blank(rows, cols, background)
    palette = sample_palette(rng, 6, background)
    motif_name = rng.choice(["square2", "l3", "plus5", "zig4"])
    motif_colour = palette[0]
    objects = []
    missing_index = rng.randint(1, count - 2) if missing else -1
    for idx in range(count):
        if idx == missing_index:
            continue
        top = 2 if axis == "horizontal" else 1 + idx * step
        left = 1 + idx * step if axis == "horizontal" else 3
        objects.append(
            place_object(
                grid,
                shape_name=motif_name,
                colour=motif_colour,
                top=top,
                left=left,
                role="motif",
                variant=0,
            )
        )
    return Scene(
        grid=grid,
        mode=f"sequence_{axis}",
        background=background,
        objects=tuple(objects),
        metadata={"axis": axis, "missing": missing, "motif_name": motif_name, "count": count},
    )
