from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

from .program import Operation, Program
from .task_schema import Grid


@dataclass(frozen=True)
class ExecutionTrace:
    family: str
    program_id: str
    operations: list[dict]
    intermediate_grids: list[Grid]


def clone_grid(grid: Grid) -> Grid:
    return [list(row) for row in grid]


def blank(height: int, width: int, fill: int = 0) -> Grid:
    return [[fill for _ in range(width)] for _ in range(height)]


def shape(grid: Grid) -> tuple[int, int]:
    return (len(grid), len(grid[0]) if grid else 0)


def most_common_colour(grid: Grid) -> int:
    counts = Counter(cell for row in grid for cell in row)
    return counts.most_common(1)[0][0] if counts else 0


def connected_components(grid: Grid, background: int | None = None) -> list[dict]:
    if not grid or not grid[0]:
        return []
    if background is None:
        background = most_common_colour(grid)
    rows, cols = shape(grid)
    seen: set[tuple[int, int]] = set()
    components = []
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
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = cr + dr, cc + dc
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and (nr, nc) not in seen
                        and grid[nr][nc] == colour
                    ):
                        seen.add((nr, nc))
                        queue.append((nr, nc))
            components.append({"colour": colour, "cells": cells, "size": len(cells)})
    components.sort(key=lambda item: (-item["size"], item["colour"], sorted(item["cells"])[0]))
    return components


def bbox(cells: set[tuple[int, int]]) -> tuple[int, int, int, int]:
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    return min(rows), max(rows), min(cols), max(cols)


def paint_cells(grid: Grid, cells: set[tuple[int, int]], colour: int, clear_first: bool = False) -> Grid:
    out = clone_grid(grid)
    if clear_first:
        bg = most_common_colour(grid)
        for r, row in enumerate(out):
            for c, _ in enumerate(row):
                if (r, c) in cells:
                    out[r][c] = bg
    for r, c in cells:
        out[r][c] = colour
    return out


def recolor(grid: Grid, source_colour: int, target_colour: int) -> Grid:
    return [[target_colour if cell == source_colour else cell for cell in row] for row in grid]


def delete_colour(grid: Grid, colour: int, background: int | None = None) -> Grid:
    bg = most_common_colour(grid) if background is None else background
    return [[bg if cell == colour else cell for cell in row] for row in grid]


def crop_to_content(grid: Grid) -> Grid:
    bg = most_common_colour(grid)
    cells = {(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell != bg}
    if not cells:
        return [[bg]]
    r0, r1, c0, c1 = bbox(cells)
    return [row[c0:c1 + 1] for row in grid[r0:r1 + 1]]


def mirror_colour(grid: Grid, colour: int, axis: str) -> Grid:
    out = clone_grid(grid)
    rows, cols = shape(grid)
    for r, c in [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == colour]:
        nr, nc = (rows - 1 - r, c) if axis == "horizontal" else (r, cols - 1 - c)
        out[nr][nc] = colour
    return out


def translate_colour_to_marker(
    grid: Grid,
    object_colour: int,
    marker_colour: int,
    keep_marker: bool,
) -> Grid:
    bg = most_common_colour(grid)
    object_cells = {(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == object_colour}
    marker_cells = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == marker_colour]
    if not object_cells or not marker_cells:
        return clone_grid(grid)
    min_r = min(r for r, _ in object_cells)
    min_c = min(c for _, c in object_cells)
    anchor_r, anchor_c = marker_cells[0]
    dr, dc = anchor_r - min_r, anchor_c - min_c
    out = [[bg if cell == object_colour or (cell == marker_colour and not keep_marker) else cell for cell in row] for row in grid]
    for r, c in object_cells:
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(out) and 0 <= nc < len(out[0]):
            out[nr][nc] = object_colour
    if keep_marker:
        for r, c in marker_cells:
            out[r][c] = marker_colour
    return out


def duplicate_to_markers(
    grid: Grid,
    object_colour: int,
    marker_colour: int,
    keep_markers: bool,
) -> Grid:
    bg = most_common_colour(grid)
    object_cells = {(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == object_colour}
    marker_cells = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == marker_colour]
    if not object_cells or not marker_cells:
        return clone_grid(grid)
    min_r = min(r for r, _ in object_cells)
    min_c = min(c for _, c in object_cells)
    out = [[bg if cell == marker_colour and not keep_markers else cell for cell in row] for row in grid]
    for anchor_r, anchor_c in marker_cells:
        dr, dc = anchor_r - min_r, anchor_c - min_c
        for r, c in object_cells:
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(out) and 0 <= nc < len(out[0]):
                out[nr][nc] = object_colour
    return out


def connect_markers(grid: Grid, marker_colour: int, line_colour: int, retain_markers: bool) -> Grid:
    bg = most_common_colour(grid)
    points = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == marker_colour]
    out = [[bg if cell == marker_colour and not retain_markers else cell for cell in row] for row in grid]
    if len(points) < 2:
        return out
    (r0, c0), (r1, c1) = points[:2]
    if r0 == r1:
        for c in range(min(c0, c1), max(c0, c1) + 1):
            out[r0][c] = line_colour
    elif c0 == c1:
        for r in range(min(r0, r1), max(r0, r1) + 1):
            out[r][c0] = line_colour
    else:
        step_r = 1 if r1 > r0 else -1
        step_c = 1 if c1 > c0 else -1
        r, c = r0, c0
        while True:
            out[r][c] = line_colour
            if (r, c) == (r1, c1):
                break
            if r != r1:
                r += step_r
            if c != c1:
                c += step_c
    if retain_markers:
        for r, c in points[:2]:
            out[r][c] = marker_colour
    return out


