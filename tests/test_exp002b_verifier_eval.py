"""Tests for EXP002-B's bootstrap CI, selective-accuracy curve, and empirical prior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis.exp002b_verifier_eval import (  # noqa: E402
    bootstrap_ci,
    measure_singleton_prior,
    selective_accuracy_curve,
)
from src.harness.schemas import Candidate, CandidateSet, TaskEvidence  # noqa: E402
from src.run001.archive import grid_digest  # noqa: E402


def test_bootstrap_ci_empty_is_none():
    assert bootstrap_ci([]) is None


def test_bootstrap_ci_all_true_has_point_one_and_tight_interval():
    result = bootstrap_ci([True] * 30, n_bootstrap=200)
    assert result["point"] == 1.0
    assert result["ci_low"] == pytest.approx(1.0)
    assert result["ci_high"] == pytest.approx(1.0)


def test_bootstrap_ci_is_deterministic_for_fixed_seed():
    data = [True, False, True, True, False]
    a = bootstrap_ci(data, n_bootstrap=500, seed=1)
    b = bootstrap_ci(data, n_bootstrap=500, seed=1)
    assert a == b


def test_bootstrap_ci_interval_widens_with_more_variance():
    tight = bootstrap_ci([True] * 100, n_bootstrap=500)
    wide = bootstrap_ci([True, False] * 50, n_bootstrap=500)
    assert (tight["ci_high"] - tight["ci_low"]) < (wide["ci_high"] - wide["ci_low"])


def test_selective_accuracy_curve_perfect_confidence_ordering():
    # All hits are the most confident; misses are least confident.
    hits = [True, True, False, False]
    confidences = [0.9, 0.8, 0.2, 0.1]
    curve = selective_accuracy_curve(hits, confidences)
    assert curve[0.2]["accuracy"] == 1.0  # top 20% (1 example) is a hit
    assert curve[1.0]["accuracy"] == 0.5  # everyone: 2/4


def test_selective_accuracy_curve_covers_at_least_one_example():
    curve = selective_accuracy_curve([True], [0.5])
    assert curve[0.2]["n"] == 1


def make_candidate(task_id, test_index, grid):
    return Candidate(
        task_id=task_id, test_index=test_index, grid=grid, grid_sha1=grid_digest(grid), solver_branch="x"
    )


def test_measure_singleton_prior_computed_only_from_singleton_sets():
    cs_singleton_correct = CandidateSet(
        task_id="a", test_index=0, candidates=[make_candidate("a", 0, [[1]])]
    )
    cs_singleton_wrong = CandidateSet(
        task_id="b", test_index=0, candidates=[make_candidate("b", 0, [[2]])]
    )
    cs_multi = CandidateSet(
        task_id="c",
        test_index=0,
        candidates=[make_candidate("c", 0, [[3]]), make_candidate("c", 0, [[4]])],
    )
    evidence_map = {
        ("a", 0): TaskEvidence(task_id="a", test_index=0, candidate_set=cs_singleton_correct),
        ("b", 0): TaskEvidence(task_id="b", test_index=0, candidate_set=cs_singleton_wrong),
        ("c", 0): TaskEvidence(task_id="c", test_index=0, candidate_set=cs_multi),
    }
    solutions = {"a": [[[1]]], "b": [[[9]]], "c": [[[3]]]}  # c is multi-candidate, excluded from the prior
    prior = measure_singleton_prior(evidence_map, list(evidence_map), solutions)
    assert prior == pytest.approx(0.5)  # 1 correct out of 2 singleton sets


def test_measure_singleton_prior_default_when_no_singletons_present():
    from src.harness.verifier.base import DEFAULT_SINGLETON_PRIOR

    cs_multi = CandidateSet(
        task_id="c",
        test_index=0,
        candidates=[make_candidate("c", 0, [[3]]), make_candidate("c", 0, [[4]])],
    )
    evidence_map = {("c", 0): TaskEvidence(task_id="c", test_index=0, candidate_set=cs_multi)}
    prior = measure_singleton_prior(evidence_map, list(evidence_map), {"c": [[[3]]]})
    assert prior == DEFAULT_SINGLETON_PRIOR
