"""Relations between a grid's objects: a scene graph.

Nodes are `Object`s (already extracted, `objects.py`); edges are relational
facts computed from geometry alone — nothing here reads a task ID or a
ground-truth grid.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.gen002.objects import Object


@dataclass(frozen=True)
class Edge:
    i: int
    j: int
    relation: str


@dataclass(frozen=True)
class SceneGraph:
    objects: tuple[Object, ...]
    edges: tuple[Edge, ...]

    def relations_of(self, index: int) -> tuple[Edge, ...]:
        return tuple(e for e in self.edges if e.i == index or e.j == index)


def _aligned(a: Object, b: Object) -> bool:
    ar0, ac0, ar1, ac1 = a.bbox
    br0, bc0, br1, bc1 = b.bbox
    row_overlap = not (ar1 < br0 or br1 < ar0)
    col_overlap = not (ac1 < bc0 or bc1 < ac0)
    return row_overlap or col_overlap


def build_scene_graph(objects: tuple[Object, ...]) -> SceneGraph:
    edges: list[Edge] = []
    for i, a in enumerate(objects):
        for j, b in enumerate(objects):
            if i >= j:
                continue
            if a.overlaps(b):
                edges.append(Edge(i, j, "overlap"))
            if a.touches(b):
                edges.append(Edge(i, j, "adjacent"))
            if a.contains_bbox(b) and not a.overlaps(b):
                edges.append(Edge(i, j, "contains"))
            elif b.contains_bbox(a) and not a.overlaps(b):
                edges.append(Edge(j, i, "contains"))
            if _aligned(a, b):
                edges.append(Edge(i, j, "aligned"))
            if a.shape_id == b.shape_id:
                edges.append(Edge(i, j, "equal_shape"))
    return SceneGraph(objects=objects, edges=tuple(edges))


def sort_by_size(objects: tuple[Object, ...], *, descending: bool = True) -> tuple[Object, ...]:
    return tuple(sorted(objects, key=lambda o: o.area, reverse=descending))


def sort_by_position(objects: tuple[Object, ...]) -> tuple[Object, ...]:
    """Reading order: top-to-bottom, then left-to-right, by bbox origin."""
    return tuple(sorted(objects, key=lambda o: (o.bbox[0], o.bbox[1])))


def sort_by_colour(objects: tuple[Object, ...]) -> tuple[Object, ...]:
    return tuple(sorted(objects, key=lambda o: sorted(o.colour_set)))
