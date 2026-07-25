"""Tests for RUN-001 post-run artifact validation, on synthetic artifacts.

No real Kaggle download or real competition data is used: `COMPETITION` is
monkeypatched to a tmp_path with a small hand-built challenges file, so these
tests do not depend on `~/arc-agi-2-2026` being present.
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run001 import validate_outputs as vo  # noqa: E402
from src.run001.archive import _SUMMARY_COLUMNS  # noqa: E402

PLACEHOLDER = [[0]]


def write_gz_jsonl(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def make_challenges(tasks: dict[str, int]) -> dict:
    """tasks: task_id -> number of test inputs."""
    return {task_id: {"test": [{} for _ in range(n)]} for task_id, n in tasks.items()}


@pytest.fixture()
def synthetic_run(tmp_path, monkeypatch):
    """A minimal, internally-consistent 2-task RUN-001 artifact directory."""
    competition_dir = tmp_path / "competition_2026" / "extracted"
    competition_dir.mkdir(parents=True)
    monkeypatch.setattr(vo, "COMPETITION", competition_dir)

    challenges = make_challenges({"task_a": 1, "task_b": 1})
    (competition_dir / "arc-agi_evaluation_challenges.json").write_text(json.dumps(challenges))

    artifact_dir = tmp_path / "artifacts" / "run001"
    artifact_dir.mkdir(parents=True)

    grid_a = [[1]]
    grid_b = [[2]]
    grid_c = [[3]]
    grid_d = [[4]]
    grid_e = [[5]]

    candidates = [
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_a,
         "grid_sha1": vo.digest(grid_a), "score_aug_mean": 0.5},
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_b,
         "grid_sha1": vo.digest(grid_b), "score_aug_mean": 0.2},
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_b,
         "grid_sha1": vo.digest(grid_b), "score_aug_mean": 0.2},
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_c,
         "grid_sha1": vo.digest(grid_c), "score_aug_mean": 0.3},
        {"kind": "candidate", "task_id": "task_b", "test_index": 0, "grid": grid_d,
         "grid_sha1": vo.digest(grid_d), "score_aug_mean": 0.1},
        {"kind": "candidate", "task_id": "task_b", "test_index": 0, "grid": grid_e,
         "grid_sha1": vo.digest(grid_e), "score_aug_mean": 0.4},
    ]
    write_gz_jsonl(artifact_dir / "candidates.jsonl.gz", candidates)

    selection = [
        {"kind": "selection", "task_id": "task_a", "test_index": 0, "grid_sha1": vo.digest(grid_b),
         "rank_after_aggregation": 1, "selected": True, "selection_algorithm": "score_kgmon"},
        {"kind": "selection", "task_id": "task_a", "test_index": 0, "grid_sha1": vo.digest(grid_c),
         "rank_after_aggregation": 2, "selected": True, "selection_algorithm": "score_kgmon"},
        {"kind": "selection", "task_id": "task_a", "test_index": 0, "grid_sha1": vo.digest(grid_a),
         "rank_after_aggregation": 3, "selected": False, "selection_algorithm": "score_kgmon"},
        {"kind": "selection", "task_id": "task_b", "test_index": 0, "grid_sha1": vo.digest(grid_d),
         "rank_after_aggregation": 1, "selected": True, "selection_algorithm": "score_kgmon"},
        {"kind": "selection", "task_id": "task_b", "test_index": 0, "grid_sha1": vo.digest(grid_e),
         "rank_after_aggregation": 2, "selected": True, "selection_algorithm": "score_kgmon"},
    ]
    write_gz_jsonl(artifact_dir / "candidates.ranking.jsonl.gz", selection)

    submission = {
        "task_a": [{"attempt_1": grid_b, "attempt_2": grid_c}],
        "task_b": [{"attempt_1": grid_d, "attempt_2": grid_e}],
    }
    (artifact_dir / "submission.json").write_text(json.dumps(submission))

    # n_records counts only "candidate" records: the real notebook writes
    # selection/ranking records separately at decode time, bypassing
    # CandidateArchive.flush_task entirely (INSTRUMENTATION_DIFF.md cell 8).
    summary_rows = [
        {"task_id": "task_a", "n_records": 4, "n_test_inputs": 1, "hit_time_guard": 0},
        {"task_id": "task_b", "n_records": 2, "n_test_inputs": 1, "hit_time_guard": 0},
    ]
    with open(artifact_dir / "task_summary.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_SUMMARY_COLUMNS)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    (artifact_dir / "run_manifest.json").write_text(json.dumps({"commit": "abc123"}))
    (artifact_dir / "errors.jsonl").write_text("")

    return artifact_dir


# -- submission schema -----------------------------------------------------------


def test_check_submission_schema_accepts_well_formed_submission():
    challenges = make_challenges({"t1": 1})
    submission = {"t1": [{"attempt_1": [[1, 2]], "attempt_2": PLACEHOLDER}]}
    stats, problems = vo.check_submission_schema(submission, challenges)
    assert problems == []
    assert stats["n_placeholder_attempts"] == 1


def test_check_submission_schema_flags_missing_and_extra_tasks():
    challenges = make_challenges({"t1": 1, "t2": 1})
    submission = {"t1": [{"attempt_1": [[1]], "attempt_2": [[1]]}], "t3": [{"attempt_1": [[1]], "attempt_2": [[1]]}]}
    _, problems = vo.check_submission_schema(submission, challenges)
    assert any("missing" in p for p in problems)
    assert any("unexpected" in p for p in problems)


def test_check_submission_schema_flags_bad_grid():
    challenges = make_challenges({"t1": 1})
    submission = {"t1": [{"attempt_1": [[1, 2], [3]], "attempt_2": PLACEHOLDER}]}
    _, problems = vo.check_submission_schema(submission, challenges)
    assert any("ragged" in p for p in problems)


def test_check_submission_schema_flags_out_of_range_colour():
    challenges = make_challenges({"t1": 1})
    submission = {"t1": [{"attempt_1": [[11]], "attempt_2": PLACEHOLDER}]}
    _, problems = vo.check_submission_schema(submission, challenges)
    assert any("colours" in p for p in problems)


# -- candidate archive structure --------------------------------------------------


def test_check_candidates_structure_accepts_well_formed_records():
    records = [
        {"kind": "candidate", "task_id": "a", "grid_sha1": "x"},
        {"kind": "selection", "task_id": "a", "grid_sha1": "x", "rank_after_aggregation": 1},
    ]
    stats, problems = vo.check_candidates_structure(records)
    assert problems == []
    assert stats["n_candidate_kind_records"] == 1
    assert stats["n_selection_kind_records"] == 1


def test_check_candidates_structure_flags_missing_fields_and_unknown_kind():
    records = [
        {"kind": "candidate"},  # missing task_id, grid_sha1
        {"kind": "mystery"},
    ]
    stats, problems = vo.check_candidates_structure(records)
    assert stats["n_malformed_records"] == 2
    assert problems


# -- task_summary reconciliation --------------------------------------------------


def test_task_summary_reconciliation_passes_when_counts_agree():
    candidates = [{"task_id": "a"}, {"task_id": "a"}, {"task_id": "b"}]
    rows = [{"task_id": "a", "n_records": "2"}, {"task_id": "b", "n_records": "1"}]
    stats, problems = vo.check_task_summary_reconciliation(candidates, rows)
    assert problems == []
    assert stats["n_tasks_corrupted_or_truncated"] == 0


def test_task_summary_reconciliation_flags_truncated_task():
    candidates = [{"task_id": "a"}]  # summary claims 3, only 1 present -> truncated
    rows = [{"task_id": "a", "n_records": "3"}]
    stats, problems = vo.check_task_summary_reconciliation(candidates, rows)
    assert stats["n_tasks_corrupted_or_truncated"] == 1
    assert problems


# -- selected-vs-submission -------------------------------------------------------


def test_selected_matches_submission_when_consistent():
    grid = [[1]]
    records = [
        {"kind": "selection", "task_id": "t", "test_index": 0, "grid_sha1": vo.digest(grid), "selected": True},
    ]
    submission = {"t": [{"attempt_1": grid, "attempt_2": PLACEHOLDER}]}
    _, notes = vo.check_selected_matches_submission(records, submission)
    assert notes == []


def test_selected_matches_submission_flags_grid_not_in_selected_set():
    selected_grid = [[1]]
    submitted_grid = [[9]]
    records = [
        {"kind": "selection", "task_id": "t", "test_index": 0, "grid_sha1": vo.digest(selected_grid), "selected": True},
    ]
    submission = {"t": [{"attempt_1": submitted_grid, "attempt_2": PLACEHOLDER}]}
    _, notes = vo.check_selected_matches_submission(records, submission)
    assert notes and "1 of 1" in notes[0]


# -- leakage -----------------------------------------------------------------------


def test_no_leakage_passes_clean_archive():
    stats, problems = vo.check_no_leakage([{"kind": "candidate", "grid": [[1]]}])
    assert problems == []
    assert stats["archive_has_answer_fields"] == 0


def test_no_leakage_flags_answer_field():
    stats, problems = vo.check_no_leakage([{"kind": "candidate", "ground_truth": [[1]]}])
    assert stats["archive_has_answer_fields"] == 1
    assert problems


# -- classification -----------------------------------------------------------------


def test_classify_run_complete():
    report = {"problems": [], "n_tasks_expected": 2, "n_tasks_with_candidates": 2, "n_hit_time_guard": 0}
    assert vo.classify_run(report, "COMPLETE") == "COMPLETE"


def test_classify_run_partial_without_time_guard():
    report = {"problems": [], "n_tasks_expected": 10, "n_tasks_with_candidates": 4, "n_hit_time_guard": 0}
    assert vo.classify_run(report, "COMPLETE") == "PARTIAL"


def test_classify_run_timed_out_when_guard_fired():
    report = {"problems": [], "n_tasks_expected": 10, "n_tasks_with_candidates": 4, "n_hit_time_guard": 3}
    assert vo.classify_run(report, "COMPLETE") == "TIMED_OUT"


def test_classify_run_failed_on_kernel_error():
    report = {"problems": [], "n_tasks_expected": 10, "n_tasks_with_candidates": 10, "n_hit_time_guard": 0}
    assert vo.classify_run(report, "ERROR") == "FAILED"


def test_classify_run_failed_on_hard_problems():
    report = {"problems": ["something is wrong"], "n_tasks_expected": 10, "n_tasks_with_candidates": 10, "n_hit_time_guard": 0}
    assert vo.classify_run(report, "COMPLETE") == "FAILED"


# -- end-to-end validate() ----------------------------------------------------------


def test_validate_end_to_end_on_consistent_synthetic_run(synthetic_run):
    report = vo.validate(synthetic_run, kernel_status="COMPLETE")
    assert report["ok"], report["problems"]
    assert report["classification"] == "COMPLETE"
    assert report["n_tasks_with_candidates"] == 2
    assert report["n_tasks_corrupted_or_truncated"] == 0
    assert report["n_selected_mismatches"] == 0
    assert report["archive_has_answer_fields"] == 0


def test_validate_reports_missing_submission(tmp_path, monkeypatch):
    competition_dir = tmp_path / "competition_2026" / "extracted"
    competition_dir.mkdir(parents=True)
    monkeypatch.setattr(vo, "COMPETITION", competition_dir)
    (competition_dir / "arc-agi_evaluation_challenges.json").write_text(json.dumps(make_challenges({"t": 1})))

    empty_dir = tmp_path / "artifacts" / "run001"
    empty_dir.mkdir(parents=True)
    report = vo.validate(empty_dir, kernel_status="COMPLETE")
    assert not report["ok"]
    assert "submission.json missing" in report["problems"]
    assert report["classification"] == "FAILED"


def test_validate_detects_truncated_task(synthetic_run):
    # Corrupt the summary to claim more records than the archive actually has.
    rows = (synthetic_run / "task_summary.csv").read_text().splitlines()
    rows[1] = rows[1].replace(",4,", ",99,")
    (synthetic_run / "task_summary.csv").write_text("\n".join(rows) + "\n")

    report = vo.validate(synthetic_run, kernel_status="COMPLETE")
    assert not report["ok"]
    assert report["n_tasks_corrupted_or_truncated"] == 1
    assert report["classification"] == "FAILED"
