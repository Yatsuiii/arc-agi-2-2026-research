"""Duplicate and near-duplicate detection between and within splits.

Three progressively weaker notions of identity, reported separately because they
carry different leakage risk:

exact task
    Same demonstration pairs. A held-out task that is an exact duplicate of a
    training task is fully leaked.

exact pair
    An individual input/output pair appearing in two splits. Partial leakage:
    the transformation is demonstrated to the model even though the task id
    differs.

canonical task
    Same demonstration pairs up to the D4 dihedral group and colour
    relabelling, which is exactly the augmentation group every reference solver
    trains on. Two tasks identical under it are indistinguishable to those
    solvers, so this is the leakage notion that actually matters for them.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from .corpus import Corpus, Grid, Pair


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def _transpose(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid)]


def _rot90(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid)][::-1]


def _d4(grid: Grid):
    """The eight dihedral views of a grid."""
    current = grid
    for _ in range(4):
        yield current
        yield _transpose(current)
        current = _rot90(current)


def _relabel(grid: Grid) -> Grid:
    """Recolour by first appearance, so colour identity stops mattering."""
    mapping: dict[int, int] = {}
    for row in grid:
        for cell in row:
            mapping.setdefault(cell, len(mapping))
    return [[mapping[cell] for cell in row] for row in grid]


def _canonical_pairs(pairs: list[Pair]) -> str:
    """Smallest digest over the D4 orbit, with colours relabelled consistently.

    The same transform is applied to every pair of the task, because a solver
    sees the pairs together; independently canonicalising them would collapse
    tasks that are genuinely different.
    """
    candidates = []
    for index in range(8):
        views = []
        for pair in pairs:
            if pair.output is None:
                continue
            transformed_in = list(_d4(pair.input))[index]
            transformed_out = list(_d4(pair.output))[index]
            # Relabel input and output under one shared palette mapping.
            merged = _relabel(transformed_in + [[]] + transformed_out)
            split = merged.index([])
            views.append((merged[:split], merged[split + 1 :]))
        candidates.append(_digest(sorted(map(list, views))))
    return min(candidates)


def _pair_key(pair: Pair) -> str:
    return _digest([pair.input, pair.output])


def report(corpora: list[Corpus]) -> dict:
    """Duplicate report across the given corpora, plus within each of them."""
    exact_task: dict[str, list[str]] = defaultdict(list)
    canonical_task: dict[str, list[str]] = defaultdict(list)
    pair_owner: dict[str, list[str]] = defaultdict(list)

    for corpus in corpora:
        for task in corpus:
            label = f"{corpus.name}:{task.task_id}"
            exact_task[_digest([[p.input, p.output] for p in task.train])].append(label)
            canonical_task[_canonical_pairs(task.train)].append(label)
            for pair in task.train:
                pair_owner[_pair_key(pair)].append(label)

    def collisions(index, cross_split_only):
        found = []
        for key, labels in index.items():
            if len(labels) < 2:
                continue
            splits = {label.split(":")[0] for label in labels}
            if cross_split_only and len(splits) < 2:
                continue
            found.append({"key": key, "members": sorted(labels)})
        return sorted(found, key=lambda entry: entry["key"])

    return {
        "corpora": [{"name": c.name, "n_tasks": len(c), "source": c.source} for c in corpora],
        "exact_duplicate_tasks": collisions(exact_task, cross_split_only=False),
        "canonical_duplicate_tasks": collisions(canonical_task, cross_split_only=False),
        "shared_demonstration_pairs_across_splits": collisions(
            pair_owner, cross_split_only=True
        ),
        "notes": {
            "canonical_group": "D4 (transpose x rot90) with colour relabelling by first appearance",
            "why": "matches the augmentation group used by every reference solver",
        },
    }
