"""Probability calibration for verifier output, and the metrics that judge it.

A verifier can rank correctly while its probabilities are meaningless (a
ranking is invariant to any monotonic transform of the scores; calibration is
not). This module is the one place that gap gets measured and, optionally,
closed with Platt scaling.
"""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression

from src.harness.metrics import (
    brier_score,
    expected_calibration_error,
    false_confidence_rate,
    negative_log_likelihood,
    reliability_bins,
)


class PlattCalibrator:
    """1-D logistic regression mapping a raw score to a calibrated P(correct).

    Fit on a held-out (dev) set of `(raw_score, is_correct)` pairs, never on
    the same set a verifier's ranking was evaluated on — that would be
    fitting calibration to the test it is supposed to validate.
    """

    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=1000)
        self._fitted = False

    def fit(self, raw_scores: list[float], outcomes: list[bool]) -> None:
        if len(set(outcomes)) < 2:
            raise ValueError("Platt scaling needs both classes present in the fit set")
        self.model.fit([[s] for s in raw_scores], outcomes)
        self._fitted = True

    def calibrate(self, raw_score: float) -> float:
        if not self._fitted:
            raise RuntimeError("PlattCalibrator.calibrate called before fit()")
        return float(self.model.predict_proba([[raw_score]])[0][1])

    def calibrate_many(self, raw_scores: list[float]) -> list[float]:
        return [self.calibrate(s) for s in raw_scores]


def calibration_report(
    probabilities: list[float], outcomes: list[bool], n_bins: int = 10
) -> dict:
    """Every calibration metric EXP002 requires, in one call."""
    return {
        "brier_score": brier_score(probabilities, outcomes),
        "expected_calibration_error": expected_calibration_error(probabilities, outcomes, n_bins),
        "negative_log_likelihood": negative_log_likelihood(probabilities, outcomes),
        "false_confidence_rate_at_0.8": false_confidence_rate(probabilities, outcomes, threshold=0.8),
        "reliability_bins": reliability_bins(probabilities, outcomes, n_bins),
        "n": len(probabilities),
    }
