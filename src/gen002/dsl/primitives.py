"""The DSL's primitive library: typed, deterministic, costed, unit-tested.

Every primitive raises `ProgramError` on inputs it cannot act on — never an
uncaught exception, and never anything but `ProgramError` (the search loop
catches exactly this one exception type; anything else is a bug, not a
dead-program signal).

Scope, and every deviation from `experiments/GEN002A/DSL_SPEC.md`, is
recorded in `experiments/GEN002A/PRIMITIVE_CATALOG.md`, generated from
this module's own `PRIMITIVES` registry so the two can never drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.gen002 import grid as gridmod
from src.gen002 import objects as objectsmod
from src.gen002 import scene_graph
from src.gen002.dsl.types import Coordinate, Direction, Grid, ObjectSet, ProgramError, Type


@dataclass(frozen=True)
class Primitive:
    name: str
    params: tuple[Type, ...]
    returns: Type
    cost: int
    func: object  # Callable[..., Any]; kept untyped to avoid a generic-callable annotation tax


PRIMITIVES: dict[str, Primitive] = {}


def _register(name: str, params: tuple[Type, ...], returns: Type, cost: int = 1):
    def wrap(func):
        PRIMITIVES[name] = Primitive(name=name, params=params, returns=returns, cost=cost, func=func)
        return func

    return wrap


def _background(grid: Grid) -> int:
    return gridmod.background_candidates(grid)[0]


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


@_register("objects4", (Type.GRID,), Type.OBJECT_SET)
def objects4(grid: Grid) -> ObjectSet:
    return objectsmod.extract_objects(grid, background=_background(grid), connectivity=4)


@_register("objects8", (Type.GRID,), Type.OBJECT_SET)
def objects8(grid: Grid) -> ObjectSet:
    return objectsmod.extract_objects(grid, background=_background(grid), connectivity=8)


@_register("largest", (Type.OBJECT_SET,), Type.OBJECT_SET)
def largest(objs: ObjectSet) -> ObjectSet:
    if not objs:
        raise ProgramError("largest: empty object set")
    max_area = max(o.area for o in objs)
    return tuple(o for o in objs if o.area == max_area)


@_register("smallest", (Type.OBJECT_SET,), Type.OBJECT_SET)
def smallest(objs: ObjectSet) -> ObjectSet:
    if not objs:
        raise ProgramError("smallest: empty object set")
    min_area = min(o.area for o in objs)
    return tuple(o for o in objs if o.area == min_area)


@_register("unique_by_shape", (Type.OBJECT_SET,), Type.OBJECT_SET)
def unique_by_shape(objs: ObjectSet) -> ObjectSet:
    seen: dict = {}
    for o in scene_graph.sort_by_position(objs):
        seen.setdefault(o.shape_id, o)
    return tuple(seen.values())


@_register("by_colour", (Type.OBJECT_SET, Type.COLOUR), Type.OBJECT_SET)
def by_colour(objs: ObjectSet, colour: int) -> ObjectSet:
    return tuple(o for o in objs if colour in o.colour_set)


@_register("by_size", (Type.OBJECT_SET, Type.INTEGER), Type.OBJECT_SET)
def by_size(objs: ObjectSet, n: int) -> ObjectSet:
    return tuple(o for o in objs if o.area == n)


@_register("min_size", (Type.OBJECT_SET, Type.INTEGER), Type.OBJECT_SET)
def min_size(objs: ObjectSet, n: int) -> ObjectSet:
    return tuple(o for o in objs if o.area >= n)


@_register("touching", (Type.OBJECT_SET, Type.OBJECT_SET), Type.OBJECT_SET)
def touching(objs: ObjectSet, reference: ObjectSet) -> ObjectSet:
    return tuple(o for o in objs if any(o.touches(r) for r in reference if r is not o))


@_register("nearest", (Type.OBJECT_SET, Type.OBJECT_SET), Type.OBJECT_SET)
def nearest(objs: ObjectSet, reference: ObjectSet) -> ObjectSet:
    if not objs or not reference:
        raise ProgramError("nearest: empty operand")
    scored = sorted(
        objs, key=lambda o: (min(o.distance_to(r) for r in reference), o.bbox[0], o.bbox[1])
    )
    return (scored[0],)


@_register("sort_by_size", (Type.OBJECT_SET,), Type.OBJECT_SET)
def sort_by_size_prim(objs: ObjectSet) -> ObjectSet:
    return scene_graph.sort_by_size(objs)


@_register("sort_by_position", (Type.OBJECT_SET,), Type.OBJECT_SET)
def sort_by_position_prim(objs: ObjectSet) -> ObjectSet:
    return scene_graph.sort_by_position(objs)


@_register("sort_by_colour", (Type.OBJECT_SET,), Type.OBJECT_SET)
def sort_by_colour_prim(objs: ObjectSet) -> ObjectSet:
    return scene_graph.sort_by_colour(objs)


# ---------------------------------------------------------------------------
# Geometric transformation
# ---------------------------------------------------------------------------


@_register("rotate_90", (Type.GRID,), Type.GRID)
def rotate_90(grid: Grid) -> Grid:
    return tuple(zip(*grid[::-1]))


@_register("rotate_180", (Type.GRID,), Type.GRID)
def rotate_180(grid: Grid) -> Grid:
    return tuple(row[::-1] for row in grid[::-1])


@_register("rotate_270", (Type.GRID,), Type.GRID)
def rotate_270(grid: Grid) -> Grid:
    return tuple(zip(*grid))[::-1]


@_register("reflect_horizontal", (Type.GRID,), Type.GRID)
def reflect_horizontal(grid: Grid) -> Grid:
    return tuple(row[::-1] for row in grid)


@_register("reflect_vertical", (Type.GRID,), Type.GRID)
def reflect_vertical(grid: Grid) -> Grid:
    return grid[::-1]


@_register("reflect_diagonal", (Type.GRID,), Type.GRID)
def reflect_diagonal(grid: Grid) -> Grid:
    return gridmod.transpose(grid)


@_register("crop", (Type.GRID,), Type.GRID)
def crop(grid: Grid) -> Grid:
    bg = _background(grid)
    region = gridmod.bounding_region(grid, background=bg)
    if region is None:
        raise ProgramError("crop: grid is entirely background")
    r0, c0, r1, c1 = region
    return tuple(row[c0 : c1 + 1] for row in grid[r0 : r1 + 1])


@_register("pad", (Type.GRID, Type.INTEGER, Type.COLOUR), Type.GRID)
def pad(grid: Grid, amount: int, fill: int) -> Grid:
    if amount < 0:
        raise ProgramError("pad: negative amount")
    h, w = gridmod.dims(grid)
    new_w = w + 2 * amount
    border = (fill,) * new_w
    middle = tuple((fill,) * amount + row + (fill,) * amount for row in grid)
    return (border,) * amount + middle + (border,) * amount


@_register("scale", (Type.GRID, Type.INTEGER), Type.GRID)
def scale(grid: Grid, factor: int) -> Grid:
    if factor < 1 or factor > 10:
        raise ProgramError("scale: factor out of range")
    return tuple(
        tuple(cell for cell in row for _ in range(factor)) for row in grid for _ in range(factor)
    )


@_register("tile", (Type.GRID, Type.INTEGER, Type.INTEGER), Type.GRID)
def tile(grid: Grid, n_rows: int, n_cols: int) -> Grid:
    if not (1 <= n_rows <= 10 and 1 <= n_cols <= 10):
        raise ProgramError("tile: repeat count out of range")
    tiled_rows = tuple(row * n_cols for row in grid)
    return tiled_rows * n_rows


@_register("translate", (Type.GRID, Type.DIRECTION, Type.INTEGER), Type.GRID)
def translate(grid: Grid, direction: Direction, distance: int) -> Grid:
    bg = _background(grid)
    h, w = gridmod.dims(grid)
    dr, dc = direction.dr * distance, direction.dc * distance
    out = [[bg] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = grid[r][c]
    return tuple(tuple(row) for row in out)


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------


@_register("recolour", (Type.GRID, Type.COLOUR, Type.COLOUR), Type.GRID)
def recolour(grid: Grid, old: int, new: int) -> Grid:
    return tuple(tuple(new if cell == old else cell for cell in row) for row in grid)


@_register("swap_colours", (Type.GRID, Type.COLOUR, Type.COLOUR), Type.GRID)
def swap_colours(grid: Grid, a: int, b: int) -> Grid:
    mapping = {a: b, b: a}
    return tuple(tuple(mapping.get(cell, cell) for cell in row) for row in grid)


@_register("map_colours_by_frequency", (Type.GRID,), Type.GRID)
def map_colours_by_frequency(grid: Grid) -> Grid:
    """Canonicalises colours to their descending-frequency rank (most
    frequent -> 0, next -> 1, ...). A genuinely useful unary
    canonicalisation, used in place of the acceptance message's
    `map_colours` (which would need a `Mapping` value type this DSL does
    not have — see `PRIMITIVE_CATALOG.md`'s deviation note)."""
    counts = gridmod.colour_histogram(grid)
    ranked = sorted(counts, key=lambda c: (-counts[c], c))
    mapping = {colour: rank for rank, colour in enumerate(ranked)}
    return tuple(tuple(mapping[cell] for cell in row) for row in grid)


@_register("background_replace", (Type.GRID, Type.COLOUR), Type.GRID)
def background_replace(grid: Grid, new_background: int) -> Grid:
    bg = _background(grid)
    return recolour(grid, bg, new_background)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@_register("blank_grid", (Type.INTEGER, Type.INTEGER, Type.COLOUR), Type.GRID)
def blank_grid(h: int, w: int, fill: int) -> Grid:
    if not (1 <= h <= 30 and 1 <= w <= 30):
        raise ProgramError("blank_grid: dimensions out of range")
    return tuple((fill,) * w for _ in range(h))


def _paint_cells(grid: Grid, cells, colour: int) -> Grid:
    h, w = gridmod.dims(grid)
    out = [list(row) for row in grid]
    for (r, c) in cells:
        if 0 <= r < h and 0 <= c < w:
            out[r][c] = colour
    return tuple(tuple(row) for row in out)


@_register("paint", (Type.GRID, Type.OBJECT_SET, Type.COLOUR), Type.GRID)
def paint(grid: Grid, objs: ObjectSet, colour: int) -> Grid:
    cells = [cell for o in objs for cell in o.cells]
    return _paint_cells(grid, cells, colour)


@_register("overlay", (Type.GRID, Type.GRID), Type.GRID)
def overlay(base: Grid, top: Grid) -> Grid:
    if gridmod.dims(base) != gridmod.dims(top):
        raise ProgramError("overlay: dimension mismatch")
    top_bg = _background(top)
    out = [list(row) for row in base]
    for r, row in enumerate(top):
        for c, cell in enumerate(row):
            if cell != top_bg:
                out[r][c] = cell
    return tuple(tuple(row) for row in out)


@_register("copy_object", (Type.GRID, Type.OBJECT_SET, Type.DIRECTION, Type.INTEGER), Type.GRID)
def copy_object(grid: Grid, objs: ObjectSet, direction: Direction, distance: int) -> Grid:
    cells = [
        (r + direction.dr * distance, c + direction.dc * distance, colour)
        for o in objs
        for (r, c), colour in o.colours
    ]
    h, w = gridmod.dims(grid)
    out = [list(row) for row in grid]
    for r, c, colour in cells:
        if 0 <= r < h and 0 <= c < w:
            out[r][c] = colour
    return tuple(tuple(row) for row in out)


@_register("delete_object", (Type.GRID, Type.OBJECT_SET), Type.GRID)
def delete_object(grid: Grid, objs: ObjectSet) -> Grid:
    bg = _background(grid)
    cells = [cell for o in objs for cell in o.cells]
    return _paint_cells(grid, cells, bg)


@_register("bounding_box", (Type.GRID, Type.OBJECT_SET), Type.GRID)
def bounding_box(grid: Grid, objs: ObjectSet) -> Grid:
    if not objs:
        raise ProgramError("bounding_box: empty object set")
    r0 = min(o.bbox[0] for o in objs)
    c0 = min(o.bbox[1] for o in objs)
    r1 = max(o.bbox[2] for o in objs)
    c1 = max(o.bbox[3] for o in objs)
    return tuple(row[c0 : c1 + 1] for row in grid[r0 : r1 + 1])


@_register("fill_bbox", (Type.GRID, Type.OBJECT_SET, Type.COLOUR), Type.GRID)
def fill_bbox(grid: Grid, objs: ObjectSet, colour: int) -> Grid:
    if not objs:
        raise ProgramError("fill_bbox: empty object set")
    r0 = min(o.bbox[0] for o in objs)
    c0 = min(o.bbox[1] for o in objs)
    r1 = max(o.bbox[2] for o in objs)
    c1 = max(o.bbox[3] for o in objs)
    cells = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
    return _paint_cells(grid, cells, colour)


@_register("outline", (Type.GRID, Type.OBJECT_SET, Type.COLOUR), Type.GRID)
def outline(grid: Grid, objs: ObjectSet, colour: int) -> Grid:
    cells = []
    for o in objs:
        for (r, c) in o.cells:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if (r + dr, c + dc) not in o.cells:
                    cells.append((r, c))
                    break
    return _paint_cells(grid, cells, colour)


@_register("fill_holes", (Type.GRID, Type.OBJECT_SET, Type.COLOUR), Type.GRID)
def fill_holes(grid: Grid, objs: ObjectSet, colour: int) -> Grid:
    cells = []
    for o in objs:
        if o.holes == 0:
            continue
        r0, c0, r1, c1 = o.bbox
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r, c) not in o.cells:
                    cells.append((r, c))
    return _paint_cells(grid, cells, colour)


