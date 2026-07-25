"""Structural-evidence features: does a candidate obey the demonstrations' pattern?

Generic ARC grid geometry only — no task IDs, no answers, nothing that would
not apply equally to a task nobody has ever seen. Every function takes plain
grids (`list[list[int]]`), not harness dataclasses, so they are testable and
reusable outside the harness.

**Scope, stated plainly.** The Phase-2 spec lists twenty-odd structural
properties (output dimensions, colours, object counts, connected components,
bounding boxes, relative positions, connectivity, topology, symmetry,
repetition, tiling, translation, rotation, reflection, scaling, cropping,
containment, adjacency, alignment, demonstration consistency). Several of
those are the same computation under different names — connectivity and
topology are both read off `connected_components`; translation, rotation and
reflection are read off `symmetry_signature`; cropping and scaling are read
off `size_relation` — so they are implemented once and reported together
rather than as twenty independent functions computing the same thing twice.
**Not implemented in this pass:** relative-position, containment and
adjacency scoring between specific objects. They need an object
*correspondence* step (which demo-output object came from which demo-input
object), which `paper/FAILURE_TAXONOMY.md`'s "Explicitly rejected categories"
already flags as not decidable from a transduction solver's output alone.
Recorded here as a scope limit, not silently dropped.
"""

from __future__ import annotations

from collections import Counter

Grid = list[list[int]]


def shape(grid: Grid) -> tuple[int, int]:
    if not grid or not grid[0]:
        return (0, 0)
    return (len(grid), len(grid[0]))


def colour_counts(grid: Grid) -> Counter:
    return Counter(cell for row in grid for cell in row)


def colour_set(grid: Grid) -> set[int]:
    return set(colour_counts(grid))


def connected_components(grid: Grid, background: int | None = None) -> list[dict]:
    """4-connected same-colour components, excluding the background colour.

    Background defaults to the grid's most common colour (the ARC convention
    when none is specified). Each component is
    `{"colour": int, "cells": {(r, c), ...}, "size": int}`.
    """
    if not grid or not grid[0]:
        return []
    if background is None:
        background = colour_counts(grid).most_common(1)[0][0]

    rows, cols = shape(grid)
    seen: set[tuple[int, int]] = set()
    components = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) in seen or grid[r][c] == background:
                continue
            colour = grid[r][c]
            stack = [(r, c)]
            cells: set[tuple[int, int]] = set()
            seen.add((r, c))
            while stack:
                cr, cc = stack.pop()
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
                        stack.append((nr, nc))
            components.append({"colour": colour, "cells": cells, "size": len(cells)})
    return components


def bounding_box(cells: set[tuple[int, int]]) -> tuple[int, int, int, int] | None:
    if not cells:
        return None
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    return (min(rows), max(rows), min(cols), max(cols))


def symmetry_signature(grid: Grid) -> dict[str, bool]:
    """Which symmetries this grid exhibits: horizontal/vertical/180-degree/diagonal.

    Diagonal symmetry (transpose invariance) is only defined for square grids.
    """
    rows, cols = shape(grid)
    horizontal = grid == [list(reversed(row)) for row in grid]
    vertical = grid == list(reversed(grid))
    rot180 = grid == [list(reversed(row)) for row in reversed(grid)]
    diagonal = rows == cols and grid == [
        [grid[c][r] for c in range(rows)] for r in range(cols)
    ]
    return {"h": horizontal, "v": vertical, "rot180": rot180, "diag": diagonal}


def is_periodic_tiling(grid: Grid) -> bool:
    """True if the grid is exactly tiled by a strictly smaller sub-block."""
    rows, cols = shape(grid)
    for period_r in range(1, rows + 1):
        if rows % period_r:
            continue
        for period_c in range(1, cols + 1):
            if cols % period_c:
                continue
            if period_r == rows and period_c == cols:
                continue
            if all(
                grid[r][c] == grid[r % period_r][c % period_c]
                for r in range(rows)
                for c in range(cols)
            ):
                return True
    return False


