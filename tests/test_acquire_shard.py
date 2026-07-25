"""Unit tests for ACQ-001's orchestration layer (`src/run002c/acquire_shard.py`),
run entirely against a stubbed process launcher -- no subprocess, no GPU, no
Kaggle. This is Phase 3's local half of the production-path validation: the
exact functions embedded verbatim into the Kaggle notebook
(`src/run002c/build_acq001_notebook.py`) are exercised here directly.
"""

from __future__ import annotations

import json

import pytest

from src.run002c import acquire_shard


def _fake_result(task_id: str, n_test: int = 1) -> dict:
    grid = [[1, 2], [3, 4]]
    return {
        "task_id": task_id,
        "n_test": n_test,
        "steps_run": 100,
        "timed_out": True,
        "elapsed_s": 1.0,
        "peak_memory_bytes": 1024,
        "device": "cuda:0",
        "attempt_1": [grid] * n_test,
        "attempt_2": [grid] * n_test,
        "candidates": [{"grid": [grid] * n_test, "accumulated_score": 1}],
    }


class FakeProc:
    def __init__(self, returncode_after_polls: int, returncode: int):
        self._polls_left = returncode_after_polls
        self._returncode_value = returncode
        self.pid = id(self)

    def poll(self):
        if self._polls_left > 0:
            self._polls_left -= 1
            return None
        return self._returncode_value

    def kill(self):
        self._returncode_value = -9


class FakeLauncher:
    """Simulates `solve_task_cli.py`: writes a valid result JSON for tasks
    scripted to succeed, writes nothing for tasks scripted to crash."""

    def __init__(self, archive_dir, outcomes: dict[str, str], never_finish: set[str] | None = None):
        self.archive_dir = archive_dir
        self.outcomes = outcomes  # task_id -> "success" | "crash"
        self.never_finish = never_finish or set()
        self.launch_calls: list[str] = []

    def launch(self, task_id: str, device: str):
        self.launch_calls.append(task_id)
        out_path = self.archive_dir / f"{task_id}.json"
        log_path = self.archive_dir / f"{task_id}.log"
        log_handle = open(log_path, "w")
        if task_id in self.never_finish:
            proc = FakeProc(returncode_after_polls=10**6, returncode=0)
            return proc, out_path, log_handle, log_path
        outcome = self.outcomes[task_id]
        if outcome == "success":
            out_path.write_text(json.dumps(_fake_result(task_id)))
            proc = FakeProc(returncode_after_polls=0, returncode=0)
        else:
            log_path.write_text("Traceback: something crashed\n")
            proc = FakeProc(returncode_after_polls=0, returncode=1)
        return proc, out_path, log_handle, log_path


def test_build_waves_splits_by_slots_per_gpu():
    waves = acquire_shard.build_waves(["t1", "t2", "t3", "t4", "t5"], slots_per_gpu=2)
    assert waves == [
        [("t1", "cuda:0"), ("t2", "cuda:0"), ("t3", "cuda:1"), ("t4", "cuda:1")],
        [("t5", "cuda:0")],
    ]


def test_run_shard_all_succeed(tmp_path):
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    task_ids = ["t1", "t2", "t3"]
    launcher = FakeLauncher(archive_dir, {t: "success" for t in task_ids})
    checkpoint_path = tmp_path / "checkpoint_state.json"

    result = acquire_shard.run_shard(task_ids, checkpoint_path, launcher, slots_per_gpu=2, poll_interval_s=0.001)

    assert result["any_aborted"] is False
    assert {t: r["status"] for t, r in result["checkpoint"].items()} == {t: "complete" for t in task_ids}
    assert launcher.launch_calls == task_ids


def test_run_shard_retries_a_crash_once_then_succeeds(tmp_path):
    """A task that crashes on attempt 1 gets one retry; the retry launcher
    is scripted to succeed, and the final checkpoint reflects success with
    attempts=2 -- confirms retry-without-duplicating-completed-work."""
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    task_ids = ["flaky", "stable"]
    checkpoint_path = tmp_path / "checkpoint_state.json"

    calls = {"flaky": 0}

    class RetryingLauncher(FakeLauncher):
        def launch(self, task_id, device):
            if task_id == "flaky":
                calls["flaky"] += 1
                outcome = "crash" if calls["flaky"] == 1 else "success"
                self.outcomes["flaky"] = outcome
            return super().launch(task_id, device)

    launcher = RetryingLauncher(archive_dir, {"stable": "success", "flaky": "crash"})
    result = acquire_shard.run_shard(task_ids, checkpoint_path, launcher, slots_per_gpu=2, poll_interval_s=0.001)

    assert result["checkpoint"]["flaky"]["status"] == "complete"
    assert result["checkpoint"]["flaky"]["attempts"] == 2
    assert result["checkpoint"]["stable"]["status"] == "complete"
    assert calls["flaky"] == 2


