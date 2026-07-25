"""Verifier interface: `TaskEvidence -> VerificationResult`, never touching ground truth.

Every baseline in `original.py`/`consensus.py`/`learned.py`/`independent.py`
implements `Verifier.rank`. `softmax`, `rank_from_scores`, `build_result` and
`build_result_from_probabilities` are shared so every baseline produces a
`VerificationResult` of the same shape — which is what makes V0-V3
comparable in EXP002-B rather than several ad hoc formats.

**Confidence-semantics fix (EXP002-B Part 1).** The first EXP002 pass's
`build_result` ran every candidate set, singleton or not, through the same
softmax. A one-candidate set always softmaxes to probability 1.0 — correct
about ranking (there is nothing to lose to) but silently wrong if read as "the
verifier is sure this is right" (`experiments/EXP002/ERROR_ANALYSIS.md`'s five
`margin=1.000, rank=never generated` examples). Both builders below now
compute `candidate_set_sufficiency` from the softmax distribution's own
effective size and set `abstain=True` whenever there are 0 or 1 *effectively
distinguishable* candidates, backing `correctness_confidence` off to a
caller-supplied empirical prior in that case instead of reporting the trivial
ranking probability as if it answered a different question.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from src.harness.schemas import TaskEvidence, VerificationResult

DEFAULT_SINGLETON_PRIOR = 0.5
"""Fallback empirical prior for P(correct) when a caller does not supply one
measured from data. 0.5 encodes "no information", not "50% of singletons are
right" — callers evaluating against real labels (`exp002b_verifier_eval.py`)
should pass the corpus's own measured oracle rate instead, per
`experiments/EXP002B/CONFIDENCE_SEMANTICS.md`."""

SUFFICIENCY_SPAN = 2.0
"""`candidate_set_sufficiency` reaches 1.0 at an effective candidate count of
1 + SUFFICIENCY_SPAN. Effective count is `exp(entropy)`
(`features/uncertainty.py`'s `effective_candidate_count`), so 3 genuinely
competitive candidates (entropy = ln 3) saturates sufficiency; two duplicates
of the same grid contribute less than two genuinely different grids do,
because entropy is lower when the score mass concentrates."""


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


def _entropy(probabilities: dict[str, float]) -> float:
    return -sum(p * math.log(p) for p in probabilities.values() if p > 0)


def _sufficiency(probabilities: dict[str, float]) -> float:
    """0 for <=1 effectively distinguishable candidate, 1.0 once the softmax
    distribution's effective size reaches `1 + SUFFICIENCY_SPAN`."""
    if len(probabilities) <= 1:
        return 0.0
    effective_count = math.exp(_entropy(probabilities))
    return min(1.0, (effective_count - 1.0) / SUFFICIENCY_SPAN)


def build_result(
    task_id: str,
    test_index: int,
    scores: dict[str, float],
    verifier_name: str,
    temperature: float = 1.0,
    provenance: dict[str, str] | None = None,
    singleton_prior: float = DEFAULT_SINGLETON_PRIOR,
) -> VerificationResult:
    """Turn a `{grid_sha1: score}` map into a full `VerificationResult`.

    Only grids present in `scores` are ranked at all — a verifier that has no
    opinion about a grid (e.g. it was never selected by NVARC, for `B0`)
    leaves it out rather than guessing. `scores` are relative and uncalibrated
    (a heuristic's raw output), so `correctness_confidence` here is the same
    softmax distribution as `ranking_confidence` — this builder cannot
    manufacture calibration a heuristic verifier never had, and
    `uncertainty_reason` says so explicitly.
    """
    ranked = rank_from_scores(scores)
    probabilities = softmax(scores, temperature=temperature)
    sufficiency = _sufficiency(probabilities)
    abstain = len(probabilities) <= 1

    top1 = probabilities.get(ranked[0], 0.0) if ranked else 0.0
    top2 = probabilities.get(ranked[1], 0.0) if len(ranked) > 1 else 0.0
    ranking_confidence = top1

    if abstain:
        correctness_confidence = {sha1: singleton_prior for sha1 in scores}
        reason = (
            f"{len(scores)} unique candidate(s): no ranking evidence available; "
            f"correctness_confidence backed off to empirical prior {singleton_prior}"
        )
    else:
        correctness_confidence = dict(probabilities)
        reason = "correctness_confidence is uncalibrated (ranking-derived); this verifier has no fitted calibration"

    return VerificationResult(
        task_id=task_id,
        test_index=test_index,
        ranked_grid_shas=ranked,
        probability_correct=probabilities,
        uncertainty=1.0 - sufficiency,
        confidence_margin=top1 - top2,
        ranking_confidence=ranking_confidence,
        correctness_confidence=correctness_confidence,
        candidate_set_sufficiency=sufficiency,
        abstain=abstain,
        uncertainty_reason=reason,
        feature_provenance=provenance or {},
        verifier_name=verifier_name,
    )


def build_result_from_probabilities(
    task_id: str,
    test_index: int,
    probabilities: dict[str, float],
    verifier_name: str,
    provenance: dict[str, str] | None = None,
    singleton_prior: float = DEFAULT_SINGLETON_PRIOR,
) -> VerificationResult:
    """Like `build_result`, but for a verifier (`learned.py`) whose scores are
    already independent, calibrated P(this grid is correct) estimates — e.g.
    `LogisticRegression.predict_proba` fit against real labels — not a joint
    distribution to normalise. No softmax over them: re-normalising
    already-calibrated probabilities would discard the calibration.

    Sufficiency here is judged from the same probabilities directly (as a
    distribution over "which grid, if any, is correct") rather than from a
    derived softmax, since these are already probability-shaped.
    """
    ranked = rank_from_scores(probabilities)
    sufficiency = _sufficiency(probabilities) if len(probabilities) > 1 else 0.0
    abstain = len(probabilities) <= 1

    top1 = probabilities.get(ranked[0], 0.0) if ranked else 0.0
    top2 = probabilities.get(ranked[1], 0.0) if len(ranked) > 1 else 0.0
    margin = top1 - top2

    if abstain:
        correctness_confidence = {sha1: singleton_prior for sha1 in probabilities}
        reason = (
            f"{len(probabilities)} unique candidate(s): no ranking evidence available; "
            f"correctness_confidence backed off to empirical prior {singleton_prior}"
        )
    else:
        correctness_confidence = dict(probabilities)
        reason = ""

    return VerificationResult(
        task_id=task_id,
        test_index=test_index,
        ranked_grid_shas=ranked,
        probability_correct=probabilities,
        uncertainty=1.0 - sufficiency,
        confidence_margin=margin,
        ranking_confidence=top1,
        correctness_confidence=correctness_confidence,
        candidate_set_sufficiency=sufficiency,
        abstain=abstain,
        uncertainty_reason=reason,
        feature_provenance=provenance or {},
        verifier_name=verifier_name,
    )
