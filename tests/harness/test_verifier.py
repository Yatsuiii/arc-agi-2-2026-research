from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.schemas import Candidate, CandidateSet, SelectionRecord, TaskEvidence  # noqa: E402
from src.harness.verifier.base import build_result, build_result_from_probabilities, softmax  # noqa: E402
from src.harness.verifier.calibration import PlattCalibrator, calibration_report  # noqa: E402
from src.harness.verifier.consensus import (  # noqa: E402
    AugmentationConsensusVerifier,
    DuplicateFrequencyVerifier,
    RawScoreVerifier,
    ScoreWeightedConsensusVerifier,
    SeedConsensusVerifier,
    TransformationConsistencyVerifier,
)
from src.harness.verifier.learned import LearnedVerifier  # noqa: E402
from src.harness.verifier.original import OriginalSelectionVerifier  # noqa: E402


def make_candidate(grid_sha1, beam_score=None, **kwargs):
    defaults = dict(task_id="t", test_index=0, grid=[[1]], grid_sha1=grid_sha1, solver_branch="nvarc")
    defaults.update(kwargs)
    return Candidate(beam_score=beam_score, **defaults)


# -- base helpers --------------------------------------------------------------------


def test_softmax_sums_to_one_and_prefers_higher_score():
    probs = softmax({"a": 2.0, "b": 0.0})
    assert probs["a"] > probs["b"]
    assert probs["a"] + probs["b"] == pytest.approx(1.0)


def test_softmax_empty():
    assert softmax({}) == {}


def test_build_result_ranks_best_score_first():
    result = build_result("t", 0, {"a": 1.0, "b": 5.0}, "test_verifier")
    assert result.ranked_grid_shas == ["b", "a"]
    assert result.verifier_name == "test_verifier"
    assert result.confidence_margin > 0


def test_build_result_empty_scores():
    result = build_result("t", 0, {}, "test_verifier")
    assert result.ranked_grid_shas == []
    assert result.confidence_margin == 0.0


def test_build_result_from_probabilities_does_not_renormalize():
    result = build_result_from_probabilities("t", 0, {"a": 0.9, "b": 0.1}, "learned")
    assert result.probability_correct == {"a": 0.9, "b": 0.1}
    assert result.ranked_grid_shas == ["a", "b"]
    assert result.confidence_margin == pytest.approx(0.8)


# -- B0 original ------------------------------------------------------------------


def test_original_selection_verifier_reproduces_archived_top2():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a"), make_candidate("b"), make_candidate("c")],
        selection=[
            SelectionRecord("t", 0, "b", rank=1, selected=True, algorithm="score_kgmon"),
            SelectionRecord("t", 0, "a", rank=2, selected=True, algorithm="score_kgmon"),
            SelectionRecord("t", 0, "c", rank=3, selected=False, algorithm="score_kgmon"),
        ],
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = OriginalSelectionVerifier().rank(evidence)
    assert result.top_k(2) == cs.frozen_selected() == ["b", "a"]


def test_original_selection_verifier_empty_without_selection_records():
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a")])
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = OriginalSelectionVerifier().rank(evidence)
    assert result.ranked_grid_shas == []


# -- B1-B5 consensus baselines -----------------------------------------------------


def test_raw_score_verifier_ranks_by_beam_score():
    cs = CandidateSet(
        task_id="t", test_index=0, candidates=[make_candidate("a", 0.1), make_candidate("b", 0.9)]
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = RawScoreVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "b"


def test_duplicate_frequency_verifier_ranks_by_vote_count():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a"), make_candidate("a"), make_candidate("a"), make_candidate("b")],
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = DuplicateFrequencyVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "a"


def test_augmentation_consensus_verifier_ranks_by_distinct_augmentations():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", augmentation_key="aug1"),
            make_candidate("a", augmentation_key="aug2"),
            make_candidate("b", augmentation_key="aug1"),
        ],
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = AugmentationConsensusVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "a"


def test_seed_consensus_verifier_ties_when_run001_shaped():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", seed=1), make_candidate("b", seed=1)],
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = SeedConsensusVerifier().rank(evidence)
    assert set(result.ranked_grid_shas) == {"a", "b"}  # tied; both present, order incidental


