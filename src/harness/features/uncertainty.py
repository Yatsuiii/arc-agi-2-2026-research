"""Uncertainty-evidence features: how much the candidate set itself disagrees.

Unlike `generation.py` and `structural.py`, these are computed once per
`CandidateSet` (one test index), not once per candidate — "is this test index
easy or hard" is a property of the whole set. `None` again means "not
computable from this archive," most often because RUN-001 ran one seed and
one solver branch (`experiments/RUN001/BASELINE_SPEC.md` "Seeds") — seed- and
solver-disagreement have nothing to disagree across.
"""

from __future__ import annotations

import math
import statistics

from src.harness.schemas import BudgetSnapshot, CandidateSet

NEAR_TIE_EPSILON = 1e-6


def _grid_scores(candidate_set: CandidateSet) -> dict[str, float]:
    """Best beam_score per unique grid, the score this module reasons about."""
    best: dict[str, float] = {}
    for candidate in candidate_set.candidates:
        if candidate.beam_score is None:
            continue
        current = best.get(candidate.grid_sha1)
        if current is None or candidate.beam_score > current:
            best[candidate.grid_sha1] = candidate.beam_score
    return best


def score_distribution_entropy(candidate_set: CandidateSet) -> float | None:
    """Shannon entropy, in nats, of the softmax over unique-grid best scores.

    High entropy means the set's own scores do not concentrate on one grid —
    the solver itself is unsure. `None` when fewer than 2 unique grids scored,
    since entropy over a single outcome is degenerate (always 0, not
    informative).
    """
    scores = list(_grid_scores(candidate_set).values())
    if len(scores) < 2:
        return None
    top = max(scores)
    weights = [math.exp(s - top) for s in scores]
    total = sum(weights)
    probabilities = [w / total for w in weights]
    return -sum(p * math.log(p) for p in probabilities if p > 0)


def effective_candidate_count(candidate_set: CandidateSet) -> float | None:
    """exp(entropy): the "effective" number of competitive candidates.

    1.0 means the score distribution is fully concentrated on one grid; a
    value near the unique-grid count means the scores do not discriminate at
    all between them.
    """
    entropy = score_distribution_entropy(candidate_set)
    return math.exp(entropy) if entropy is not None else None


def top_margin(candidate_set: CandidateSet) -> float | None:
    """Best score minus second-best score across unique grids."""
    scores = sorted(_grid_scores(candidate_set).values(), reverse=True)
    if len(scores) < 2:
        return None
    return scores[0] - scores[1]


def near_tie_count(candidate_set: CandidateSet, epsilon: float = NEAR_TIE_EPSILON) -> float | None:
    """How many unique grids are within `epsilon` of the top score."""
    scores = list(_grid_scores(candidate_set).values())
    if not scores:
        return None
    top = max(scores)
    return float(sum(1 for s in scores if top - s <= epsilon))


def augmentation_disagreement(candidate_set: CandidateSet) -> float | None:
    """Spread of mean score across augmentation keys: do different augmented
    views of the same input point to different candidates?

    Groups candidates by `augmentation_key`, takes each group's best score,
    and reports the population standard deviation across groups. `None` with
    fewer than 2 distinct augmentation keys.
    """
    by_augmentation: dict[str, float] = {}
    for candidate in candidate_set.candidates:
        if candidate.augmentation_key is None or candidate.beam_score is None:
            continue
        current = by_augmentation.get(candidate.augmentation_key)
        if current is None or candidate.beam_score > current:
            by_augmentation[candidate.augmentation_key] = candidate.beam_score
    if len(by_augmentation) < 2:
        return None
    return statistics.pstdev(by_augmentation.values())


def seed_disagreement(candidate_set: CandidateSet) -> float | None:
    """Placeholder for cross-TTT-seed disagreement.

    Always `None` against RUN-001: every candidate shares `ttt_seed=1`
    (`experiments/RUN001/BASELINE_SPEC.md` "Seeds"), so there is only one
    seed's output to compare against itself. Implemented so a future
    multi-seed run has a working function to call.
    """
    seeds = {c.seed for c in candidate_set.candidates if c.seed is not None}
    return None if len(seeds) < 2 else float(len(seeds))


