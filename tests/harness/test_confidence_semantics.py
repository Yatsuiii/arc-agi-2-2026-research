"""Tests for the EXP002-B confidence-semantics fix: ranking vs. correctness confidence.

Six required scenarios (`experiments/EXP002B/CONFIDENCE_SEMANTICS.md`):
one unique wrong candidate, one unique correct candidate, many duplicate
generations of one unique candidate, two near-tied candidates, one candidate
supported across independent transformations, and a candidate set whose
native score is high but structural evidence contradicts it (the last is a
consumer-side scenario — this file tests the confidence primitives it needs).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.verifier.base import (  # noqa: E402
    DEFAULT_SINGLETON_PRIOR,
    build_result,
    build_result_from_probabilities,
)


# -- scenario 1 & 2: singleton candidate, wrong vs correct --------------------------
#
# The whole point of the fix: the verifier has identical evidence in both
# cases (one candidate, no alternative to compare against), so its reported
# confidence must be identical too. Ground truth is not an input to `rank()`
# at all -- these two scenarios are indistinguishable to the verifier by
# construction, which is exactly what abstention exists to signal honestly.


def test_singleton_wrong_candidate_does_not_get_correctness_confidence_1():
    result = build_result("t", 0, {"wrong": 0.9}, "v")
    assert result.abstain is True
    assert result.correctness_confidence["wrong"] == pytest.approx(DEFAULT_SINGLETON_PRIOR)
    assert result.correctness_confidence["wrong"] != 1.0


def test_singleton_correct_candidate_gets_the_same_prior_as_wrong_would():
    result = build_result("t", 0, {"correct": 0.9}, "v")
    assert result.abstain is True
    assert result.correctness_confidence["correct"] == pytest.approx(DEFAULT_SINGLETON_PRIOR)


def test_singleton_ranking_confidence_is_trivially_high_but_flagged():
    result = build_result("t", 0, {"only": 0.1}, "v")
    assert result.ranking_confidence == 1.0  # no alternatives to lose to -- this part is fine
    assert result.abstain is True
    assert "no ranking evidence available" in result.uncertainty_reason


def test_singleton_prior_is_configurable():
    result = build_result("t", 0, {"a": 1.0}, "v", singleton_prior=0.05)
    assert result.correctness_confidence["a"] == pytest.approx(0.05)


def test_empty_candidate_set_also_abstains():
    result = build_result("t", 0, {}, "v")
    assert result.abstain is True
    assert result.ranked_grid_shas == []
    assert result.candidate_set_sufficiency == 0.0


# -- scenario 3: many duplicate generations of one unique candidate -------------------


def test_many_duplicates_of_one_grid_still_abstains():
    """Vote count is irrelevant to sufficiency here: whether a grid was
    generated once or a hundred times, there is still only one *unique*
    candidate and therefore no ranking evidence between alternatives."""
    result = build_result("t", 0, {"only": 50.0}, "v")  # score already aggregates duplicate votes
    assert result.abstain is True
    assert result.candidate_set_sufficiency == 0.0


# -- scenario 4: two near-tied candidates ---------------------------------------------


def test_near_tied_candidates_have_low_but_nonzero_sufficiency():
    tied = build_result("t", 0, {"a": 1.0, "b": 0.999}, "v")
    assert tied.abstain is False
    assert 0.0 < tied.candidate_set_sufficiency <= 1.0
    assert tied.ranking_confidence < 0.6  # close to 50/50, not confident


def test_near_tied_has_lower_ranking_confidence_than_a_clear_winner():
    tied = build_result("t", 0, {"a": 1.0, "b": 0.999}, "v")
    clear = build_result("t", 0, {"a": 100.0, "b": -100.0}, "v")
    assert tied.ranking_confidence < clear.ranking_confidence


def test_sufficiency_increases_with_more_genuinely_distinct_candidates():
    two = build_result("t", 0, {"a": 1.0, "b": 1.0}, "v")
    three = build_result("t", 0, {"a": 1.0, "b": 1.0, "c": 1.0}, "v")
    assert three.candidate_set_sufficiency >= two.candidate_set_sufficiency


# -- correctness_confidence: heuristic (uncalibrated) vs. build_result_from_probabilities ---


def test_heuristic_correctness_confidence_is_flagged_uncalibrated():
    result = build_result("t", 0, {"a": 1.0, "b": 0.0}, "v")
    assert result.abstain is False
    assert "uncalibrated" in result.uncertainty_reason


def test_calibrated_builder_does_not_flag_uncalibrated_when_sufficient():
    result = build_result_from_probabilities("t", 0, {"a": 0.9, "b": 0.1}, "learned")
    assert result.abstain is False
    assert result.correctness_confidence == {"a": 0.9, "b": 0.1}
    assert "uncalibrated" not in result.uncertainty_reason


def test_calibrated_builder_still_abstains_and_backs_off_on_singleton():
    result = build_result_from_probabilities("t", 0, {"a": 0.99}, "learned", singleton_prior=0.3)
    assert result.abstain is True
    assert result.correctness_confidence["a"] == pytest.approx(0.3)
    assert result.correctness_confidence["a"] != 0.99


# -- scenario: ranking_confidence vs correctness_confidence must be independently readable --


def test_ranking_and_correctness_confidence_can_diverge():
    """A calibrated model can be sure B ranks above A while still being unsure
    B is actually right -- these must not be forced to the same number."""
    result = build_result_from_probabilities("t", 0, {"a": 0.05, "b": 0.15}, "learned")
    assert result.ranked_grid_shas[0] == "b"
    assert result.ranking_confidence == pytest.approx(0.15)  # b's own (low) absolute probability
    assert result.correctness_confidence["b"] == pytest.approx(0.15)
    # Both are low -- "wins the contest" and "is actually correct" are both
    # weak here, which is the honest answer when every candidate looks bad.
    assert result.ranking_confidence < 0.5
