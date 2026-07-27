"""The DSL's static type system. Runtime values are plain Python objects
(tuples, ints, dataclasses already defined in `src.gen002.objects`); `Type`
is a layer the search engine uses for type-directed expansion — it is
never checked by the Python interpreter itself, only by
`primitives.PRIMITIVES`' declared signatures.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from src.gen002.grid import Grid  # noqa: F401 - re-exported for callers of this module
from src.gen002.objects import Object

ObjectSet = tuple[Object, ...]
Mask = Grid
"""Same physical representation as `Grid` (0/1 cells) — a distinct DSL
`Type` tag, not a distinct Python class, since nothing about mask cell
values differs from grid cell values."""


class Coordinate(NamedTuple):
    row: int
    col: int


class Direction(NamedTuple):
    dr: int
    dc: int


DIRECTIONS: tuple[Direction, ...] = (
    Direction(-1, 0),
    Direction(1, 0),
    Direction(0, -1),
    Direction(0, 1),
    Direction(-1, -1),
    Direction(-1, 1),
    Direction(1, -1),
    Direction(1, 1),
)


class Type(Enum):
    GRID = "Grid"
    OBJECT = "Object"
    OBJECT_SET = "ObjectSet"
    MASK = "Mask"
    COLOUR = "Colour"
    COORDINATE = "Coordinate"
    DIRECTION = "Direction"
    INTEGER = "Integer"
    BOOLEAN = "Boolean"


class ProgramError(Exception):
    """Raised by a primitive on any input it cannot meaningfully act on
    (shape mismatch, empty object set, out-of-range parameter). Caught by
    the search loop; a program that raises this on any training input is
    dead (`search/pruning.py`'s dead-program elimination)."""
