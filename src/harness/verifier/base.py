"""Verifier interface: `TaskEvidence -> VerificationResult`, never touching ground truth.

Every baseline in `original.py`/`consensus.py`/`learned.py` implements
`Verifier.rank`. `softmax`, `rank_from_scores` and `build_result` are shared
so every baseline produces a `VerificationResult` of the same shape — which is
what makes B0-B8 directly comparable in EXP002 rather than five ad hoc
formats.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from src.harness.schemas import TaskEvidence, VerificationResult


class Verifier(ABC):
    """A verifier ranks the grids already in a `CandidateSet`. It generates nothing."""

    name: str = "base"

    @abstractmethod
    def rank(self, evidence: TaskEvidence) -> VerificationResult: ...


def softmax(scores: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
    """Numerically stable softmax over a `{grid_sha1: score}` map."""
    if not scores:
        return {}
    top = max(scores.values())
    weights = {sha1: math.exp((value - top) / temperature) for sha1, value in scores.items()}
    total = sum(weights.values())
    return {sha1: w / total for sha1, w in weights.items()}


def rank_from_scores(scores: dict[str, float]) -> list[str]:
    """Grid sha1s ordered best-first. Python's sort is stable, so tied scores
    keep their `scores` dict insertion order rather than shuffling."""
    return sorted(scores, key=lambda sha1: scores[sha1], reverse=True)


def build_result(
    task_id: str,
    test_index: int,
    scores: dict[str, float],
    verifier_name: str,
    temperature: float = 1.0,
    provenance: dict[str, str] | None = None,
) -> VerificationResult:
    """Turn a `{grid_sha1: score}` map into a full `VerificationResult`.

    Only grids present in `scores` are ranked at all — a verifier that has no
    opinion about a grid (e.g. it was never selected by NVARC, for `B0`)
    leaves it out rather than guessing.
    """
    ranked = rank_from_scores(scores)
    probabilities = softmax(scores, temperature=temperature)
    top1 = probabilities.get(ranked[0], 0.0) if ranked else 0.0
    top2 = probabilities.get(ranked[1], 0.0) if len(ranked) > 1 else 0.0
    uncertainty = (
        -sum(p * math.log(p) for p in probabilities.values() if p > 0) if probabilities else 0.0
    )
    return VerificationResult(
        task_id=task_id,
        test_index=test_index,
        ranked_grid_shas=ranked,
        probability_correct=probabilities,
        uncertainty=uncertainty,
        confidence_margin=top1 - top2,
        feature_provenance=provenance or {},
        verifier_name=verifier_name,
    )


def build_result_from_probabilities(
    task_id: str,
    test_index: int,
    probabilities: dict[str, float],
    verifier_name: str,
    provenance: dict[str, str] | None = None,
) -> VerificationResult:
    """Like `build_result`, but for a verifier (`learned.py`) whose scores are
    already independent P(this grid is correct) estimates, not a joint
    distribution to normalise. No softmax: re-normalising already-calibrated
    probabilities would silently discard the calibration.
    """
    ranked = rank_from_scores(probabilities)
    top1 = probabilities.get(ranked[0], 0.0) if ranked else 0.0
    top2 = probabilities.get(ranked[1], 0.0) if len(ranked) > 1 else 0.0
    margin = top1 - top2
    return VerificationResult(
        task_id=task_id,
        test_index=test_index,
        ranked_grid_shas=ranked,
        probability_correct=probabilities,
        uncertainty=1.0 - margin,
        confidence_margin=margin,
        feature_provenance=provenance or {},
        verifier_name=verifier_name,
    )
