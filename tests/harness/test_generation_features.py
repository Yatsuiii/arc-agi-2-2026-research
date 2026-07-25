from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.features.generation import (  # noqa: E402
    persistence_features,
    rank_and_score_stability,
    score_features,
)
from src.harness.schemas import (  # noqa: E402
    BudgetSnapshot,
    Candidate,
    CandidateSet,
    SelectionRecord,
)


def make_candidate(grid_sha1, beam_score, **kwargs):
    defaults = dict(
        task_id="t",
        test_index=0,
        grid=[[1]],
        grid_sha1=grid_sha1,
        solver_branch="nvarc",
    )
    defaults.update(kwargs)
    return Candidate(beam_score=beam_score, **defaults)


def test_score_features_normalizes_and_computes_margin():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0),
            make_candidate("b", 0.5),
            make_candidate("c", 0.0),
        ],
    )
    features = score_features(cs)
    assert features["a"]["normalized_score"] == 1.0
    assert features["c"]["normalized_score"] == 0.0
    assert features["a"]["score_margin"] == 0.5
    assert features["c"]["score_margin"] is None or features["c"]["score_margin"] < 0


def test_score_features_duplicate_count_and_rank():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 1.0), make_candidate("a", 1.0), make_candidate("b", 0.2)],
        selection=[SelectionRecord("t", 0, "a", rank=1, selected=True, algorithm="score_kgmon")],
    )
    features = score_features(cs)
    assert features["a"]["duplicate_generation_count"] == 2
    assert features["a"]["original_rank"] == 1
    assert features["b"]["original_rank"] is None


def test_score_features_single_seed_and_branch_report_none():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0, seed=1, solver_branch="nvarc"),
            make_candidate("a", 1.0, seed=1, solver_branch="nvarc"),
        ],
    )
    features = score_features(cs)
    assert features["a"]["n_seeds_producing"] is None
    assert features["a"]["n_solver_branches_producing"] is None


def test_score_features_multi_seed_is_counted():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0, seed=1),
            make_candidate("a", 1.0, seed=2),
        ],
    )
    features = score_features(cs)
    assert features["a"]["n_seeds_producing"] == 2


def test_score_features_generation_order_first_and_time():
    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("a", 1.0, generation_order=5, cumulative_task_s=50.0),
            make_candidate("a", 1.0, generation_order=2, cumulative_task_s=20.0),
        ],
    )
    features = score_features(cs)
    assert features["a"]["generation_order_first"] == 2
    assert features["a"]["time_first_appearance_s"] == 20.0


def test_score_features_empty_candidate_set():
    cs = CandidateSet(task_id="t", test_index=0)
    assert score_features(cs) == {}


def test_rank_and_score_stability_none_for_single_run():
    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("a", 1.0)])
    stability = rank_and_score_stability([cs])
    assert stability["a"]["rank_stability"] is None
    assert stability["a"]["score_stability"] is None


def test_rank_and_score_stability_across_multiple_runs():
    run1 = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 1.0)],
        selection=[SelectionRecord("t", 0, "a", rank=1, selected=True, algorithm="x")],
    )
    run2 = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("a", 0.8)],
        selection=[SelectionRecord("t", 0, "a", rank=2, selected=True, algorithm="x")],
    )
    stability = rank_and_score_stability([run1, run2])
    assert stability["a"]["rank_stability"] is not None
    assert stability["a"]["score_stability"] is not None
    # Perfectly stable grid should score higher (less negative) than a volatile one.
    run3 = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("b", 1.0)],
        selection=[SelectionRecord("t", 0, "b", rank=1, selected=True, algorithm="x")],
    )
    run4 = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[make_candidate("b", 1.0)],
        selection=[SelectionRecord("t", 0, "b", rank=1, selected=True, algorithm="x")],
    )
    stable = rank_and_score_stability([run3, run4])
    assert stable["b"]["rank_stability"] >= stability["a"]["rank_stability"]


def test_persistence_features_first_appearance_and_fraction():
    snapshots = [
        BudgetSnapshot("t", 0, budget=10.0, candidate_shas=("a",)),
        BudgetSnapshot("t", 0, budget=20.0, candidate_shas=("a", "b")),
        BudgetSnapshot("t", 0, budget=30.0, candidate_shas=("b",)),
    ]
    features = persistence_features(snapshots)
    assert features["a"]["first_appearance_snapshot_index"] == 0.0
    assert features["a"]["snapshots_present_count"] == 2.0
    assert features["a"]["persistence_fraction"] == 2 / 3
    assert features["b"]["first_appearance_snapshot_index"] == 1.0
    assert features["b"]["persistence_fraction"] == 1.0


def test_persistence_features_empty_snapshots():
    assert persistence_features([]) == {}
