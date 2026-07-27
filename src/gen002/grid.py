"""Deterministic, ground-truth-free grid analysis.

`Grid` is a tuple of tuples of `int` (0-9) — immutable and hashable by
construction, which is what makes semantic hashing (`search/cache.py`)
free: two grids compare equal, and hash equal, exactly when their cells
are equal, with no custom `__eq__`/`__hash__` to maintain.

Every function here takes only grid cells. None reads a task ID or any
value not derivable from the grid itself.
"""

from __future__ import annotations

from collections import Counter

Grid = tuple[tuple[int, ...], ...]


def from_nested_list(rows: list[list[int]]) -> Grid:
    return tuple(tuple(int(cell) for cell in row) for row in rows)


def to_nested_list(grid: Grid) -> list[list[int]]:
    return [list(row) for row in grid]


def dims(grid: Grid) -> tuple[int, int]:
    if not grid:
        return (0, 0)
    return (len(grid), len(grid[0]))


def colour_histogram(grid: Grid) -> Counter:
    counts: Counter = Counter()
    for row in grid:
        counts.update(row)
    return counts


def background_candidates(grid: Grid) -> list[int]:
    """Colours ordered most-to-least likely to be background: most frequent
    first, with colour 0 preferred on a frequency tie (ARC's own
    convention, not this project's invention — 0 is universally "black" in
    every published ARC solver's rendering)."""
    counts = colour_histogram(grid)
    return sorted(counts, key=lambda colour: (-counts[colour], colour != 0, colour))


def columns(grid: Grid) -> Grid:
    return tuple(zip(*grid)) if grid else ()


def transpose(grid: Grid) -> Grid:
    return columns(grid)


def symmetry_axes(grid: Grid) -> dict[str, bool]:
    h, w = dims(grid)
    horizontal = grid == tuple(row[::-1] for row in grid)
    vertical = grid == grid[::-1]
    rotational_180 = grid == tuple(row[::-1] for row in grid[::-1])
    diagonal = h == w and grid == transpose(grid)
    anti_diagonal = h == w and grid == tuple(
        tuple(grid[w - 1 - c][h - 1 - r] for c in range(w)) for r in range(h)
    )
    return {
        "horizontal": horizontal,
        "vertical": vertical,
        "rotational_180": rotational_180,
        "diagonal": diagonal,
        "anti_diagonal": anti_diagonal,
    }


def _period(sequence: list[tuple]) -> int:
    n = len(sequence)
    for period in range(1, n + 1):
        if all(sequence[i] == sequence[i % period] for i in range(n)):
            return period
    return n


def periodicity(grid: Grid) -> tuple[int, int]:
    """(row_period, col_period): the smallest tile size whose repetition
    reproduces the grid exactly. Equals `dims(grid)` when the grid has no
    smaller periodic structure."""
    h, w = dims(grid)
    if h == 0 or w == 0:
        return (0, 0)
    row_period = _period(list(grid))
    col_period = _period(list(columns(grid)))
    return (row_period, col_period)


def bounding_region(grid: Grid, background: int) -> tuple[int, int, int, int] | None:
    """(min_row, min_col, max_row, max_col) inclusive of every non-background
    cell, or None if every cell is background."""
    coords = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell != background]
    if not coords:
        return None
    rs = [r for r, _ in coords]
    cs = [c for _, c in coords]
    return (min(rs), min(cs), max(rs), max(cs))
