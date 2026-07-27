import pytest

from src.gen002.candidate_union import (
    normalize_compressarc,
    normalize_gen002,
    normalize_nvarc,
    union_candidates,
)


def test_identical_grids_merge_and_preserve_both_generators():
    compressarc = normalize_compressarc(
        {
            "task_id": "task",
            "test_index": 0,
            "grid": [[1, 2]],
            "grid_sha1": "source-id-a",
            "beam_score": -1.0,
        }
    )
    gen002 = normalize_gen002(
        {
            "task_id": "task",
            "test_index": 0,
            "candidate_grid": [[1, 2]],
            "program_source": "reflect(input)",
        }
    )
    merged = union_candidates([compressarc, gen002])
    assert len(merged) == 1
    assert [p.generator_id for p in merged[0].provenance] == [
        "compressarc",
        "gen002_program_synthesis",
    ]


def test_distinct_grids_remain_distinct():
    a = normalize_compressarc(
        {"task_id": "task", "test_index": 0, "grid": [[1]]}
    )
    b = normalize_nvarc(
        {"task_id": "task", "test_index": 0, "grid": [[2]]}
    )
    assert len(union_candidates([a, b])) == 2


def test_same_grid_on_different_test_indices_does_not_merge():
    a = normalize_compressarc(
        {"task_id": "task", "test_index": 0, "grid": [[1]]}
    )
    b = normalize_nvarc(
        {"task_id": "task", "test_index": 1, "grid": [[1]]}
    )
    assert len(union_candidates([a, b])) == 2


def test_normalized_record_has_no_selection_field():
    candidate = normalize_nvarc(
        {"task_id": "task", "test_index": 0, "grid": [[1]]}
    )
    record = candidate.to_record()
    assert "rank" not in record
    assert "score" not in record
    assert "selected" not in record


def test_rejects_invalid_grid():
    with pytest.raises(ValueError):
        normalize_compressarc(
            {"task_id": "task", "test_index": 0, "grid": [[1], [2, 3]]}
        )