def delete_smallest_object(grid: Grid) -> Grid:
    bg = most_common_colour(grid)
    components = connected_components(grid, background=bg)
    if not components:
        return clone_grid(grid)
    target = sorted(components, key=lambda item: (item["size"], item["colour"], sorted(item["cells"])[0]))[0]
    out = clone_grid(grid)
    for r, c in target["cells"]:
        out[r][c] = bg
    return out


def fill_containers(grid: Grid, border_colour: int, fill_colour: int) -> Grid:
    out = clone_grid(grid)
    rows, cols = shape(grid)
    cells = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == border_colour]
    if not cells:
        return out
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if out[r][c] != border_colour:
                out[r][c] = fill_colour
    return out


def tile_by_markers(
    grid: Grid,
    motif_colour: int,
    marker_colour: int,
    axis: str,
    spacing: int,
) -> Grid:
    bg = most_common_colour(grid)
    motif_cells = {(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == motif_colour}
    markers = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == marker_colour]
    if not motif_cells or not markers:
        return clone_grid(grid)
    r0, r1, c0, c1 = bbox(motif_cells)
    motif = [row[c0:c1 + 1] for row in grid[r0:r1 + 1]]
    count = len(markers)
    mh, mw = len(motif), len(motif[0])
    rows, cols = shape(grid)
    if axis == "horizontal":
        out_width = count * mw + max(0, count - 1) * spacing
        out = blank(max(rows, mh), max(cols, out_width), bg)
        for idx in range(count):
            start_c = idx * (mw + spacing)
            for r in range(mh):
                for c in range(mw):
                    if motif[r][c] == motif_colour:
                        out[r][start_c + c] = motif_colour
    else:
        out_height = count * mh + max(0, count - 1) * spacing
        out = blank(max(rows, out_height), max(cols, mw), bg)
        for idx in range(count):
            start_r = idx * (mh + spacing)
            for r in range(mh):
                for c in range(mw):
                    if motif[r][c] == motif_colour:
                        out[start_r + r][c] = motif_colour
    return out


def apply_operation(grid: Grid, operation: Operation) -> Grid:
    params = operation.params
    if operation.kind == "recolor":
        return recolor(grid, params["source_colour"], params["target_colour"])
    if operation.kind == "translate_to_marker":
        return translate_colour_to_marker(
            grid,
            params["object_colour"],
            params["marker_colour"],
            params.get("keep_marker", False),
        )
    if operation.kind == "mirror":
        return mirror_colour(grid, params["colour"], params["axis"])
    if operation.kind == "crop_to_content":
        return crop_to_content(grid)
    if operation.kind == "duplicate_to_markers":
        return duplicate_to_markers(
            grid,
            params["object_colour"],
            params["marker_colour"],
            params.get("keep_markers", False),
        )
    if operation.kind == "connect_markers":
        return connect_markers(
            grid,
            params["marker_colour"],
            params["line_colour"],
            params.get("retain_markers", False),
        )
    if operation.kind == "fill_container":
        return fill_containers(grid, params["border_colour"], params["fill_colour"])
    if operation.kind == "delete_smallest_object":
        return delete_smallest_object(grid)
    if operation.kind == "tile_by_markers":
        return tile_by_markers(
            grid,
            params["motif_colour"],
            params["marker_colour"],
            params.get("axis", "horizontal"),
            params.get("spacing", 0),
        )
    if operation.kind == "delete_colour":
        return delete_colour(grid, params["colour"])
    raise ValueError(f"Unsupported operation kind: {operation.kind}")


def execute_program(program: Program, input_grid: Grid, with_trace: bool = False):
    current = clone_grid(input_grid)
    intermediates = [clone_grid(current)]
    trace_ops = []
    for op in program.operations:
        current = apply_operation(current, op)
        intermediates.append(clone_grid(current))
        trace_ops.append({"kind": op.kind, "params": dict(op.params)})
    if with_trace:
        return current, ExecutionTrace(
            family=program.family,
            program_id=program.program_id,
            operations=trace_ops,
            intermediate_grids=intermediates,
        )
    return current
