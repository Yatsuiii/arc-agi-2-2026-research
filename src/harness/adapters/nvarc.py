"""Adapter: RUN-001's archived NVARC records -> harness `Candidate`/`SelectionRecord`.

This is the one module allowed to know that a "candidate" record has a
`beam_score` field, that a "selection" record has `rank_after_aggregation`,
or that `test_index` arrives as an int rather than parsed out of `base_key`.
Everything downstream (`features/`, `verifier/`) never sees those names.
"""

from __future__ import annotations

from pathlib import Path

from src.harness.candidate_store import CandidateStore
from src.harness.schemas import Candidate, SelectionRecord
from src.run001.archive import read_records

SOLVER_BRANCH_DEFAULT = "nvarc_architects_qwen3_4b"


def _to_candidate(record: dict) -> Candidate | None:
    task_id = record.get("task_id")
    test_index = record.get("test_index")
    grid_sha1 = record.get("grid_sha1")
    if task_id is None or test_index is None or grid_sha1 is None:
        return None  # malformed record; validate_outputs.py is where this gets flagged, not here
    score_aug = record.get("score_aug")
    return Candidate(
        task_id=task_id,
        test_index=test_index,
        grid=record.get("grid", []),
        grid_sha1=grid_sha1,
        solver_branch=record.get("solver_branch", SOLVER_BRANCH_DEFAULT),
        seed=record.get("ttt_seed"),
        augmentation_key=record.get("augmentation_key"),
        beam_score=record.get("beam_score"),
        score_aug=tuple(score_aug) if score_aug else (),
        score_aug_mean=record.get("score_aug_mean"),
        generation_order=record.get("generation_order"),
        cumulative_task_s=record.get("cumulative_task_s"),
        candidate_latency_s=record.get("candidate_latency_s"),
        raw=record,
    )


def _to_selection(record: dict) -> SelectionRecord | None:
    task_id = record.get("task_id")
    test_index = record.get("test_index")
    grid_sha1 = record.get("grid_sha1")
    rank = record.get("rank_after_aggregation")
    if None in (task_id, test_index, grid_sha1, rank):
        return None
    return SelectionRecord(
        task_id=task_id,
        test_index=test_index,
        grid_sha1=grid_sha1,
        rank=rank,
        selected=bool(record.get("selected", False)),
        algorithm=record.get("selection_algorithm", "score_kgmon"),
    )


def load_into_store(artifact_dir: Path, store: CandidateStore | None = None) -> CandidateStore:
    """Read `candidates.jsonl.gz` and `candidates.ranking.jsonl.gz` from a RUN-001
    artifact directory into a `CandidateStore`.

    Tolerates a truncated final gzip member, same as
    `src/run001/validate_outputs.py` — a run killed by a time guard still
    yields a readable prefix (`src/run001/archive.py` module docstring).
    """
    store = store if store is not None else CandidateStore()
    artifact_dir = Path(artifact_dir)

    candidates = []
    for raw in read_records(artifact_dir / "candidates.jsonl.gz"):
        if raw.get("kind") != "candidate":
            continue
        candidate = _to_candidate(raw)
        if candidate is not None:
            candidates.append(candidate)
    store.append_candidates(candidates)

    selection = []
    for raw in read_records(artifact_dir / "candidates.ranking.jsonl.gz"):
        if raw.get("kind") != "selection":
            continue
        record = _to_selection(raw)
        if record is not None:
            selection.append(record)
    store.append_selection(selection)

    return store