def solver_disagreement(candidate_set: CandidateSet) -> float | None:
    """Placeholder for cross-solver-branch disagreement.

    Always `None` against RUN-001: every candidate shares one
    `solver_branch` (`nvarc_architects_qwen3_4b`). Real once a complementary
    solver (TRM) contributes candidates to the same `CandidateSet`.
    """
    branches = {c.solver_branch for c in candidate_set.candidates if c.solver_branch}
    return None if len(branches) < 2 else float(len(branches))


def duplicate_fraction(candidate_set: CandidateSet) -> float | None:
    """Fraction of generation events that did not introduce a new unique grid."""
    total = len(candidate_set.candidates)
    if total == 0:
        return None
    unique = len(candidate_set.unique_grid_shas())
    return 1 - unique / total


def time_since_last_new_unique(candidate_set: CandidateSet) -> float | None:
    """Seconds of compute spent after the last first-seen unique grid.

    Needs `cumulative_task_s` and `generation_order` on every candidate; a
    large value means the solver kept generating without finding anything
    new — the empirical signal `AllocationAction.STOP` should eventually key
    off (`allocator/stopping.py`), computed here so it exists as a feature to
    fit against before the allocator experiments (EXP003+) touch it.
    """
    timed = [
        c
        for c in candidate_set.candidates
        if c.cumulative_task_s is not None and c.generation_order is not None
    ]
    if not timed:
        return None
    timed.sort(key=lambda c: c.generation_order)
    seen: set[str] = set()
    last_new_time = timed[0].cumulative_task_s
    for candidate in timed:
        if candidate.grid_sha1 not in seen:
            seen.add(candidate.grid_sha1)
            last_new_time = candidate.cumulative_task_s
    final_time = timed[-1].cumulative_task_s
    return final_time - last_new_time


def growth_rate(snapshots: list[BudgetSnapshot]) -> float | None:
    """New-unique-grids-per-snapshot, averaged over consecutive snapshot pairs."""
    if len(snapshots) < 2:
        return None
    rates = []
    seen: set[str] = set(snapshots[0].candidate_shas)
    for previous, current in zip(snapshots, snapshots[1:]):
        new = set(current.candidate_shas) - seen
        budget_delta = current.budget - previous.budget
        if budget_delta > 0:
            rates.append(len(new) / budget_delta)
        seen.update(current.candidate_shas)
    return statistics.fmean(rates) if rates else None


def rank_volatility(snapshots: list[BudgetSnapshot], selection_by_snapshot: list[str | None]) -> float | None:
    """How often the leading (rank-1-implied) grid changes across snapshots.

    `selection_by_snapshot[i]` is whatever grid_sha1 a caller considers "best"
    at `snapshots[i]` (e.g. highest reconstructed score at that budget cutoff);
    this function just counts how often that identity changes between
    consecutive snapshots, normalised to [0, 1].
    """
    changes = sum(
        1
        for a, b in zip(selection_by_snapshot, selection_by_snapshot[1:])
        if a is not None and b is not None and a != b
    )
    denom = len(selection_by_snapshot) - 1
    return changes / denom if denom > 0 else None


def verifier_disagreement(rankings: list[list[str]]) -> float | None:
    """Fraction of verifier pairs whose top-1 pick differs, over all rankings given.

    Generic over any set of ranked-grid-sha1 lists — used to compare several
    verifiers' opinions on the same test index, not tied to any one verifier
    implementation.
    """
    tops = [r[0] for r in rankings if r]
    if len(tops) < 2:
        return None
    pairs = [(i, j) for i in range(len(tops)) for j in range(i + 1, len(tops))]
    disagreements = sum(1 for i, j in pairs if tops[i] != tops[j])
    return disagreements / len(pairs)
