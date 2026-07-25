from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.features.independence import (  # noqa: E402
    INDEPENDENT_FEATURES,
    SCORE_DERIVED_FEATURES,
    ScoreLeakageError,
    assert_score_independent,
)


def test_score_derived_and_independent_sets_are_disjoint():
    assert SCORE_DERIVED_FEATURES.isdisjoint(INDEPENDENT_FEATURES)


def test_assert_score_independent_passes_pure_independent_list():
    assert_score_independent(["output_size_matches_expected", "contradiction_count"])  # must not raise


def test_assert_score_independent_rejects_score_derived_feature():
    with pytest.raises(ScoreLeakageError):
        assert_score_independent(["output_size_matches_expected", "reconstructed_score_kgmon"])


def test_assert_score_independent_rejects_duplicate_and_augmentation_counts():
    with pytest.raises(ScoreLeakageError):
        assert_score_independent(["duplicate_generation_count"])
    with pytest.raises(ScoreLeakageError):
        assert_score_independent(["n_augmentations_producing"])


def test_assert_score_independent_rejects_unknown_feature_name():
    with pytest.raises(ScoreLeakageError):
        assert_score_independent(["some_brand_new_feature_nobody_classified"])


def test_assert_score_independent_error_message_names_the_offender():
    with pytest.raises(ScoreLeakageError, match="original_score"):
        assert_score_independent(["original_score"])


def test_assert_score_independent_accepts_empty_list():
    assert_score_independent([])  # must not raise
