from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.adapters import trm  # noqa: E402
from src.harness.adapters.nvarc import load_into_store  # noqa: E402


def write_gz_jsonl(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


@pytest.fixture()
def archive_dir(tmp_path):
    candidates = [
        {
            "kind": "candidate", "task_id": "t1", "test_index": 0, "grid": [[1]],
            "grid_sha1": "aaa", "beam_score": 0.5, "score_aug": [0.1, 0.2],
            "score_aug_mean": 0.15, "ttt_seed": 1, "augmentation_key": "aug1",
            "generation_order": 0, "cumulative_task_s": 1.0, "solver_branch": "nvarc_architects_qwen3_4b",
        },
        {"kind": "candidate", "task_id": "t1", "test_index": 0},  # malformed: no grid_sha1
    ]
    write_gz_jsonl(tmp_path / "candidates.jsonl.gz", candidates)
    selection = [
        {"kind": "selection", "task_id": "t1", "test_index": 0, "grid_sha1": "aaa",
         "rank_after_aggregation": 1, "selected": True, "selection_algorithm": "score_kgmon"},
        {"kind": "selection", "task_id": "t1", "test_index": 0},  # malformed: no grid_sha1/rank
    ]
    write_gz_jsonl(tmp_path / "candidates.ranking.jsonl.gz", selection)
    return tmp_path


def test_load_into_store_parses_well_formed_records(archive_dir):
    store = load_into_store(archive_dir)
    cs = store.get("t1", 0)
    assert cs is not None
    assert len(cs.candidates) == 1
    candidate = cs.candidates[0]
    assert candidate.grid_sha1 == "aaa"
    assert candidate.beam_score == 0.5
    assert candidate.score_aug == (0.1, 0.2)
    assert candidate.seed == 1
    assert candidate.augmentation_key == "aug1"
    assert candidate.generation_order == 0


def test_load_into_store_skips_malformed_records(archive_dir):
    store = load_into_store(archive_dir)
    cs = store.get("t1", 0)
    # Only one well-formed candidate and one well-formed selection record made it in.
    assert len(cs.candidates) == 1
    assert len(cs.selection) == 1


def test_load_into_store_preserves_raw_fields(archive_dir):
    store = load_into_store(archive_dir)
    candidate = store.get("t1", 0).candidates[0]
    assert candidate.raw["task_id"] == "t1"


def test_load_into_store_reuses_an_existing_store(archive_dir):
    from src.harness.candidate_store import CandidateStore

    store = CandidateStore()
    returned = load_into_store(archive_dir, store=store)
    assert returned is store


def test_load_into_store_handles_missing_archive_files(tmp_path):
    store = load_into_store(tmp_path)
    assert len(store) == 0


def test_trm_adapter_raises_not_implemented(tmp_path):
    assert trm.TRM_AVAILABLE is False
    with pytest.raises(NotImplementedError):
        trm.load_into_store(tmp_path)
