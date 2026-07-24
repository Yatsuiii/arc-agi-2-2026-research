"""Tests for the RUN-001 candidate archive.

The load-bearing test is `test_logging_is_behaviour_neutral`: a mock solver runs
twice, with archiving on and off, and every observable must match including the
evolution of the RNG state. If that fails, the instrumentation is not safe to
put in front of a 12-hour GPU run.
"""

from __future__ import annotations

import gzip
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run001.archive import (  # noqa: E402
    CandidateArchive,
    grid_digest,
    read_records,
    to_grid,
)


# -- a deterministic stand-in for the solver ------------------------------------


def mock_solver(tasks, archive=None, seed=1234):
    """Mimic the notebook's shape: RNG-driven candidates, scores, ranking.

    Archiving must not perturb any of it.
    """
    rng = random.Random(seed)
    outputs = {}
    for task_index, task_id in enumerate(tasks):
        candidates = []
        for test_index in range(rng.randint(1, 2)):
            for cand_index in range(rng.randint(1, 4)):
                height, width = rng.randint(1, 4), rng.randint(1, 4)
                grid = [[rng.randint(0, 9) for _ in range(width)] for _ in range(height)]
                beam = rng.random()
                aug = [rng.random() for _ in range(8)]
                candidates.append((test_index, cand_index, grid, beam, aug))
                if archive is not None:
                    archive.record_candidate(
                        task_id=task_id,
                        task_index=task_index,
                        test_index=test_index,
                        candidate_index=cand_index,
                        grid=grid,
                        grid_sha1=grid_digest(grid),
                        beam_score=beam,
                        score_aug=aug,
                    )
        ranked = sorted(candidates, key=lambda c: (c[3], c[1]))
        outputs[task_id] = [c[2] for c in ranked[:2]]
        if archive is not None:
            for rank, cand in enumerate(ranked, start=1):
                archive.record_selection(
                    task_id=task_id,
                    test_index=cand[0],
                    grid_sha1=grid_digest(cand[2]),
                    rank_after_aggregation=rank,
                    selected=rank <= 2,
                )
            archive.flush_task(task_id, n_candidates=len(candidates))
    return outputs, rng.getstate()


# -- neutrality ------------------------------------------------------------------


def test_logging_is_behaviour_neutral(tmp_path):
    tasks = [f"task{i:03d}" for i in range(25)]

    without, rng_without = mock_solver(tasks, archive=None)
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    with_, rng_with = mock_solver(tasks, archive=archive)

    assert without == with_, "archiving changed the selected outputs"
    assert rng_without == rng_with, "archiving perturbed RNG state evolution"
    for task_id in tasks:
        assert without[task_id] == with_[task_id]


def test_archive_never_touches_global_rng(tmp_path):
    random.seed(99)
    before = random.getstate()
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="t", grid=[[1]], grid_sha1="x")
    archive.record_error("t", "solve", ValueError("boom"))
    archive.flush_task("t")
    assert random.getstate() == before


# -- persistence -----------------------------------------------------------------


def test_records_round_trip(tmp_path):
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="a", candidate_index=0, grid=[[1, 2], [3, 4]])
    archive.record_selection(task_id="a", rank_after_aggregation=1, selected=True)
    written = archive.flush_task("a", n_candidates=1)

    assert written == 2
    records = read_records(archive.candidates_path)
    assert [r["kind"] for r in records] == ["candidate", "selection"]
    assert records[0]["grid"] == [[1, 2], [3, 4]]
    assert records[1]["selected"] is True


def test_flush_per_task_creates_readable_prefix(tmp_path):
    """A run killed mid-flight must leave every completed task readable."""
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    for i in range(5):
        archive.record_candidate(task_id=f"t{i}", grid=[[i]])
        archive.flush_task(f"t{i}")

    # Simulate a hard kill during the sixth task's write.
    raw = archive.candidates_path.read_bytes()
    truncated = tmp_path / "run" / "truncated.jsonl.gz"
    truncated.write_bytes(raw + b"\x1f\x8b\x08\x00garbage-partial-member")

    recovered = read_records(truncated)
    assert len(recovered) == 5
    assert [r["task_id"] for r in recovered] == [f"t{i}" for i in range(5)]


def test_empty_flush_is_allowed(tmp_path):
    """A task that times out before producing anything still gets a summary row."""
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    assert archive.flush_task("timeout_task", hit_time_guard=True) == 0
    rows = archive.summary_path.read_text().splitlines()
    assert rows[0].startswith("task_id,")
    assert "timeout_task" in rows[1]
    assert rows[1].split(",")[1] == "0"


