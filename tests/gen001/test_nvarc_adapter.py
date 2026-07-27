import pytest

from src.gen001.nvarc_adapter import (
    CONTAMINATION_STATUS,
    FROZEN_PILOT_CONFIG,
    MOCK_CHECKPOINT_ID,
    MockGenerator,
    TaskInput,
    deduplicate_candidates,
    export_candidate_record,
)


def _task():
    return TaskInput(
        task_id="deadbeef",
        test_index=0,
        train_pairs=({"input": [[1]], "output": [[2]]},),
        test_input=[[3, 4], [5, 6]],
    )


def test_candidate_schema_has_required_fields():
    task = _task()
    raw = MockGenerator(n_candidates=1).generate(task, FROZEN_PILOT_CONFIG)[0]
    record = export_candidate_record(task, raw, FROZEN_PILOT_CONFIG, checkpoint_id="ckpt-x")
    for field in (
        "task_id",
        "test_index",
        "grid",
        "grid_sha1",
        "solver_branch",
        "checkpoint_id",
        "config_hash",
        "contamination_status",
    ):
        assert field in record


def test_contamination_label_propagates():
    task = _task()
    raw = MockGenerator(n_candidates=1).generate(task, FROZEN_PILOT_CONFIG)[0]
    record = export_candidate_record(task, raw, FROZEN_PILOT_CONFIG, checkpoint_id="ckpt-x")
    assert record["contamination_status"] == CONTAMINATION_STATUS == "SCIENTIFICALLY_CONTAMINATED"


def test_mock_checkpoint_id_never_looks_real():
    task = _task()
    raw = MockGenerator(n_candidates=1).generate(task, FROZEN_PILOT_CONFIG)[0]
    record = export_candidate_record(task, raw, FROZEN_PILOT_CONFIG, checkpoint_id=MOCK_CHECKPOINT_ID)
    assert record["checkpoint_id"] == "MOCK"
    assert record["checkpoint_id"] != FROZEN_PILOT_CONFIG.checkpoint_id


def test_invalid_grid_rejected():
    task = _task()
    with pytest.raises(ValueError):
        export_candidate_record(task, {"grid": []}, FROZEN_PILOT_CONFIG, checkpoint_id="ckpt-x")


def test_duplicate_grids_collapsed_with_multiplicity():
    task = _task()
    raw = {"grid": [[1, 2]], "beam_score": -0.1}
    record = export_candidate_record(task, raw, FROZEN_PILOT_CONFIG, checkpoint_id="ckpt-x")
    deduped = deduplicate_candidates([record, dict(record), dict(record)])
    assert len(deduped) == 1
    assert deduped[0]["multiplicity"] == 3


def test_config_hash_stable_and_sensitive_to_changes():
    h1 = FROZEN_PILOT_CONFIG.config_hash()
    h2 = FROZEN_PILOT_CONFIG.config_hash()
    assert h1 == h2
    import dataclasses

    changed = dataclasses.replace(FROZEN_PILOT_CONFIG, seed=FROZEN_PILOT_CONFIG.seed + 1)
    assert changed.config_hash() != h1


def test_generator_never_receives_ground_truth():
    task = _task()
    assert not hasattr(task, "test_output")
    assert not hasattr(task, "solution")
