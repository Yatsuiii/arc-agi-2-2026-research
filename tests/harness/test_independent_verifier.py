from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.features.independence import INDEPENDENT_FEATURES, ScoreLeakageError  # noqa: E402
from src.harness.schemas import Candidate, CandidateSet, TaskEvidence  # noqa: E402
from src.harness.verifier.independent import (  # noqa: E402
    HybridVerifier,
    IndependentHeuristicVerifier,
    IndependentLearnedVerifier,
    NativeScoreControlVerifier,
)


def make_candidate(grid_sha1, grid, **kwargs):
    defaults = dict(task_id="t", test_index=0, solver_branch="nvarc")
    defaults.update(kwargs)
    return Candidate(grid=grid, grid_sha1=grid_sha1, **defaults)


# -- V1: native-score control ----------------------------------------------------------


def test_v1_is_named_and_behaves_like_score_weighted_consensus():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", [[1]], score_aug_mean=0.1),
            make_candidate("a", [[1]], score_aug_mean=0.1),
            make_candidate("b", [[2]], score_aug_mean=5.0),
        ],
    )
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)
    result = NativeScoreControlVerifier().rank(evidence)
    assert result.verifier_name == "V1_native_score_control"
    assert result.ranked_grid_shas[0] == "a"  # more votes, lower mean score -> higher score_kgmon


# -- V2-heuristic: structural consistency only -------------------------------------------


def test_v2_heuristic_prefers_structurally_consistent_grid():
    good = [[9, 9], [9, 8]]
    bad = [[9, 9, 9]]
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("good", good), make_candidate("bad", bad)],
    )
    demo_pairs = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    evidence = TaskEvidence(
        task_id="t", test_index=0, candidate_set=cs, demo_pairs=demo_pairs, test_input=[[1, 2], [3, 4]]
    )
    result = IndependentHeuristicVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "good"
    assert result.verifier_name == "V2_independent_heuristic"


def test_v2_heuristic_ignores_native_score_entirely():
    """A grid with a huge beam_score but bad structure must not win over one
    with a tiny beam_score and good structure -- V2 never reads beam_score."""
    good_structure_low_score = [[9, 9], [9, 8]]
    bad_structure_high_score = [[9, 9, 9]]
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("good", good_structure_low_score, beam_score=-1000.0),
            make_candidate("bad", bad_structure_high_score, beam_score=1000.0),
        ],
    )
    demo_pairs = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    evidence = TaskEvidence(
        task_id="t", test_index=0, candidate_set=cs, demo_pairs=demo_pairs, test_input=[[1, 2], [3, 4]]
    )
    result = IndependentHeuristicVerifier().rank(evidence)
    assert result.ranked_grid_shas[0] == "good"


def test_v2_heuristic_degrades_gracefully_without_context():
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a", [[1]])])
    evidence = TaskEvidence(task_id="t", test_index=0, candidate_set=cs)  # no demo_pairs
    result = IndependentHeuristicVerifier().rank(evidence)
    assert "a" in result.ranked_grid_shas


# -- V2-learned: enforced feature independence --------------------------------------------


def test_v2_learned_rejects_score_derived_feature_at_construction():
    with pytest.raises(ScoreLeakageError):
        IndependentLearnedVerifier(feature_names=["original_score"])


def test_v2_learned_accepts_independent_feature_list():
    verifier = IndependentLearnedVerifier(feature_names=["output_size_matches_expected"])
    assert verifier.feature_names == ["output_size_matches_expected"]


def test_v2_learned_defaults_to_the_full_independent_feature_set():
    verifier = IndependentLearnedVerifier()
    assert set(verifier.feature_names) == INDEPENDENT_FEATURES


def test_v2_learned_fits_and_ranks_using_only_independent_features():
    verifier = IndependentLearnedVerifier(feature_names=["contradiction_count"])
    rows = [{"contradiction_count": 0.0}, {"contradiction_count": 3.0}] * 5
    labels = [True, False] * 5
    verifier.fit(rows, labels)

    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a", [[1]]), make_candidate("b", [[2]])])
    evidence = TaskEvidence(
        task_id="t",
        test_index=0,
        candidate_set=cs,
        features_by_grid={"a": {"contradiction_count": 0.0}, "b": {"contradiction_count": 3.0}},
    )
    result = verifier.rank(evidence)
    assert result.ranked_grid_shas[0] == "a"
    assert result.verifier_name == "V2_independent_learned"


# -- V3: hybrid, unrestricted ------------------------------------------------------------


# -- confidence-semantics scenario 6: high native score, contradicted by structure -----


def test_v1_and_v2_can_disagree_when_high_score_contradicts_structure():
    """The scenario CONFIDENCE_SEMANTICS.md promises: a candidate NVARC's own
    score prefers, that structural evidence flags as wrong shape."""
    high_score_wrong_shape = [[9, 9, 9]]  # V1 prefers: huge vote count
    low_score_right_shape = [[9, 9], [9, 8]]  # V2 prefers: matches demo size relation
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("wrong_shape", high_score_wrong_shape, score_aug_mean=0.01),
            make_candidate("wrong_shape", high_score_wrong_shape, score_aug_mean=0.01),
            make_candidate("wrong_shape", high_score_wrong_shape, score_aug_mean=0.01),
            make_candidate("right_shape", low_score_right_shape, score_aug_mean=9.0),
        ],
    )
    demo_pairs = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    evidence = TaskEvidence(
        task_id="t", test_index=0, candidate_set=cs, demo_pairs=demo_pairs, test_input=[[1, 2], [3, 4]]
    )
    v1_top = NativeScoreControlVerifier().rank(evidence).ranked_grid_shas[0]
    v2_top = IndependentHeuristicVerifier().rank(evidence).ranked_grid_shas[0]
    assert v1_top == "wrong_shape"
    assert v2_top == "right_shape"
    assert v1_top != v2_top  # the disagreement structural evidence is supposed to surface


def test_v3_hybrid_accepts_score_derived_features_without_raising():
    verifier = HybridVerifier(feature_names=["original_score", "contradiction_count"])
    rows = [{"original_score": 1.0, "contradiction_count": 0.0}, {"original_score": 0.0, "contradiction_count": 3.0}] * 5
    labels = [True, False] * 5
    verifier.fit(rows, labels)  # must not raise -- V3 is deliberately unrestricted
    assert verifier.name == "V3_hybrid"