def size_relation(demo_pairs: list[tuple[Grid, Grid]]) -> str:
    """How output shape relates to input shape, across all demonstration pairs.

    One of "same" (output shape always equals input shape), "constant"
    (output shape is identical across demos regardless of input shape),
    "scaled" (output shape is a fixed integer multiple of input shape in both
    dimensions), or "inconsistent" (none of the above hold uniformly — the
    one machine-detectable symptom of task ambiguity per
    `docs/DATASET_AUDIT.md` §8).
    """
    if not demo_pairs:
        return "inconsistent"
    shapes = [(shape(i), shape(o)) for i, o in demo_pairs]
    if all(i == o for i, o in shapes):
        return "same"
    out_shapes = {o for _, o in shapes}
    if len(out_shapes) == 1:
        return "constant"
    ratios = set()
    for (ir, ic), (orr, oc) in shapes:
        if ir == 0 or ic == 0 or orr % ir or oc % ic:
            return "inconsistent"
        ratios.add((orr // ir, oc // ic))
    return "scaled" if len(ratios) == 1 else "inconsistent"


def expected_output_shape(
    test_input: Grid, demo_pairs: list[tuple[Grid, Grid]]
) -> tuple[int, int] | None:
    """Best-guess output shape for `test_input`, or `None` if not determinable."""
    relation = size_relation(demo_pairs)
    if relation == "same":
        return shape(test_input)
    if relation == "constant":
        return shape(demo_pairs[0][1])
    if relation == "scaled":
        ir, ic = shape(demo_pairs[0][0])
        orr, oc = shape(demo_pairs[0][1])
        ratio_r, ratio_c = orr // ir, oc // ic
        tr, tc = shape(test_input)
        return (tr * ratio_r, tc * ratio_c)
    return None


def demo_colour_pattern(demo_pairs: list[tuple[Grid, Grid]]) -> dict[str, set[int]]:
    """Colours ever introduced / removed / preserved from input to output, over all demos."""
    introduced: set[int] = set()
    removed: set[int] = set()
    preserved: set[int] = set()
    for input_grid, output_grid in demo_pairs:
        in_colours, out_colours = colour_set(input_grid), colour_set(output_grid)
        introduced |= out_colours - in_colours
        removed |= in_colours - out_colours
        preserved |= in_colours & out_colours
    return {"introduced": introduced, "removed": removed, "preserved": preserved}


MAX_DIMENSION = 30
VALID_COLOURS = set(range(10))


def is_valid_grid(grid: Grid) -> float:
    """1.0 if `grid` satisfies the ARC-AGI grid contract, else 0.0.

    Non-empty, rectangular, every cell a colour 0-9, no dimension over 30 —
    the same contract `src/run001/validate_outputs.py` checks a submission
    against, restated here as a candidate-level feature so a structurally
    invalid grid (which should never occur from a well-formed decoder, but is
    cheap to rule out) never silently scores as merely "inconsistent."
    """
    if not grid or not grid[0]:
        return 0.0
    widths = {len(row) for row in grid}
    if len(widths) != 1:
        return 0.0
    if len(grid) > MAX_DIMENSION or widths.pop() > MAX_DIMENSION:
        return 0.0
    return float(all(cell in VALID_COLOURS for row in grid for cell in row))


def grid_complexity(grid: Grid) -> float:
    """Coarse, model-independent complexity proxy: connected components per cell.

    Not a real minimum-description-length estimate (`docs/CANDIDATE_RESEARCH_THESES.md`
    §T2.3 names MDL-style scoring as CompressARC's actual objective, which
    needs an optimiser this project does not have); this is a cheap,
    deterministic stand-in in the same spirit — a grid built from few, large,
    simply-shaped regions scores low, a visually noisy or over-segmented one
    scores high.
    """
    rows, cols = shape(grid)
    area = rows * cols
    if area == 0:
        return 0.0
    return len(connected_components(grid)) / area


def structural_features(
    candidate: Grid, test_input: Grid, demo_pairs: list[tuple[Grid, Grid]]
) -> dict[str, float | None]:
    """The full structural feature vector for one candidate against its task."""
    relation = size_relation(demo_pairs)
    expected_shape = expected_output_shape(test_input, demo_pairs)
    cand_shape = shape(candidate)

    demo_pattern = demo_colour_pattern(demo_pairs)
    cand_in_colours, cand_out_colours = colour_set(test_input), colour_set(candidate)
    cand_introduced = cand_out_colours - cand_in_colours
    cand_removed = cand_in_colours - cand_out_colours

    demo_out_symmetries = [symmetry_signature(o) for _, o in demo_pairs]
    cand_symmetry = symmetry_signature(candidate)
    symmetry_agreement = None
    if demo_out_symmetries:
        keys = demo_out_symmetries[0].keys()
        matches = [
            1.0
            for key in keys
            if all(s[key] for s in demo_out_symmetries) == cand_symmetry[key]
        ]
        symmetry_agreement = sum(matches) / len(keys)

    demo_object_counts = [len(connected_components(o)) for _, o in demo_pairs]
    demo_input_object_counts = [len(connected_components(i)) for i, _ in demo_pairs]
    object_count_delta_pattern = [
        out_c - in_c for in_c, out_c in zip(demo_input_object_counts, demo_object_counts)
    ]
    cand_object_count = len(connected_components(candidate))
    test_input_object_count = len(connected_components(test_input))
    expected_object_count = None
    object_count_consistent = None
    if object_count_delta_pattern and len(set(object_count_delta_pattern)) == 1:
        expected_object_count = test_input_object_count + object_count_delta_pattern[0]
        object_count_consistent = float(cand_object_count == expected_object_count)

    demo_periodic = [is_periodic_tiling(o) for _, o in demo_pairs]
    tiling_pattern_consistent = None
    if demo_periodic:
        expected_periodic = all(demo_periodic)
        tiling_pattern_consistent = float(is_periodic_tiling(candidate) == expected_periodic)

    output_size_matches_expected = (
        float(cand_shape == expected_shape) if expected_shape is not None else None
    )
    introduced_colours_seen_in_demos = (
        float(cand_introduced <= demo_pattern["introduced"]) if cand_introduced else 1.0
    )
    removed_colours_seen_in_demos = (
        float(cand_removed <= demo_pattern["removed"]) if cand_removed else 1.0
    )

    # Every summand below is a 0/1 (or fractional, for symmetry) agreement
    # score; a contradiction is a check that resolved (not None) and scored
    # below 0.5. Counted, not just summed, so "3 checks fired and all
    # disagreed" reads differently from "1 check fired and disagreed."
    consistency_checks = (
        output_size_matches_expected,
        introduced_colours_seen_in_demos,
        removed_colours_seen_in_demos,
        symmetry_agreement,
        object_count_consistent,
        tiling_pattern_consistent,
    )
    contradiction_count = sum(1.0 for v in consistency_checks if v is not None and v < 0.5)

    return {
        "output_size_matches_expected": output_size_matches_expected,
        "size_relation_category": relation,  # categorical; verifiers may one-hot it
        "n_colours_introduced_by_candidate": float(len(cand_introduced)),
        "n_colours_removed_by_candidate": float(len(cand_removed)),
        "introduced_colours_seen_in_demos": introduced_colours_seen_in_demos,
        "removed_colours_seen_in_demos": removed_colours_seen_in_demos,
        "symmetry_agreement_with_demo_outputs": symmetry_agreement,
        "object_count": float(cand_object_count),
        "object_count_consistent_with_demo_pattern": object_count_consistent,
        "tiling_pattern_consistent_with_demos": tiling_pattern_consistent,
        "is_degenerate_input_copy": float(candidate == test_input),
        "is_degenerate_constant_fill": float(len(cand_out_colours) <= 1),
        "is_valid_grid": is_valid_grid(candidate),
        "grid_complexity": grid_complexity(candidate),
        "contradiction_count": contradiction_count,
    }