@_register("draw_line", (Type.GRID, Type.COORDINATE, Type.DIRECTION, Type.INTEGER, Type.COLOUR), Type.GRID)
def draw_line(grid: Grid, start: Coordinate, direction: Direction, length: int, colour: int) -> Grid:
    if length < 1:
        raise ProgramError("draw_line: non-positive length")
    cells = [(start.row + direction.dr * i, start.col + direction.dc * i) for i in range(length)]
    return _paint_cells(grid, cells, colour)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


@_register("symmetric_horizontal", (Type.GRID,), Type.BOOLEAN)
def symmetric_horizontal(grid: Grid) -> bool:
    return gridmod.symmetry_axes(grid)["horizontal"]


@_register("symmetric_vertical", (Type.GRID,), Type.BOOLEAN)
def symmetric_vertical(grid: Grid) -> bool:
    return gridmod.symmetry_axes(grid)["vertical"]


@_register("equal_grids", (Type.GRID, Type.GRID), Type.BOOLEAN)
def equal_grids(a: Grid, b: Grid) -> bool:
    return a == b


@_register("conditional", (Type.BOOLEAN, Type.GRID, Type.GRID), Type.GRID)
def conditional(cond: bool, if_true: Grid, if_false: Grid) -> Grid:
    return if_true if cond else if_false
