"""Tests for EXP002's candidate headroom analysis, on synthetic RUN-001 archives.

`COMPETITION` is monkeypatched to a tmp_path throughout, so these tests never
read the real competition data and can freely exercise the "no solutions file
available" path (the actual case for the ARC-AGI-2 `test` split).
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis import candidate_headroom as ch  # noqa: E402
from src.run001.archive import grid_digest  # noqa: E402


def write_gz_jsonl(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


@pytest.fixture()
def synthetic_archive(tmp_path, monkeypatch):
    """Two tasks, one test index each: one selection failure, one clean solve."""
    competition_dir = tmp_path / "competition_2026" / "extracted"
    competition_dir.mkdir(parents=True)
    monkeypatch.setattr(ch, "COMPETITION", competition_dir)

    grid_a = [[1]]  # correct for task_a, generated but not selected
    grid_b = [[2]]  # selected for task_a (wrong)
    grid_c = [[3]]  # also selected for task_a (wrong), rank 2
    grid_d = [[4]]  # correct for task_b, generated and selected
    grid_e = [[5]]  # selected for task_b rank 2 (wrong but doesn't matter)

    solutions = {"task_a": [grid_a], "task_b": [grid_d]}
    (competition_dir / "arc-agi_evaluation_solutions.json").write_text(json.dumps(solutions))

    artifact_dir = tmp_path / "artifacts" / "run001"
    artifact_dir.mkdir(parents=True)

    candidates = [
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_a,
         "grid_sha1": grid_digest(grid_a), "score_aug_mean": 0.5, "score_aug": [0.5] * 8},
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_b,
         "grid_sha1": grid_digest(grid_b), "score_aug_mean": 0.2, "score_aug": [0.2] * 8},
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_b,
         "grid_sha1": grid_digest(grid_b), "score_aug_mean": 0.2, "score_aug": [0.2] * 8},
        {"kind": "candidate", "task_id": "task_a", "test_index": 0, "grid": grid_c,
         "grid_sha1": grid_digest(grid_c), "score_aug_mean": 0.3, "score_aug": [0.1, 0.5] * 4},
        {"kind": "candidate", "task_id": "task_b", "test_index": 0, "grid": grid_d,
         "grid_sha1": grid_digest(grid_d), "score_aug_mean": 0.1, "score_aug": [0.1] * 8},
        {"kind": "candidate", "task_id": "task_b", "test_index": 0, "grid": grid_e,
         "grid_sha1": grid_digest(grid_e), "score_aug_mean": 0.4, "score_aug": [0.4] * 8},
    ]
    write_gz_jsonl(artifact_dir / "candidates.jsonl.gz", candidates)

    selection = [
        {"kind": "selection", "task_id": "task_a", "test_index": 0, "grid_sha1": grid_digest(grid_b),
         "rank_after_aggregation": 1, "selected": True},
        {"kind": "selection", "task_id": "task_a", "test_index": 0, "grid_sha1": grid_digest(grid_c),
         "rank_after_aggregation": 2, "selected": True},
        {"kind": "selection", "task_id": "task_a", "test_index": 0, "grid_sha1": grid_digest(grid_a),
         "rank_after_aggregation": 3, "selected": False},
        {"kind": "selection", "task_id": "task_b", "test_index": 0, "grid_sha1": grid_digest(grid_d),
         "rank_after_aggregation": 1, "selected": True},
        {"kind": "selection", "task_id": "task_b", "test_index": 0, "grid_sha1": grid_digest(grid_e),
         "rank_after_aggregation": 2, "selected": True},
    ]
    write_gz_jsonl(artifact_dir / "candidates.ranking.jsonl.gz", selection)

    with open(artifact_dir / "task_summary.csv", "w") as handle:
        handle.write("task_id,n_records,n_test_inputs,n_candidates,n_unique_grids,ttt_seconds,solve_seconds,hit_time_guard,gpu_index,peak_mem_train_mib,peak_mem_infer_mib\n")
        handle.write("task_a,4,1,4,3,,12.5,0,0,,\n")
        handle.write("task_b,2,1,2,2,,3.0,0,1,,\n")

    return artifact_dir


# -- load_solutions: must not require unavailable ground truth ---------------------


def test_load_solutions_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(ch, "COMPETITION", tmp_path)
    assert ch.load_solutions("test") is None


def test_load_solutions_reads_present_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ch, "COMPETITION", tmp_path)
    (tmp_path / "arc-agi_training_solutions.json").write_text(json.dumps({"t": [[[1]]]}))
    assert ch.load_solutions("training") == {"t": [[[1]]]}


# -- augmentation_agreement ---------------------------------------------------------


def test_augmentation_agreement_is_high_for_constant_scores():
    assert ch.augmentation_agreement({"score_aug": [0.3] * 8}) == pytest.approx(1.0)


def test_augmentation_agreement_is_lower_for_spread_scores():
    tight = ch.augmentation_agreement({"score_aug": [0.5] * 8})
    spread = ch.augmentation_agreement({"score_aug": [0.0, 1.0, 0.0, 1.0]})
    assert spread < tight


def test_augmentation_agreement_none_when_insufficient_scores():
    assert ch.augmentation_agreement({"score_aug": [0.5]}) is None
    assert ch.augmentation_agreement({}) is None


# -- reconstruct_score_kgmon ---------------------------------------------------------


def test_reconstruct_score_kgmon_matches_votes_minus_mean():
    group = [{"score_aug_mean": 0.2}, {"score_aug_mean": 0.2}]
    assert ch.reconstruct_score_kgmon(group) == pytest.approx(2 - 0.2)


def test_reconstruct_score_kgmon_none_without_scores():
    assert ch.reconstruct_score_kgmon([{}]) is None


# -- join_candidates_and_selection ---------------------------------------------------


def test_join_groups_by_task_and_test_index():
    candidates = [{"kind": "candidate", "task_id": "a", "test_index": 0}]
    selection = [{"kind": "selection", "task_id": "a", "test_index": 0, "grid_sha1": "x"}]
    joined = ch.join_candidates_and_selection(candidates, selection)
    assert list(joined) == [("a", 0)]
    assert len(joined[("a", 0)]["candidates"]) == 1
    assert "x" in joined[("a", 0)]["selection"]


# -- analyse_run: ground truth available ---------------------------------------------


def test_analyse_run_computes_headroom_with_ground_truth(synthetic_archive):
    report = ch.analyse_run(synthetic_archive, "evaluation")

    assert report["ground_truth_available"] is True
    assert report["n_test_indices"] == 2
    assert report["oracle_candidate_accuracy"] == pytest.approx(1.0)  # both generated
    assert report["selected_accuracy"] == pytest.approx(0.5)  # only task_b selected correctly
    assert report["selection_headroom"] == pytest.approx(0.5)

    task_a = report["per_test_index"]["task_a:0"]
    assert task_a["correct_candidate_generated"] is True
    assert task_a["correct_candidate_selected"] is False
    assert task_a["rank_of_correct_candidate"] == 3
    assert task_a["n_candidates"] == 4
    assert task_a["n_unique_grids"] == 3
    assert task_a["duplicate_candidate_frequency"] == pytest.approx(0.25)
    # selected (grid_b, votes=2, mean=0.2 -> score 1.8) outscores correct (grid_a, votes=1, mean=0.5 -> score 0.5)
    assert task_a["score_margin_correct_vs_selected"] == pytest.approx(1.8 - 0.5)

    task_b = report["per_test_index"]["task_b:0"]
    assert task_b["correct_candidate_generated"] is True
    assert task_b["correct_candidate_selected"] is True
    assert task_b["rank_of_correct_candidate"] == 1
    assert task_b["score_margin_correct_vs_selected"] == pytest.approx(0.0)


def test_analyse_run_includes_task_runtime_from_summary(synthetic_archive):
    report = ch.analyse_run(synthetic_archive, "evaluation")
    assert report["per_task_runtime"]["task_a"]["solve_seconds"] == pytest.approx(12.5)
    assert report["per_task_runtime"]["task_b"]["hit_time_guard"] is False


# -- analyse_run: no ground truth available -------------------------------------------


def test_analyse_run_omits_truth_dependent_fields_when_solutions_missing(tmp_path, monkeypatch):
    competition_dir = tmp_path / "competition_2026" / "extracted"
    competition_dir.mkdir(parents=True)
    monkeypatch.setattr(ch, "COMPETITION", competition_dir)

    artifact_dir = tmp_path / "artifacts" / "run001"
    artifact_dir.mkdir(parents=True)
    grid = [[7]]
    write_gz_jsonl(
        artifact_dir / "candidates.jsonl.gz",
        [{"kind": "candidate", "task_id": "t", "test_index": 0, "grid": grid,
          "grid_sha1": grid_digest(grid), "score_aug_mean": 0.1}],
    )
    write_gz_jsonl(
        artifact_dir / "candidates.ranking.jsonl.gz",
        [{"kind": "selection", "task_id": "t", "test_index": 0, "grid_sha1": grid_digest(grid),
          "rank_after_aggregation": 1, "selected": True}],
    )

    report = ch.analyse_run(artifact_dir, "test")

    assert report["ground_truth_available"] is False
    assert "oracle_candidate_accuracy" not in report
    assert "selection_headroom" not in report
    entry = report["per_test_index"]["t:0"]
    assert "correct_candidate_generated" not in entry
    assert entry["n_candidates"] == 1  # truth-independent fields are still computed
