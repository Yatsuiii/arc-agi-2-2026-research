from __future__ import annotations

import hashlib
import json
from typing import Iterable

from .task_schema import Grid, SyntheticTask

GENERATOR_VERSION = "data001a.v1"


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_appearance_colour_normalize(grid: Grid) -> Grid:
    mapping: dict[int, int] = {}
    next_colour = 0
    result = []
    for row in grid:
        norm_row = []
        for cell in row:
            if cell not in mapping:
                mapping[cell] = next_colour
                next_colour += 1
            norm_row.append(mapping[cell])
        result.append(norm_row)
    return result


def rotate_grid(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid[::-1])]


def reflect_grid(grid: Grid) -> Grid:
    return [list(reversed(row)) for row in grid]


def dihedral_variants(grid: Grid) -> list[Grid]:
    variants = []
    cur = grid
    for _ in range(4):
        variants.append(cur)
        variants.append(reflect_grid(cur))
        cur = rotate_grid(cur)
    unique = []
    seen = set()
    for variant in variants:
        key = canonical_json(variant)
        if key not in seen:
            seen.add(key)
            unique.append(variant)
    return unique


def normalized_grid_hash(grid: Grid) -> str:
    normalized = first_appearance_colour_normalize(grid)
    return sha256_text(canonical_json(normalized))


def d4_normalized_grid_hash(grid: Grid) -> str:
    variants = [first_appearance_colour_normalize(v) for v in dihedral_variants(grid)]
    return min(sha256_text(canonical_json(v)) for v in variants)


def grid_hash(grid: Grid) -> str:
    return sha256_text(canonical_json(grid))


def pair_hash(pair: dict) -> str:
    return sha256_text(canonical_json(pair))


def task_hash(task: SyntheticTask) -> str:
    return sha256_text(canonical_json(task.to_dict()))


def stable_seed(*parts: Iterable[object]) -> int:
    text = "::".join(str(part) for part in parts)
    return int(sha256_text(text)[:16], 16)

