"""Orchestrates the 24-index pilot: loads the frozen manifest, calls a
`Generator` per test-index, writes candidates via `CandidateArchive`.

Runs identically whether `generator` is `MockGenerator` (CPU validation,
`experiments/GEN001A/LOCAL_VALIDATION.md`) or a real GPU-backed
implementation (Kaggle-only, Phase 9) — the orchestration logic never
branches on which one it holds, which is what makes the CPU dry run a
genuine validation of the code path a real pilot would execute, not a
separate untested code path that happens to look similar.

Resumable: `completed_indices.json` is read at start and any index already
present is skipped, so an interrupted run picks up where it left off,
mirroring `src/run002c/acquire_shard.py`'s checkpoint discipline.

Never reads a ground-truth field: `_load_task_input` reads only `train` and
the test `input` from the challenges file, never a solutions file.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from src.gen001.nvarc_adapter import (
    Generator,
    MockGenerator,
    PilotConfig,
    TaskInput,
    deduplicate_candidates,
    export_candidate_record,
)
from src.run001.archive import CandidateArchive

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"
DEFAULT_CHALLENGES = ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_challenges.json"


def load_manifest(path: Path = DEFAULT_MANIFEST) -> list[dict]:
    return json.loads(path.read_text())["test_indices"]


def _load_task_input(challenges: dict, task_id: str, test_index: int) -> TaskInput:
    task = challenges[task_id]
    return TaskInput(
        task_id=task_id,
        test_index=test_index,
        train_pairs=tuple(task["train"]),
        test_input=task["test"][test_index]["input"],
    )


def _load_completed(run_dir: Path) -> set[tuple[str, int]]:
    path = run_dir / "completed_indices.json"
    if not path.exists():
        return set()
    return {tuple(pair) for pair in json.loads(path.read_text())}


def _save_completed(run_dir: Path, completed: set[tuple[str, int]]) -> None:
    path = run_dir / "completed_indices.json"
    path.write_text(json.dumps(sorted(list(pair) for pair in completed)))


def run_pilot(
    *,
    run_dir: Path,
    generator: Generator,
    config: PilotConfig,
    checkpoint_id: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    challenges_path: Path = DEFAULT_CHALLENGES,
    global_time_cap_s: int | None = None,
) -> dict:
    """Run every manifest row not already in `completed_indices.json`.

    Returns a runtime summary dict; also writes it to
    `runtime_summary.json` in `run_dir`, matching ACQ-001's own output
    contract (`src/run001/archive.py::CandidateArchive.write_runtime_summary`).
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = load_manifest(manifest_path)
    challenges = json.loads(Path(challenges_path).read_text())
    archive = CandidateArchive(run_dir, shard="pilot", manifest=vars(config) | {"checkpoint_id": checkpoint_id})

    completed = _load_completed(run_dir)
    cap = global_time_cap_s if global_time_cap_s is not None else config.global_time_cap_s
    start = time.monotonic()
    n_run = 0
    hit_global_cap = False

    for row in rows:
        key = (row["task_id"], row["test_index"])
        if key in completed:
            continue
        if time.monotonic() - start > cap:
            hit_global_cap = True
            break

        task = _load_task_input(challenges, row["task_id"], row["test_index"])
        task_start = time.monotonic()
        try:
            raw_candidates = generator.generate(task, config)
        except Exception as exc:  # noqa: BLE001 - archived, not swallowed
            archive.record_error(task.task_id, "generate", exc, test_index=task.test_index)
            raw_candidates = []
        task_elapsed = time.monotonic() - task_start

        records = [
            export_candidate_record(task, raw, config, checkpoint_id=checkpoint_id)
            for raw in raw_candidates
        ]
        records = deduplicate_candidates(records)
        for record in records:
            archive.record_candidate(**record)
        archive.flush_task(
            task.task_id,
            test_index=task.test_index,
            n_candidates=len(records),
            hit_time_guard=task_elapsed > config.per_task_time_cap_s,
        )
        completed.add(key)
        _save_completed(run_dir, completed)
        n_run += 1

    summary = dict(
        n_manifest_rows=len(rows),
        n_completed=len(completed),
        n_run_this_call=n_run,
        hit_global_cap=hit_global_cap,
        checkpoint_id=checkpoint_id,
        config_hash=config.config_hash(),
        contamination_status=config.contamination_status,
    )
    archive.write_runtime_summary(**summary)
    return summary


def main() -> None:
    """CPU-only dry run using `MockGenerator`. Never mistaken for a real
    pilot result: `checkpoint_id=MOCK_CHECKPOINT_ID` is stamped on every
    record it produces."""
    from src.gen001.nvarc_adapter import FROZEN_PILOT_CONFIG, MOCK_CHECKPOINT_ID

    run_dir = ROOT / "artifacts" / "GEN001A" / "mock_pilot_output"
    summary = run_pilot(
        run_dir=run_dir,
        generator=MockGenerator(),
        config=FROZEN_PILOT_CONFIG,
        checkpoint_id=MOCK_CHECKPOINT_ID,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
