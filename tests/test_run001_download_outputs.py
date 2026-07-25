"""Tests for RUN-001 output ingestion.

No real Kaggle CLI is invoked: `subprocess.run` is monkeypatched throughout,
so these tests never touch the network or the live kernel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run001 import download_outputs as do  # noqa: E402


class _FakeCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.returncode = 0


# -- kernel_status -----------------------------------------------------------------


def test_kernel_status_parses_running(monkeypatch):
    def fake_run(cmd, capture_output, text, check):
        return _FakeCompletedProcess(
            'redlotusthepotus/run001-nvarc-t4x2-baseline has status "KernelWorkerStatus.RUNNING"\n'
        )

    monkeypatch.setattr(do.subprocess, "run", fake_run)
    assert do.kernel_status("redlotusthepotus/run001-nvarc-t4x2-baseline") == "RUNNING"


def test_kernel_status_parses_complete(monkeypatch):
    def fake_run(cmd, capture_output, text, check):
        return _FakeCompletedProcess('some/kernel has status "KernelWorkerStatus.COMPLETE"\n')

    monkeypatch.setattr(do.subprocess, "run", fake_run)
    assert do.kernel_status("some/kernel") == "COMPLETE"


def test_kernel_status_raises_on_unrecognised_output(monkeypatch):
    def fake_run(cmd, capture_output, text, check):
        return _FakeCompletedProcess("nonsense output\n")

    monkeypatch.setattr(do.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        do.kernel_status("some/kernel")


def test_kernel_status_uses_the_given_kaggle_binary(monkeypatch):
    seen = {}

    def fake_run(cmd, capture_output, text, check):
        seen["cmd"] = cmd
        return _FakeCompletedProcess('k has status "KernelWorkerStatus.COMPLETE"\n')

    monkeypatch.setattr(do.subprocess, "run", fake_run)
    do.kernel_status("some/kernel", kaggle_bin="/opt/kaggle-venv/bin/kaggle")
    assert seen["cmd"][0] == "/opt/kaggle-venv/bin/kaggle"


# -- checksums -----------------------------------------------------------------------


def test_checksum_files_covers_every_file_and_excludes_bookkeeping(tmp_path):
    (tmp_path / "submission.json").write_text('{"a": 1}')
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "candidates.jsonl.gz").write_bytes(b"binary-content")
    (tmp_path / "checksums.json").write_text("{}")  # must not checksum itself
    (tmp_path / "ingestion_manifest.json").write_text("{}")

    checksums = do.checksum_files(tmp_path)

    assert set(checksums) == {"submission.json", "nested/candidates.jsonl.gz"}
    assert all(len(v) == 64 for v in checksums.values())  # sha256 hex digest length


def test_checksum_files_is_deterministic(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    first = do.checksum_files(tmp_path)
    second = do.checksum_files(tmp_path)
    assert first == second


def test_write_checksums_round_trips(tmp_path):
    checksums = {"submission.json": "a" * 64}
    path = do.write_checksums(tmp_path, checksums)
    assert json.loads(path.read_text()) == checksums


# -- ingestion manifest ---------------------------------------------------------------


def test_update_ingestion_manifest_creates_and_merges(tmp_path):
    first = do.update_ingestion_manifest(tmp_path, kernel_status="RUNNING")
    assert json.loads(first.read_text())["kernel_status"] == "RUNNING"

    second = do.update_ingestion_manifest(tmp_path, kernel_status="COMPLETE", classification="COMPLETE")
    payload = json.loads(second.read_text())
    assert payload["kernel_status"] == "COMPLETE"
    assert payload["classification"] == "COMPLETE"
    assert "ingested_at" in payload


# -- ingest() orchestration and the running-kernel guard -------------------------------


def test_ingest_refuses_to_download_a_running_kernel(tmp_path, monkeypatch):
    monkeypatch.setattr(
        do, "kernel_status", lambda kernel_ref, kaggle_bin="kaggle": "RUNNING"
    )
    called = {"download": False}
    monkeypatch.setattr(
        do, "download_outputs", lambda *a, **k: called.__setitem__("download", True)
    )

    with pytest.raises(do.KernelNotFinished):
        do.ingest(dest_dir=tmp_path)
    assert called["download"] is False


def test_ingest_downloads_when_forced_despite_running_status(tmp_path, monkeypatch):
    monkeypatch.setattr(
        do, "kernel_status", lambda kernel_ref, kaggle_bin="kaggle": "RUNNING"
    )

    def fake_download(kernel_ref, dest_dir, kaggle_bin="kaggle"):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "submission.json").write_text("{}")

    monkeypatch.setattr(do, "download_outputs", fake_download)
    monkeypatch.setattr(
        do, "validate", lambda dest_dir, kernel_status=None: {
            "ok": False, "problems": ["submission.json missing"], "classification": "PARTIAL"
        }
    )

    result = do.ingest(dest_dir=tmp_path, force=True)
    assert result["kernel_status"] == "RUNNING"
    assert result["classification"] == "PARTIAL"
    assert (tmp_path / "ingestion_manifest.json").exists()


def test_ingest_downloads_and_writes_checksums_and_manifest_on_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(
        do, "kernel_status", lambda kernel_ref, kaggle_bin="kaggle": "COMPLETE"
    )

    def fake_download(kernel_ref, dest_dir, kaggle_bin="kaggle"):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "submission.json").write_text('{"t": []}')

    monkeypatch.setattr(do, "download_outputs", fake_download)
    monkeypatch.setattr(
        do, "validate", lambda dest_dir, kernel_status=None: {
            "ok": True, "problems": [], "classification": "COMPLETE"
        }
    )

    result = do.ingest(dest_dir=tmp_path)

    assert result["kernel_status"] == "COMPLETE"
    assert result["classification"] == "COMPLETE"
    checksums = json.loads((tmp_path / "checksums.json").read_text())
    assert "submission.json" in checksums
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["validation_ok"] is True
    assert manifest["n_files_downloaded"] == len(checksums)
