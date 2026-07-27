# GEN002-A — DSL_SPEC

Frozen before implementation. A minimal typed DSL, not an attempt at the
acceptance message's full primitive list — every family is represented by
a deliberately chosen, general-purpose subset, with every omission stated
here rather than discovered later. Primitives are chosen for general
applicability to ARC-style grid transformations, not fitted to the 24-index
pilot (which has not been run yet when this scope is frozen).

## Types

`Grid`, `Object`, `ObjectSet`, `Mask`, `Colour` (int 0-9), `Coordinate`
(row, col), `Direction` (one of 8 unit vectors), `Integer`, `Boolean`.
`Grid` is an immutable tuple-of-tuples of `Colour` — hashable by
construction, which is what makes semantic hashing (Phase 4) free.

## Selection (8 of the acceptance message's ~13, chosen for orthogonality)

`objects(grid, connectivity)`, `largest(objects)`, `smallest(objects)`,
`unique_by_shape(objects)`, `by_colour(objects, colour)`,
`by_size(objects, n, comparator)`, `touching(objects, target)`,
`nearest(objects, target)`.

**Omitted**: `components` (subsumed by `objects` with a connectivity
parameter), `by_shape` (subsumed by `unique_by_shape` plus `filter_objects`
composition), `contained`/`aligned` (relational properties exposed on
`Object` itself via `scene_graph.py`, reachable through `filter_objects`
rather than a dedicated selector — avoids two ways to express the same
query), `farthest` (a `nearest` with reversed comparator is one
`sort_objects` + index away, not worth a second primitive at this DSL
size).

## Geometric transformation (10)

`translate`, `rotate_90`, `rotate_180`, `rotate_270`,
`reflect_horizontal`, `reflect_vertical`, `reflect_diagonal`, `crop`,
`pad`, `scale`, `tile`.

**Omitted**: `repeat` — `tile` already covers periodic repetition; a
distinct `repeat` primitive would be a pass-through synonym (an APoSD red
flag this project's own coding discipline explicitly names), not a new
capability.

## Colour (4)

`recolour`, `swap_colours`, `map_colours`, `background_replace`.

**Omitted**: `preserve_colour` — the identity colour operation is what
"not calling `recolour`" already means; a no-op primitive adds search
branching factor without adding expressivity.

## Construction (10)

`blank_grid`, `paint`, `overlay`, `copy_object`, `delete_object`,
`bounding_box`, `fill_bbox`, `outline`, `fill_holes`, `draw_line`.

**Omitted**: `connect_objects` and `extend_ray` — both are real, useful
primitives for line-drawing ARC tasks, deferred because they need a
disambiguation policy (which two objects, which direction) that would
either need a hidden heuristic or a combinatorial parameter search this
DSL's search budget cannot absorb at this scope. Flagged here as a named
gap for `ERROR_ANALYSIS.md`'s missing-language category to point at if a
pilot failure needs exactly this capability.

## Composition (5)

`map_over_objects`, `filter_objects`, `sort_objects`, `compose`,
`conditional`.

**Omitted**: `repeat_until_stable` — a genuine fixed-point combinator is
useful but its termination is data-dependent even under a bound, which
interacts badly with this phase's strict per-task timeout and state
budget (Phase 4's actual binding constraint, per `PLAN.md`'s timeout
deviation). Deferred as a documented gap, not implemented with a silent
bound that would make its behaviour partially undocumented.

## Total primitive count

37 primitives across 5 families plus 9 types. Every primitive: typed
signature, deterministic semantics, a fixed cost (used for MDL ranking,
Phase 4), canonical serialization (its AST node repr), unit tests, defined
failure behaviour (raises a typed `ProgramError`, caught by the search
loop, never propagates as an uncaught exception), and no access to
anything but the `Grid`/`Object`/etc. values passed to it — no primitive
reads a task ID, a ground-truth grid, or any global state.

Full table with signatures and costs: `PRIMITIVE_CATALOG.md`, written
after implementation (Phase 3), reflecting exactly what `src/gen002/dsl/primitives.py`
contains — not a second, potentially drifting source of truth.
