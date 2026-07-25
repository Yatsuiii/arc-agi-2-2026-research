"""Metrics shared by EXP002 (verification) and, later, EXP003/EXP004 (allocation).

Every function here takes plain floats/lists, not harness dataclasses, so it
is testable in isolation and reusable outside the harness (EXP001's headroom
analysis already computes some of these by hand; this module is where they
become one implementation instead of several).
"""

from __future__ import annotations

import math


def recovered_headroom(
    verifier_accuracy: float, original_accuracy: float, oracle_accuracy: float
) -> float | None:
    """(verifier - original) / (oracle - original), the EXP002 primary metric.

    Returns `None` when the denominator is zero (oracle already equals
    original, so there is no headroom to recover — the ratio is undefined,
    not zero and not infinite). Callers must handle `None` explicitly rather
    than defaulting it, per the preregistration's "handle zero-denominator
    cases explicitly."
    """
    denominator = oracle_accuracy - original_accuracy
    if denominator == 0:
        return None
    return (verifier_accuracy - original_accuracy) / denominator


def mean_reciprocal_rank(ranks: list[int | None]) -> float:
    """Mean of 1/rank over tasks where the correct candidate has a rank.

    A `None` rank (correct candidate never generated) contributes 0, matching
    the standard MRR convention of scoring an absent correct answer as 0
    reciprocal rank rather than excluding it.
    """
    if not ranks:
        return 0.0
    return sum((1.0 / r) if r else 0.0 for r in ranks) / len(ranks)


def rank_stats(ranks: list[int | None]) -> dict:
    """Mean/median rank of the correct candidate, over tasks where it was generated."""
    present = sorted(r for r in ranks if r is not None)
    if not present:
        return {"mean_rank": None, "median_rank": None, "n_present": 0}
    mid = len(present) // 2
    median = (
        present[mid]
        if len(present) % 2
        else (present[mid - 1] + present[mid]) / 2
    )
    return {
        "mean_rank": sum(present) / len(present),
        "median_rank": median,
        "n_present": len(present),
    }


def brier_score(probabilities: list[float], outcomes: list[bool]) -> float:
    """Mean squared error between predicted P(correct) and the 0/1 outcome.

    Lower is better; 0 is perfect, 0.25 is what a constant p=0.5 predictor
    scores against a balanced label set.
    """
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must be the same length")
    if not probabilities:
        return 0.0
    return sum((p - float(o)) ** 2 for p, o in zip(probabilities, outcomes)) / len(probabilities)


def expected_calibration_error(
    probabilities: list[float], outcomes: list[bool], n_bins: int = 10
) -> float:
    """Weighted mean gap between predicted confidence and observed accuracy, per bin.

    Standard ECE: bin predictions into `n_bins` equal-width buckets over
    [0, 1], and average `|confidence - accuracy|` per bin weighted by bin
    occupancy. Empty bins contribute nothing.
    """
    if not probabilities:
        return 0.0
    bins = [[] for _ in range(n_bins)]
    for p, o in zip(probabilities, outcomes):
        index = min(int(p * n_bins), n_bins - 1)
        bins[index].append((p, o))
    n = len(probabilities)
    ece = 0.0
    for bucket in bins:
        if not bucket:
            continue
        confidence = sum(p for p, _ in bucket) / len(bucket)
        accuracy = sum(float(o) for _, o in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(confidence - accuracy)
    return ece


def negative_log_likelihood(probabilities: list[float], outcomes: list[bool], eps: float = 1e-9) -> float:
    """Mean binary cross-entropy, with predictions clipped away from 0/1 to stay finite."""
    if not probabilities:
        return 0.0
    total = 0.0
    for p, o in zip(probabilities, outcomes):
        clipped = min(max(p, eps), 1 - eps)
        total += -(math.log(clipped) if o else math.log(1 - clipped))
    return total / len(probabilities)


def false_confidence_rate(
    probabilities: list[float], outcomes: list[bool], threshold: float = 0.8
) -> float | None:
    """Fraction of high-confidence (p >= threshold) predictions that were wrong.

    `None` when nothing cleared the threshold — there is nothing to rate, and
    0 would misleadingly read as "the verifier is well calibrated at this
    threshold" rather than "the verifier never said it was this sure."
    """
    confident = [(p, o) for p, o in zip(probabilities, outcomes) if p >= threshold]
    if not confident:
        return None
    wrong = sum(1 for _, o in confident if not o)
    return wrong / len(confident)


def reliability_bins(
    probabilities: list[float], outcomes: list[bool], n_bins: int = 10
) -> list[dict]:
    """Per-bin (confidence, accuracy, count), the data a reliability diagram plots."""
    bins = [[] for _ in range(n_bins)]
    for p, o in zip(probabilities, outcomes):
        index = min(int(p * n_bins), n_bins - 1)
        bins[index].append((p, o))
    rows = []
    for i, bucket in enumerate(bins):
        low, high = i / n_bins, (i + 1) / n_bins
        if not bucket:
            rows.append({"bin_low": low, "bin_high": high, "confidence": None, "accuracy": None, "count": 0})
            continue
        confidence = sum(p for p, _ in bucket) / len(bucket)
        accuracy = sum(float(o) for _, o in bucket) / len(bucket)
        rows.append({"bin_low": low, "bin_high": high, "confidence": confidence, "accuracy": accuracy, "count": len(bucket)})
    return rows


def auc(scores: list[float], outcomes: list[bool]) -> float | None:
    """AUC-ROC via the Mann-Whitney U statistic, no external dependency.

    `None` when outcomes are all-positive or all-negative — AUC is undefined
    without both classes present, and 0.5 would misrepresent "no signal"
    for "untestable."
    """
    positives = [s for s, o in zip(scores, outcomes) if o]
    negatives = [s for s, o in zip(scores, outcomes) if not o]
    if not positives or not negatives:
        return None
    wins = 0.0
    for p in positives:
        for n in negatives:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(positives) * len(negatives))