def test_score_weighted_consensus_combines_votes_and_mean_aug_score():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", score_aug_mean=0.1),
            make_candidate("a", score_aug_mean=0.1),  # 2 votes, low mean -> high score_kgmon
            make_candidate("b", score_aug_mean=5.0),  # 1 vote, high mean -> low score_kgmon
        ],
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = ScoreWeightedConsensusVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "a"


# -- B6 transformation consistency -------------------------------------------------


def test_transformation_consistency_verifier_prefers_structurally_consistent_grid():
    good = [[9, 9], [9, 8]]
    bad = [[9, 9, 9]]  # wrong shape
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("good", grid=good), make_candidate("bad", grid=bad)],
    )
    demo_pairs = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    evidence = TaskEvidence(
        task_id="t", test_index=0, candidate_set=cs, demo_pairs=demo_pairs, test_input=[[1, 2], [3, 4]]
    )
    result = TransformationConsistencyVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "good"


def test_transformation_consistency_verifier_degrades_gracefully_without_context():
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a")])
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)  # no demo_pairs
    result = TransformationConsistencyVerifier().rank(evidence)
    assert "a" in result.ranked_grid_shas


# -- B7 learned ---------------------------------------------------------------------


def test_learned_verifier_fits_and_ranks():
    verifier = LearnedVerifier(feature_names=["f1", "f2"])
    rows = [{"f1": 1.0, "f2": 0.0}, {"f1": 0.0, "f2": 1.0}] * 5
    labels = [True, False] * 5
    verifier.fit(rows, labels)

    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a"), make_candidate("b")])
    evidence = TaskEvidence(
        task_id="t",
        test_index=0,
        candidate_set=cs,
        features_by_grid={"a": {"f1": 1.0, "f2": 0.0}, "b": {"f1": 0.0, "f2": 1.0}},
    )
    result = verifier.rank(evidence)
    assert result.ranked_grid_shas[0] == "a"
    assert 0.0 <= result.probability_correct["a"] <= 1.0


def test_learned_verifier_raises_before_fit():
    verifier = LearnedVerifier(feature_names=["f1"])
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a")])
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs, features_by_grid={"a": {"f1": 1.0}})
    with pytest.raises(RuntimeError):
        verifier.rank(evidence)


def test_learned_verifier_requires_both_classes():
    verifier = LearnedVerifier(feature_names=["f1"])
    with pytest.raises(ValueError):
        verifier.fit([{"f1": 1.0}, {"f1": 0.0}], [True, True])


def test_learned_verifier_missing_feature_defaults_to_zero():
    verifier = LearnedVerifier(feature_names=["f1", "f2"])
    assert verifier.vectorize({"f1": 1.0}) == [1.0, 0.0]
    assert verifier.vectorize({"f1": None, "f2": 3.0}) == [0.0, 3.0]


def test_learned_verifier_feature_importances():
    verifier = LearnedVerifier(feature_names=["f1"])
    verifier.fit([{"f1": 1.0}, {"f1": -1.0}] * 5, [True, False] * 5)
    importances = verifier.feature_importances()
    assert set(importances) == {"f1"}


# -- calibration ---------------------------------------------------------------------


def test_platt_calibrator_fits_and_calibrates():
    calibrator = PlattCalibrator()
    calibrator.fit([1.0, 1.0, -1.0, -1.0], [True, True, False, False])
    p_high = calibrator.calibrate(1.0)
    p_low = calibrator.calibrate(-1.0)
    assert p_high > p_low


def test_platt_calibrator_raises_before_fit():
    calibrator = PlattCalibrator()
    with pytest.raises(RuntimeError):
        calibrator.calibrate(1.0)


def test_calibration_report_contains_all_required_metrics():
    report = calibration_report([0.9, 0.1, 0.5], [True, False, True])
    for key in (
        "brier_score",
        "expected_calibration_error",
        "negative_log_likelihood",
        "false_confidence_rate_at_0.8",
        "reliability_bins",
        "n",
    ):
        assert key in report
