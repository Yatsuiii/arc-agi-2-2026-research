import json

from src.gen001.nvarc_adapter import FROZEN_PILOT_CONFIG, MOCK_CHECKPOINT_ID, MockGenerator
from src.gen001.pilot_runner import load_manifest, run_pilot
from src.run001.archive import read_records


def test_manifest_loads_24_rows():
    rows = load_manifest()
    assert len(rows) == 24


def test_manifest_loading_deterministic():
    assert load_manifest() == load_manifest()


def test_mock_pilot_run_writes_valid_archive(tmp_path):
    summary = run_pilot(
        run_dir=tmp_path,
        generator=MockGenerator(n_candidates=2),
        config=FROZEN_PILOT_CONFIG,
        checkpoint_id=MOCK_CHECKPOINT_ID,
    )
    assert summary["n_completed"] == 24
    assert summary["hit_global_cap"] is False

    records = list(read_records(tmp_path / "candidates.pilot.jsonl.gz"))
    candidate_records = [r for r in records if r["kind"] == "candidate"]
    assert len(candidate_records) > 0
    assert all(r["checkpoint_id"] == "MOCK" for r in candidate_records)
    assert all(r["contamination_status"] == "SCIENTIFICALLY_CONTAMINATED" for r in candidate_records)


def test_resume_skips_completed_indices(tmp_path):
    run_pilot(
        run_dir=tmp_path,
        generator=MockGenerator(n_candidates=1),
        config=FROZEN_PILOT_CONFIG,
        checkpoint_id=MOCK_CHECKPOINT_ID,
    )
    second = run_pilot(
        run_dir=tmp_path,
        generator=MockGenerator(n_candidates=1),
        config=FROZEN_PILOT_CONFIG,
        checkpoint_id=MOCK_CHECKPOINT_ID,
    )
    assert second["n_run_this_call"] == 0
    assert second["n_completed"] == 24


def test_global_time_cap_stops_early(tmp_path):
    summary = run_pilot(
        run_dir=tmp_path,
        generator=MockGenerator(n_candidates=1),
        config=FROZEN_PILOT_CONFIG,
        checkpoint_id=MOCK_CHECKPOINT_ID,
        global_time_cap_s=0,
    )
    assert summary["hit_global_cap"] is True
    assert summary["n_run_this_call"] == 0


def test_survives_interruption_leaves_readable_prefix(tmp_path):
    run_pilot(
        run_dir=tmp_path,
        generator=MockGenerator(n_candidates=1),
        config=FROZEN_PILOT_CONFIG,
        checkpoint_id=MOCK_CHECKPOINT_ID,
        global_time_cap_s=0,
    )
    completed_path = tmp_path / "completed_indices.json"
    if completed_path.exists():
        assert json.loads(completed_path.read_text()) == []
    archive_path = tmp_path / "candidates.pilot.jsonl.gz"
    if archive_path.exists():
        list(read_records(archive_path))
