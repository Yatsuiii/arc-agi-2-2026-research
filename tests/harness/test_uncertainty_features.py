from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.features.uncertainty import (  # noqa: E402
    augmentation_disagreement,
    duplicate_fraction,
    effective_candidate_count,
    growth_rate,
    near_tie_count,
    rank_volatility,
    score_distribution_entropy,
    seed_disagreement,
    solver_disagreement,
    time_since_last_new_unique,
    top_margin,
    verifier_disagreement,
)
from src.harness.schemas import BudgetSnapshot, Candidate, CandidateSet  # noqa: E402


def make_candidate(grid_sha1, beam_score=None, **kwargs):
    defaults = dict(task_id="t", test_index=0, grid=[[1]], grid_sha1=grid_sha1, solver_branch="nvarc")
    defaults.update(kwargs)
    return Candidate(beam_score=beam_score, **defaults)


def test_score_distribution_entropy_none_below_two_grids():
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a", 1.0)])
    assert score_distribution_entropy(cs) is None


def test_score_distribution_entropy_zero_when_one_grid_dominates():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 100.0), make_candidate("b", -100.0)],
    )
    entropy = score_distribution_entropy(cs)
    assert entropy == pytest.approx(0.0, abs=1e-6)


def test_score_distribution_entropy_higher_for_tied_scores():
    tied = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 1.0), make_candidate("b", 1.0)],
    )
    skewed = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 10.0), make_candidate("b", 0.0)],
    )
    assert score_distribution_entropy(tied) > score_distribution_entropy(skewed)


def test_effective_candidate_count_matches_exp_entropy():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 1.0), make_candidate("b", 1.0)],
    )
    assert effective_candidate_count(cs) == pytest.approx(2.0)


def test_top_margin_none_below_two_grids():
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a", 1.0)])
    assert top_margin(cs) is None


def test_top_margin_computed():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 0.9), make_candidate("b", 0.4)],
    )
    assert top_margin(cs) == pytest.approx(0.5)


def test_near_tie_count():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 1.0), make_candidate("b", 1.0), make_candidate("c", 0.0)],
    )
    assert near_tie_count(cs) == 2.0


def test_augmentation_disagreement_none_below_two_augmentations():
    cs = CandidateSet(
        task_id="t", test_index=0, candidates=[make_candidate("a", 1.0, augmentation_key="aug1")]
    )
    assert augmentation_disagreement(cs) is None


def test_augmentation_disagreement_positive_when_augmentations_diverge():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0, augmentation_key="aug1"),
            make_candidate("b", -1.0, augmentation_key="aug2"),
        ],
    )
    assert augmentation_disagreement(cs) > 0


def test_seed_and_solver_disagreement_none_for_run001_shape():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0, seed=1, solver_branch="nvarc"),
            make_candidate("b", 1.0, seed=1, solver_branch="nvarc"),
        ],
    )
    assert seed_disagreement(cs) is None
    assert solver_disagreement(cs) is None


def test_seed_and_solver_disagreement_positive_when_multiple_present():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0, seed=1, solver_branch="nvarc"),
            make_candidate("b", 1.0, seed=2, solver_branch="trm"),
        ],
    )
    assert seed_disagreement(cs) == 2.0
    assert solver_disagreement(cs) == 2.0


def test_duplicate_fraction():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 1.0), make_candidate("a", 1.0), make_candidate("b", 1.0)],
    )
    assert duplicate_fraction(cs) == pytest.approx(1 / 3)


def test_duplicate_fraction_none_for_empty_set():
    cs = CandidateSet(task_id="t", test_index=0)
    assert duplicate_fraction(cs) is None


def test_time_since_last_new_unique():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", generation_order=0, cumulative_task_s=10.0),
            make_candidate("b", generation_order=1, cumulative_task_s=20.0),
            make_candidate("b", generation_order=2, cumulative_task_s=30.0),  # duplicate, not new
        ],
    )
    assert time_since_last_new_unique(cs) == pytest.approx(10.0)  # 30 - 20


def test_growth_rate_none_below_two_snapshots():
    assert growth_rate([BudgetSnapshot("t", 0, budget=1.0, candidate_shas=("a",))]) is None


def test_growth_rate_computed():
    snapshots = [
        BudgetSnapshot("t", 0, budget=0.0, candidate_shas=()),
        BudgetSnapshot("t", 0, budget=10.0, candidate_shas=("a", "b")),
    ]
    assert growth_rate(snapshots) == pytest.approx(0.2)  # 2 new grids / 10s


def test_rank_volatility_counts_leader_changes():
    assert rank_volatility([None, None], ["a", "b"]) == 1.0
    assert rank_volatility([None, None], ["a", "a"]) == 0.0
    assert rank_volatility([None, None], ["a"]) is None


def test_verifier_disagreement_none_below_two_rankings():
    assert verifier_disagreement([["a", "b"]]) is None


def test_verifier_disagreement_full_when_all_differ():
    assert verifier_disagreement([["a"], ["b"], ["c"]]) == 1.0


def test_verifier_disagreement_zero_when_all_agree():
    assert verifier_disagreement([["a", "b"], ["a", "c"]]) == 0.0
