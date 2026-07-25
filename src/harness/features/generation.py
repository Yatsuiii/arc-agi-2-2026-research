"""Generation-evidence features: what the archive's own scores and counts say.

Every function takes a `CandidateSet` (see `src/harness/schemas.py`) and
returns `{grid_sha1: {feature_name: value}}`. A value of `None` means the
feature is not computable from this candidate set — usually because RUN-001's
real archive is a single run, single TTT seed, and single solver branch
(`experiments/RUN001/BASELINE_SPEC.md` "Seeds"), so anything that needs
cross-seed or cross-branch variation has nothing to vary over. Returning
`None` rather than a constant keeps that limitation visible to callers instead
of silently reporting "1 seed agrees with itself" as if it were a real signal.
"""

from __future__ import annotations

import statistics

from src.harness.schemas import BudgetSnapshot, CandidateSet


def score_features(candidate_set: CandidateSet) -> dict[str, dict[str, float | None]]:
    """Per-unique-grid features from beam score, rank, and generation metadata."""
    by_grid: dict[str, list] = {}
    for candidate in candidate_set.candidates:
        by_grid.setdefault(candidate.grid_sha1, []).append(candidate)

    rank_by_grid = {r.grid_sha1: r.rank for r in candidate_set.selection}

    all_scores = [c.beam_score for c in candidate_set.candidates if c.beam_score is not None]
    score_lo = min(all_scores) if all_scores else None
    score_hi = max(all_scores) if all_scores else None

    # Score margin needs candidates ordered best-to-worst; higher beam_score is better.
    grid_best_score = {
        sha1: max((c.beam_score for c in group if c.beam_score is not None), default=None)
        for sha1, group in by_grid.items()
    }
    ordered_scores = sorted((s for s in grid_best_score.values() if s is not None), reverse=True)

    features: dict[str, dict[str, float | None]] = {}
    for sha1, group in by_grid.items():
        best_score = grid_best_score[sha1]
        normalized = None
        if best_score is not None and score_hi is not None and score_hi != score_lo:
            normalized = (best_score - score_lo) / (score_hi - score_lo)

        margin = None
        if best_score is not None and len(ordered_scores) > 1:
            rival = next((s for s in ordered_scores if s != best_score), None)
            if rival is not None:
                margin = best_score - rival

        seeds = {c.seed for c in group if c.seed is not None}
        augmentations = {c.augmentation_key for c in group if c.augmentation_key is not None}
        branches = {c.solver_branch for c in group if c.solver_branch}
        first = min(
            group,
            key=lambda c: (
                c.generation_order if c.generation_order is not None else float("inf")
            ),
        )

        features[sha1] = {
            "original_score": best_score,
            "normalized_score": normalized,
            "original_rank": rank_by_grid.get(sha1),
            "score_margin": margin,
            "generation_order_first": first.generation_order,
            "time_first_appearance_s": first.cumulative_task_s,
            "duplicate_generation_count": len(group),
            "reconstructed_score_kgmon": reconstruct_score_kgmon(group),
            # None (not 1) when there is only one seed/branch to count: RUN-001's
            # archive has no cross-seed or cross-branch variation to measure.
            "n_seeds_producing": len(seeds) if len(seeds) > 1 else None,
            "n_augmentations_producing": len(augmentations) if augmentations else None,
            "n_solver_branches_producing": len(branches) if len(branches) > 1 else None,
        }
    return features


def reconstruct_score_kgmon(candidates_for_grid: list) -> float | None:
    """Approximate NVARC's own selector score for one unique grid.

    `score_kgmon = len(guesses) - mean(mean(score_aug))`
    (`experiments/RUN001/BASELINE_SPEC.md` "Candidate scoring and ranking").
    The archive stores rank and a `selected` flag but not this value itself
    (`experiments/RUN001/VALIDATION_REPORT.md`), so it is rebuilt from vote
    count and the memoised augmentation-mean score. Used by
    `verifier/consensus.py`'s B5 (score-weighted consensus), which is this
    reconstruction under a different name — the two are kept as one
    implementation rather than two so a fix to the formula only has one place
    to land.
    """
    means = [c.score_aug_mean for c in candidates_for_grid if c.score_aug_mean is not None]
    if not means:
        return None
    return len(candidates_for_grid) - statistics.fmean(means)


def rank_and_score_stability(runs: list[CandidateSet]) -> dict[str, dict[str, float | None]]:
    """Rank/score stability of each grid across repeated runs of the same task.

    RUN-001 is a single run, so this always receives a one-element `runs` and
    returns `None` for every grid — implemented so a future multi-run replay
    (`AB-*` reruns, or RUN-002) has a working function to call, not a TODO.
    """
    if len(runs) < 2:
        shas = runs[0].unique_grid_shas() if runs else []
        return {sha1: {"rank_stability": None, "score_stability": None} for sha1 in shas}

    ranks_by_grid: dict[str, list[int]] = {}
    scores_by_grid: dict[str, list[float]] = {}
    for run in runs:
        rank_by_grid = {r.grid_sha1: r.rank for r in run.selection}
        for sha1 in run.unique_grid_shas():
            if sha1 in rank_by_grid:
                ranks_by_grid.setdefault(sha1, []).append(rank_by_grid[sha1])
            scores = [c.beam_score for c in run.candidates_for_grid(sha1) if c.beam_score is not None]
            if scores:
                scores_by_grid.setdefault(sha1, []).append(max(scores))

    result: dict[str, dict[str, float | None]] = {}
    for sha1 in set(ranks_by_grid) | set(scores_by_grid):
        ranks = ranks_by_grid.get(sha1, [])
        scores = scores_by_grid.get(sha1, [])
        result[sha1] = {
            "rank_stability": -statistics.pstdev(ranks) if len(ranks) > 1 else None,
            "score_stability": -statistics.pstdev(scores) if len(scores) > 1 else None,
        }
    return result


def persistence_features(
    snapshots: list[BudgetSnapshot],
) -> dict[str, dict[str, float | None]]:
    """How early and how consistently each grid appeared across budget snapshots.

    `snapshots` must be sorted by increasing budget (`snapshots.py` guarantees
    this). "Growth after appearance" is the count of later snapshots in which
    the grid's own candidate set kept growing around it, a proxy for whether
    the solver kept finding this same answer as it searched further.
    """
    if not snapshots:
        return {}
    all_shas: set[str] = set()
    for snap in snapshots:
        all_shas.update(snap.candidate_shas)

    features: dict[str, dict[str, float | None]] = {}
    for sha1 in all_shas:
        present_at = [i for i, snap in enumerate(snapshots) if sha1 in snap.candidate_shas]
        first_index = present_at[0]
        features[sha1] = {
            "first_appearance_snapshot_index": float(first_index),
            "first_appearance_budget": snapshots[first_index].budget,
            "snapshots_present_count": float(len(present_at)),
            "persistence_fraction": len(present_at) / (len(snapshots) - first_index),
        }
    return features
