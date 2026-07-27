"""Candidate-export adapter for the single frozen NVARC-lineage configuration.

Translates NVARC's own candidate representation into `src.run001.archive`
records — the exact schema ACQ-001's own acquisition
(`src/run002c/acquire_shard.py`) already writes, so CompressARC and NVARC
candidates are joinable by the same `(task_id, test_index, grid_sha1)` key
without a second schema to maintain.

This module never performs GPU inference itself. `Generator` is the
interface a real, GPU-backed implementation would satisfy; `MockGenerator`
is the only implementation this repository ships, used for CPU-only
validation (`experiments/GEN001A/LOCAL_VALIDATION.md`). A real
implementation is Kaggle-kernel-only code, written directly into
`kaggle/gen001_nvarc_pilot/` (Phase 9), never imported here — this keeps
`src/gen001/` importable and testable without torch, CUDA, or the NVARC
checkpoint present.

Frozen-baseline discipline, same as `src/harness/schemas.py`: nothing here
reads a ground-truth field. `PilotConfig` and `Generator.generate` receive
only a task's demonstration pairs and test input, never a test output.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Protocol

from src.run001.archive import grid_digest, to_grid

CONTAMINATION_STATUS = "SCIENTIFICALLY_CONTAMINATED"
"""Fixed per `experiments/GEN001A/CONTAMINATION_AUDIT.md`. Not a per-call
parameter: every record this adapter produces carries this exact value,
because the classification is a property of the checkpoint against
ACQ-001's corpus, not of any individual candidate."""

MOCK_CHECKPOINT_ID = "MOCK"
"""Reserved checkpoint identity for `MockGenerator`. Never a valid identity
for a real checkpoint, so a record can never be mistaken for a real result
by checking this one field."""


@dataclass(frozen=True)
class PilotConfig:
    """The single frozen NVARC configuration (Phase 6). Every field here is
    fixed before generation starts and is included in `config_hash`, so a
    future accidental parameter drift is detectable rather than silent."""

    checkpoint_id: str
    tokenizer_vocab_size: int
    quantization: str
    augmentation_count: int
    adaptation_steps: int
    candidate_cap: int
    per_task_time_cap_s: int
    global_time_cap_s: int
    seed: int
    selection_algorithm: str
    contamination_status: str = CONTAMINATION_STATUS

    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(payload.encode()).hexdigest()[:16]


FROZEN_PILOT_CONFIG = PilotConfig(
    checkpoint_id="sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1",
    tokenizer_vocab_size=16,
    quantization="nf4-4bit",
    augmentation_count=16,
    adaptation_steps=128,
    candidate_cap=64,
    per_task_time_cap_s=1200,
    global_time_cap_s=42000,
    seed=20260727,
    selection_algorithm="score_kgmon",
)
"""Restated from `experiments/GEN001A/NVARC_LINEAGE_AUDIT.md` (checkpoint,
tokenizer, quantization, TTT augmentation count and step count, selection
algorithm) and `PILOT_PROTOCOL.md` (seed reuses this project's EXP002-D
convention of one fixed integer per experiment). `candidate_cap` and the
time caps are pilot-scale guards (Phase 9's KERNEL_PREFLIGHT.md), not RUN-001's
own per-task 1200s/global 11h40m values reused verbatim for the 24-index
pilot's much smaller scope, except per-task time cap which is kept
identical to RUN-001's for direct comparability."""


@dataclass(frozen=True)
class TaskInput:
    """What a generator is allowed to see. No test output field exists on
    this type — the frozen-baseline guarantee is structural, not a runtime
    check that could be forgotten."""

    task_id: str
    test_index: int
    train_pairs: tuple[dict, ...]
    test_input: list[list[int]]


class Generator(Protocol):
    """Interface a real, GPU-backed NVARC implementation satisfies. Not
    implemented in this repository; see module docstring."""

    def generate(self, task: TaskInput, config: PilotConfig) -> list[dict]:
        """Return a list of raw candidate dicts, each with at least `grid`
        and `beam_score`. No ground truth is passed in, so no implementation
        of this method can access it through this interface."""
        ...


class MockGenerator:
    """Deterministic, schema-valid, CPU-only stand-in. Emits candidates by
    trivially transforming the test input, never anything derived from a
    ground-truth grid this class is never given. Used only to validate the
    rest of the pipeline (archive writing, resume, union analysis) without
    a GPU or checkpoint present."""

    def __init__(self, n_candidates: int = 3):
        self.n_candidates = n_candidates

    def generate(self, task: TaskInput, config: PilotConfig) -> list[dict]:
        candidates = []
        for i in range(self.n_candidates):
            grid = [row[:] for row in task.test_input]
            if grid and grid[0]:
                grid[0][0] = (grid[0][0] + i) % 10
            candidates.append(
                {
                    "grid": grid,
                    "beam_score": -float(i),
                    "augmentation_key": f"mock-aug-{i}",
                    "generation_order": i,
                }
            )
        return candidates


def export_candidate_record(
    task: TaskInput,
    raw_candidate: dict,
    config: PilotConfig,
    *,
    checkpoint_id: str,
) -> dict:
    """Build one `CandidateArchive.record_candidate`-shaped dict.

    `checkpoint_id` is passed explicitly (rather than always read from
    `config`) so `MockGenerator`'s output is stamped `MOCK_CHECKPOINT_ID`
    even when it is exercised against `FROZEN_PILOT_CONFIG` in a test,
    keeping the "never confused with a real result" guarantee independent
    of which config object happens to be in scope.
    """
    grid = to_grid(raw_candidate["grid"])
    if not grid or not all(isinstance(row, list) for row in grid):
        raise ValueError(f"invalid candidate grid for {task.task_id}/{task.test_index}")
    return {
        "task_id": task.task_id,
        "test_index": task.test_index,
        "grid": grid,
        "grid_sha1": grid_digest(grid),
        "solver_branch": "nvarc_lineage_branch1",
        "seed": config.seed,
        "augmentation_key": raw_candidate.get("augmentation_key"),
        "beam_score": raw_candidate.get("beam_score"),
        "generation_order": raw_candidate.get("generation_order"),
        "checkpoint_id": checkpoint_id,
        "config_hash": config.config_hash(),
        "contamination_status": config.contamination_status,
    }


def deduplicate_candidates(records: list[dict]) -> list[dict]:
    """Collapse exact-duplicate grids for one (task_id, test_index), keeping
    the first occurrence's provenance and counting multiplicity — same
    construction as `src/analysis/exp002d/corpus.py`'s multiplicity field,
    reused here rather than reinvented so the two corpora stay comparable."""
    seen: dict[tuple, dict] = {}
    for record in records:
        key = (record["task_id"], record["test_index"], record["grid_sha1"])
        if key not in seen:
            seen[key] = {**record, "multiplicity": 1}
        else:
            seen[key]["multiplicity"] += 1
    return list(seen.values())
