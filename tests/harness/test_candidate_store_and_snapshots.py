from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.candidate_store import CandidateStore, demonstration_pairs  # noqa: E402
from src.harness.candidate_store import test_inputs as get_test_inputs  # noqa: E402
from src.harness.schemas import Candidate, SelectionRecord  # noqa: E402
from src.harness.snapshots import snapshots_by_generation_order, snapshots_by_time  # noqa: E402


def make_candidate(task_id, test_index, grid_sha1, **kwargs):
    defaults = dict(grid=[[1]], solver_branch="nvarc")
    defaults.update(kwargs)
    return Candidate(task_id=task_id, test_index=test_index, grid_sha1=grid_sha1, **defaults)


# -- CandidateStore ------------------------------------------------------------------


def test_store_groups_by_task_and_test_index():
    store = CandidateStore()
    store.append_candidates(
        [make_candidate("a", 0, "x"), make_candidate("a", 1, "y"), make_candidate("b", 0, "z")]
    )
    assert len(store) == 3
    assert set(store.task_ids()) == {"a", "b"}
    assert len(store.get("a", 0).candidates) == 1
    assert store.get("missing", 0) is None


def test_store_append_selection_matches_existing_candidate_set():
    store = CandidateStore()
    store.append_candidates([make_candidate("a", 0, "x")])
    store.append_selection([SelectionRecord("a", 0, "x", rank=1, selected=True, algorithm="s")])
    cs = store.get("a", 0)
    assert len(cs.selection) == 1
    assert cs.frozen_selected() == ["x"]


def test_store_all_returns_every_set():
    store = CandidateStore()
    store.append_candidates([make_candidate("a", 0, "x"), make_candidate("b", 0, "y")])
    assert {cs.task_id for cs in store.all()} == {"a", "b"}


# -- demonstration_pairs / test_inputs ------------------------------------------------


def test_demonstration_pairs_extracts_train_grids():
    challenge = {"train": [{"input": [[1]], "output": [[2]]}], "test": [{"input": [[3]]}]}
    assert demonstration_pairs(challenge) == [([[1]], [[2]])]


def test_test_inputs_extracts_test_grids():
    challenge = {"train": [], "test": [{"input": [[3]]}, {"input": [[4]]}]}
    assert get_test_inputs(challenge) == [[[3]], [[4]]]


# -- snapshots_by_generation_order ----------------------------------------------------


def test_snapshots_by_generation_order_defaults_to_distinct_orders():
    from src.harness.schemas import CandidateSet

    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("t", 0, "a", generation_order=0),
            make_candidate("t", 0, "b", generation_order=1),
        ],
    )
    snapshots = snapshots_by_generation_order(cs)
    assert [s.budget for s in snapshots] == [0.0, 1.0]
    assert snapshots[0].candidate_shas == ("a",)
    assert snapshots[1].candidate_shas == ("a", "b")


def test_snapshots_by_generation_order_empty_without_timestamps():
    from src.harness.schemas import CandidateSet

    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("t", 0, "a")])
    assert snapshots_by_generation_order(cs) == []


def test_snapshots_by_generation_order_custom_cutoffs():
    from src.harness.schemas import CandidateSet

    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("t", 0, "a", generation_order=0),
            make_candidate("t", 0, "b", generation_order=5),
            make_candidate("t", 0, "c", generation_order=10),
        ],
    )
    snapshots = snapshots_by_generation_order(cs, cutoffs=[0, 10])
    assert len(snapshots) == 2
    assert snapshots[0].candidate_shas == ("a",)
    assert snapshots[1].candidate_shas == ("a", "b", "c")


# -- snapshots_by_time -----------------------------------------------------------------


def test_snapshots_by_time_reaches_full_set_at_final_cutoff():
    from src.harness.schemas import CandidateSet

    cs = CandidateSet(
        task_id="t",
        test_index=0,
        candidates=[
            make_candidate("t", 0, "a", cumulative_task_s=1.0),
            make_candidate("t", 0, "b", cumulative_task_s=10.0),
        ],
    )
    snapshots = snapshots_by_time(cs, n_snapshots=4)
    assert len(snapshots) == 4
    assert snapshots[-1].candidate_shas == ("a", "b")
    assert snapshots[-1].budget == pytest.approx(10.0)


def test_snapshots_by_time_empty_without_timestamps():
    from src.harness.schemas import CandidateSet

    cs = CandidateSet(task_id="t", test_index=0, candidates=[make_candidate("t", 0, "a")])
    assert snapshots_by_time(cs) == []