def test_duplicate_grids_share_a_digest(tmp_path):
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    grid = [[1, 2], [3, 4]]
    for i in range(3):
        archive.record_candidate(
            task_id="a", candidate_index=i, grid=grid, grid_sha1=grid_digest(grid)
        )
    archive.flush_task("a")
    digests = {r["grid_sha1"] for r in read_records(archive.candidates_path)}
    assert len(digests) == 1


def test_missing_metadata_is_tolerated(tmp_path):
    """Instrumentation must never crash the solver over an absent field."""
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="a")
    archive.flush_task("a")
    assert read_records(archive.candidates_path) == [{"kind": "candidate", "task_id": "a"}]


@pytest.mark.parametrize(
    "grid",
    [[[0]], [[i for i in range(30)] for _ in range(30)], [[5] * 1 for _ in range(30)], []],
)
def test_arbitrary_grid_dimensions(tmp_path, grid):
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="a", grid=grid, grid_sha1=grid_digest(grid))
    archive.flush_task("a")
    assert read_records(archive.candidates_path)[0]["grid"] == grid


def test_exception_records(tmp_path):
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_error("a", "ttt", RuntimeError("CUDA out of memory"), gpu_index=1)
    lines = archive.errors_path.read_text().splitlines()
    payload = json.loads(lines[0])
    assert payload["exception_type"] == "RuntimeError"
    assert "CUDA out of memory" in payload["message"]
    assert payload["gpu_index"] == 1


def test_errors_are_written_immediately(tmp_path):
    """Errors must not wait for a flush that may never come."""
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_error("a", "solve", ValueError("x"))
    assert archive.errors_path.exists()
    assert len(archive.errors_path.read_text().splitlines()) == 1


# -- serialization ---------------------------------------------------------------


def test_serialization_is_deterministic(tmp_path):
    def build(path):
        archive = CandidateArchive(path, shard="w0")
        archive.record_candidate(
            task_id="a", zebra=1, alpha=2, grid=[[1]], score_aug=[0.5, 0.25]
        )
        archive.flush_task("a")
        return gzip.decompress(archive.candidates_path.read_bytes())

    assert build(tmp_path / "r1") == build(tmp_path / "r2")


def test_keys_are_sorted_in_output(tmp_path):
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="a", zebra=1, alpha=2)
    archive.flush_task("a")
    line = gzip.decompress(archive.candidates_path.read_bytes()).decode().splitlines()[0]
    assert line.index('"alpha"') < line.index('"kind"') < line.index('"zebra"')


def test_numpy_like_values_are_coerced(tmp_path):
    class FakeArray:
        def __init__(self, data):
            self._data = data

        def tolist(self):
            return self._data

    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="a", grid=FakeArray([[1, 2]]), score_aug=FakeArray([0.1]))
    archive.flush_task("a")
    record = read_records(archive.candidates_path)[0]
    assert record["grid"] == [[1, 2]]
    assert record["score_aug"] == [0.1]


def test_to_grid_handles_numpy_like_and_none():
    class FakeArray:
        def tolist(self):
            return [[1, 2], [3, 4]]

    assert to_grid(FakeArray()) == [[1, 2], [3, 4]]
    assert to_grid(None) == []
    assert to_grid([[1]]) == [[1]]


def test_manifest_and_runtime_summary(tmp_path):
    archive = CandidateArchive(tmp_path / "run", shard="w0", manifest={"commit": "abc"})
    archive.record_candidate(task_id="a")
    archive.flush_task("a")
    archive.write_runtime_summary(wall_clock_seconds=12.5)

    manifest = json.loads((tmp_path / "run" / "run_manifest.w0.json").read_text())
    runtime = json.loads((tmp_path / "run" / "runtime_summary.w0.json").read_text())
    assert manifest["commit"] == "abc"
    assert runtime["tasks_flushed"] == 1
    assert runtime["records_total"] == 1
    assert runtime["wall_clock_seconds"] == 12.5


def test_no_ground_truth_field_names_leak(tmp_path):
    """Guard against ever archiving hidden answers."""
    archive = CandidateArchive(tmp_path / "run", shard="w0")
    archive.record_candidate(task_id="a", grid=[[1]], beam_score=0.5)
    archive.flush_task("a")
    blob = gzip.decompress(archive.candidates_path.read_bytes()).decode()
    for banned in ("solution", "ground_truth", "answer", "label", "correct"):
        assert banned not in blob
