"""Per-task structural statistics.

Every statistic here is a deterministic function of the grids, computable
without a model. Statistics that would need a learned notion of "object" or
"transformation family" are deliberately absent: they belong to the failure
taxonomy's human-review branch, not to a reproducible audit script.

Connectivity for object counting is fixed at 4-neighbour, same-colour, with
colour 0 treated as background. That convention is arbitrary but stated, so
counts are comparable across splits.
"""

from __future__ import annotations

from collections import Counter, deque

from .corpus import Corpus, Grid, Task

BACKGROUND = 0
_NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def shape(grid: Grid) -> tuple[int, int]:
    return len(grid), len(grid[0])


def colours(grid: Grid) -> set[int]:
    return {cell for row in grid for cell in row}


def count_objects(grid: Grid) -> int:
    """Connected components of equal non-background colour, 4-connectivity."""
    height, width = shape(grid)
    seen = [[False] * width for _ in range(height)]
    total = 0
    for row in range(height):
        for col in range(width):
            if seen[row][col] or grid[row][col] == BACKGROUND:
                continue
            total += 1
            colour = grid[row][col]
            queue = deque([(row, col)])
            seen[row][col] = True
            while queue:
                r, c = queue.popleft()
                for dr, dc in _NEIGHBOURS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < height and 0 <= nc < width:
                        if not seen[nr][nc] and grid[nr][nc] == colour:
                            seen[nr][nc] = True
                            queue.append((nr, nc))
    return total


def _size_relation(pairs) -> str:
    """How output size relates to input size across all demonstration pairs.

    Reported as one label per task because a task whose relation is inconsistent
    across pairs is qualitatively harder: the solver cannot infer output size
    from a single rule.
    """
    relations = set()
    for pair in pairs:
        if pair.output is None:
            continue
        in_shape, out_shape = shape(pair.input), shape(pair.output)
        if in_shape == out_shape:
            relations.add("same")
        elif out_shape[0] <= in_shape[0] and out_shape[1] <= in_shape[1]:
            relations.add("smaller")
        elif out_shape[0] >= in_shape[0] and out_shape[1] >= in_shape[1]:
            relations.add("larger")
        else:
            relations.add("mixed")
    if not relations:
        return "unknown"
    return relations.pop() if len(relations) == 1 else "inconsistent"


def describe(task: Task) -> dict:
    """Structural summary of one task. Keys are stable; treat as a schema."""
    known = [p for p in task.train + task.test if p.output is not None]
    inputs = [p.input for p in task.train + task.test]
    outputs = [p.output for p in known]

    in_shapes = [shape(g) for g in inputs]
    out_shapes = [shape(g) for g in outputs]
    in_colours = set().union(*(colours(g) for g in inputs)) if inputs else set()
    out_colours = set().union(*(colours(g) for g in outputs)) if outputs else set()

    return {
        "task_id": task.task_id,
        "n_train": len(task.train),
        "n_test": len(task.test),
        "n_test_with_output": sum(1 for p in task.test if p.output is not None),
        "input_height_max": max(h for h, _ in in_shapes),
        "input_width_max": max(w for _, w in in_shapes),
        "input_cells_max": max(h * w for h, w in in_shapes),
        "output_height_max": max((h for h, _ in out_shapes), default=0),
        "output_width_max": max((w for _, w in out_shapes), default=0),
        "output_cells_max": max((h * w for h, w in out_shapes), default=0),
        "n_input_colours": len(in_colours),
        "n_output_colours": len(out_colours),
        "introduces_colours": sorted(out_colours - in_colours) != [],
        "removes_colours": sorted(in_colours - out_colours) != [],
        "objects_input_mean": round(
            sum(count_objects(g) for g in inputs) / len(inputs), 3
        ),
        "objects_output_mean": (
            round(sum(count_objects(g) for g in outputs) / len(outputs), 3)
            if outputs
            else None
        ),
        "size_relation": _size_relation(task.train),
        "output_shape_varies": len({shape(p.output) for p in task.train}) > 1,
        "few_demonstrations": len(task.train) <= 2,
        "large_grid": max(max(h, w) for h, w in in_shapes + out_shapes) > 20,
    }


def summarise(corpus: Corpus) -> dict:
    """Aggregate a corpus into distribution summaries suitable for comparison."""
    rows = [describe(task) for task in corpus]

    def numeric(key):
        values = sorted(r[key] for r in rows if r[key] is not None)
        if not values:
            return {}
        return {
            "min": values[0],
            "median": values[len(values) // 2],
            "mean": round(sum(values) / len(values), 3),
            "max": values[-1],
        }

    colour_use = Counter()
    for task in corpus:
        for pair in task.train:
            colour_use.update(colours(pair.input))
            if pair.output is not None:
                colour_use.update(colours(pair.output))

    return {
        "name": corpus.name,
        "source": corpus.source,
        "n_tasks": len(corpus),
        "n_train_pairs_total": sum(r["n_train"] for r in rows),
        "n_test_pairs_total": sum(r["n_test"] for r in rows),
        "distributions": {
            key: numeric(key)
            for key in (
                "n_train",
                "n_test",
                "input_height_max",
                "input_width_max",
                "input_cells_max",
                "output_cells_max",
                "n_input_colours",
                "n_output_colours",
                "objects_input_mean",
                "objects_output_mean",
            )
        },
        "size_relation_counts": dict(Counter(r["size_relation"] for r in rows)),
        "flag_counts": {
            flag: sum(1 for r in rows if r[flag])
            for flag in (
                "introduces_colours",
                "removes_colours",
                "output_shape_varies",
                "few_demonstrations",
                "large_grid",
            )
        },
        "colour_frequency": {
            str(c): colour_use[c] for c in sorted(colour_use, key=lambda c: -colour_use[c])
        },
    }
