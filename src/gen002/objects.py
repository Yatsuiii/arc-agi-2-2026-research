"""Object extraction and per-object properties.

Objects are extracted by connected-component labelling (Rosenfeld & Pfaltz
1966) — a standard, decades-old computer-vision algorithm, implemented here
from the textbook description, not copied from any local reference
(`experiments/GEN002A/RELATED_SYSTEMS_AUDIT.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.gen002.grid import Grid, dims

Cell = tuple[int, int]

_NEIGHBOURS_4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
_NEIGHBOURS_8 = _NEIGHBOURS_4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _border_reachable(background: set[Cell], h: int, w: int) -> set[Cell]:
    """Background cells reachable from the bbox border without crossing
    object cells — the complement is what `holes` counts."""
    reachable: set[Cell] = {cell for cell in background if cell[0] in (0, h - 1) or cell[1] in (0, w - 1)}
    stack = list(reachable)
    while stack:
        r, c = stack.pop()
        for dr, dc in _NEIGHBOURS_4:
            nxt = (r + dr, c + dc)
            if nxt in background and nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    return reachable


def _count_components(cells: set[Cell]) -> int:
    """Number of 4-connected components in an arbitrary cell set."""
    remaining = set(cells)
    n_components = 0
    while remaining:
        seed = next(iter(remaining))
        component = {seed}
        frontier = [seed]
        while frontier:
            r, c = frontier.pop()
            for dr, dc in _NEIGHBOURS_4:
                nxt = (r + dr, c + dc)
                if nxt in remaining and nxt not in component:
                    component.add(nxt)
                    frontier.append(nxt)
        remaining -= component
        n_components += 1
    return n_components


@dataclass(frozen=True)
class Object:
    """One connected component. `cells` is keyed by absolute grid
    coordinates; `colours` is a sorted tuple of `(cell, colour)` pairs
    (not a `dict` — a dataclass field must be hashable for `Object` itself
    to be hashable, which the search engine's semantic-hash dedup
    requires, `search/cache.py`). `mask` is a background-normalised (0/1)
    view local to the bounding box, used for shape identity independent
    of position."""

    cells: frozenset[Cell]
    colours: tuple[tuple[Cell, int], ...]
    bbox: tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)

    @property
    def colours_dict(self) -> dict[Cell, int]:
        return dict(self.colours)

    @property
    def colour_set(self) -> frozenset[int]:
        return frozenset(colour for _, colour in self.colours)

    @property
    def area(self) -> int:
        return len(self.cells)

    @property
    def mask(self) -> tuple[tuple[int, ...], ...]:
        r0, c0, r1, c1 = self.bbox
        h, w = r1 - r0 + 1, c1 - c0 + 1
        grid = [[0] * w for _ in range(h)]
        for (r, c) in self.cells:
            grid[r - r0][c - c0] = 1
        return tuple(tuple(row) for row in grid)

    @property
    def perimeter(self) -> int:
        count = 0
        for (r, c) in self.cells:
            for dr, dc in _NEIGHBOURS_4:
                if (r + dr, c + dc) not in self.cells:
                    count += 1
        return count

    @property
    def centroid(self) -> tuple[float, float]:
        rs = [r for r, _ in self.cells]
        cs = [c for _, c in self.cells]
        return (sum(rs) / len(rs), sum(cs) / len(cs))

    @property
    def holes(self) -> int:
        """Count of background pockets fully enclosed by this object's
        bounding box that do not touch the bbox border (a simplified,
        bbox-local notion of "hole" — sufficient for typed grid transforms,
        not a full topological genus computation)."""
        r0, c0, r1, c1 = self.bbox
        h, w = r1 - r0 + 1, c1 - c0 + 1
        local = {(r - r0, c - c0) for (r, c) in self.cells}
        background = {(r, c) for r in range(h) for c in range(w)} - local
        if not background:
            return 0
        enclosed = background - _border_reachable(background, h, w)
        return _count_components(enclosed)

    @property
    def shape_id(self) -> tuple:
        """Translation-invariant identity: the normalised mask itself.
        Two objects with the same `shape_id` are the same shape, regardless
        of where they sit on the grid — used by `unique_by_shape`."""
        return self.mask

    def touches(self, other: "Object") -> bool:
        for (r, c) in self.cells:
            for dr, dc in _NEIGHBOURS_8:
                if (r + dr, c + dc) in other.cells:
                    return True
        return False

    def overlaps(self, other: "Object") -> bool:
        return bool(self.cells & other.cells)

    def contains_bbox(self, other: "Object") -> bool:
        r0, c0, r1, c1 = self.bbox
        or0, oc0, or1, oc1 = other.bbox
        return r0 <= or0 and c0 <= oc0 and r1 >= or1 and c1 >= oc1

    def distance_to(self, other: "Object") -> float:
        (sr, sc), (or_, oc) = self.centroid, other.centroid
        return ((sr - or_) ** 2 + (sc - oc) ** 2) ** 0.5


def _grow_component(
    grid: Grid, start: Cell, *, neighbours, background: int, multicolour: bool, visited: set[Cell]
) -> dict[Cell, int]:
    h, w = dims(grid)
    colour = grid[start[0]][start[1]]
    component: dict[Cell, int] = {}
    stack = [start]
    visited.add(start)
    while stack:
        cr, cc = stack.pop()
        component[(cr, cc)] = grid[cr][cc]
        for dr, dc in neighbours:
            nr, nc = cr + dr, cc + dc
            if not (0 <= nr < h and 0 <= nc < w):
                continue
            if (nr, nc) in visited or grid[nr][nc] == background:
                continue
            if not multicolour and grid[nr][nc] != colour:
                continue
            visited.add((nr, nc))
            stack.append((nr, nc))
    return component


def extract_objects(
    grid: Grid, *, connectivity: int = 4, background: int, multicolour: bool = False
) -> tuple[Object, ...]:
    """Connected-component labelling. `multicolour=False` (default) only
    merges same-coloured neighbours (colour-uniform objects, the common ARC
    convention); `multicolour=True` merges any non-background neighbours
    regardless of colour (useful for shape-only tasks with multi-coloured
    parts)."""
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")
    neighbours = _NEIGHBOURS_4 if connectivity == 4 else _NEIGHBOURS_8
    h, w = dims(grid)
    visited: set[Cell] = set()
    objects: list[Object] = []
    for r in range(h):
        for c in range(w):
            if (r, c) in visited or grid[r][c] == background:
                continue
            component = _grow_component(
                grid, (r, c), neighbours=neighbours, background=background,
                multicolour=multicolour, visited=visited,
            )
            cells = frozenset(component)
            rs = [cc[0] for cc in cells]
            cs = [cc[1] for cc in cells]
            objects.append(
                Object(
                    cells=cells,
                    colours=tuple(sorted(component.items())),
                    bbox=(min(rs), min(cs), max(rs), max(cs)),
                )
            )
    return tuple(objects)