def test_run_shard_marks_permanent_failure_after_max_attempts(tmp_path):
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    task_ids = ["always_crashes"]
    checkpoint_path = tmp_path / "checkpoint_state.json"
    launcher = FakeLauncher(archive_dir, {"always_crashes": "crash"})

    result = acquire_shard.run_shard(task_ids, checkpoint_path, launcher, slots_per_gpu=2,
                                      max_attempts=2, poll_interval_s=0.001)

    assert result["checkpoint"]["always_crashes"]["status"] == "failed"
    assert result["checkpoint"]["always_crashes"]["attempts"] == 2


def test_checkpoint_resume_skips_completed_tasks(tmp_path):
    """Simulates a killed-and-restarted run: a checkpoint file already
    marks t1 as complete before `run_shard` is called again; t1 must not
    be relaunched, only t2."""
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    checkpoint_path = tmp_path / "checkpoint_state.json"
    checkpoint_path.write_text(json.dumps({"t1": {"status": "complete", "attempts": 1}}))

    launcher = FakeLauncher(archive_dir, {"t2": "success"})
    result = acquire_shard.run_shard(["t1", "t2"], checkpoint_path, launcher, slots_per_gpu=2, poll_interval_s=0.001)

    assert launcher.launch_calls == ["t2"]
    assert result["checkpoint"]["t1"]["status"] == "complete"
    assert result["checkpoint"]["t2"]["status"] == "complete"


def test_forced_interruption_leaves_a_readable_checkpoint(tmp_path):
    """A process that never finishes triggers the stall-abort path (using a
    near-zero time_limit_s so the test does not actually wait 20 minutes).
    The checkpoint file written by the aborted wave must still parse and
    must not claim the never-finishing task completed."""
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    checkpoint_path = tmp_path / "checkpoint_state.json"
    launcher = FakeLauncher(archive_dir, {}, never_finish={"stuck"})

    result = acquire_shard.run_shard(
        ["stuck"], checkpoint_path, launcher, slots_per_gpu=2,
        time_limit_s=-2000,  # already 1200s past "deadline" at call time
        poll_interval_s=0.001,
    )

    assert result["any_aborted"] is True
    on_disk = json.loads(checkpoint_path.read_text())
    assert on_disk["stuck"]["status"] == "failed"
    assert "stuck" not in {t for t, r in on_disk.items() if r.get("status") == "complete"}


def test_ingest_archive_produces_valid_candidate_archive(tmp_path):
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    checkpoint = {}
    for task_id in ("t1", "t2"):
        out_path = archive_dir / f"{task_id}.json"
        out_path.write_text(json.dumps(_fake_result(task_id)))
        checkpoint[task_id] = {"status": "complete", "attempts": 1, "device": "cuda:0"}
    checkpoint["t3"] = {"status": "failed", "attempts": 2, "oom": False, "last_error": "boom"}

    summary = acquire_shard.ingest_archive(["t1", "t2", "t3"], checkpoint, archive_dir, run_dir, "VALIDATION")

    assert summary == {"shard": "VALIDATION", "n_tasks": 3, "n_completed": 2, "n_failed": 1}
    from src.run001.archive import read_records

    records = read_records(run_dir / "archive" / "candidates.VALIDATION.jsonl.gz")
    task_ids_seen = {r["task_id"] for r in records}
    assert task_ids_seen == {"t1", "t2"}
    completed = json.loads((run_dir / "completed_tasks.json").read_text())
    assert completed == ["t1", "t2"]
    errors_path = run_dir / "archive" / "errors.VALIDATION.jsonl"
    assert errors_path.exists()
    error_lines = [json.loads(line) for line in errors_path.read_text().splitlines()]
    assert any(e["task_id"] == "t3" for e in error_lines)


def test_ingest_archive_flags_missing_output_file_without_crashing(tmp_path):
    """Checkpoint claims complete but the output file is absent (a
    corrupted or partially-downloaded archive) -- must be recorded as an
    error, not silently skipped or a crash."""
    archive_dir = tmp_path / "per_task"
    archive_dir.mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    checkpoint = {"ghost": {"status": "complete", "attempts": 1, "device": "cuda:0"}}

    summary = acquire_shard.ingest_archive(["ghost"], checkpoint, archive_dir, run_dir, "VALIDATION")

    assert summary["n_completed"] == 0
    errors_path = run_dir / "archive" / "errors.VALIDATION.jsonl"
    error_lines = [json.loads(line) for line in errors_path.read_text().splitlines()]
    assert any(e["task_id"] == "ghost" and e["stage"] == "archive_ingest" for e in error_lines)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
