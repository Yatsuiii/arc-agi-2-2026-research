"""Behaviour-neutral candidate archiving for RUN-001.

The NVARC baseline already builds, in memory, every fact this archive needs: the
beam score, the eight augmentation scores and the decoded grid for each
candidate. It then discards them. This module persists them so that one 12-hour
GPU run yields a permanent CPU-reanalysable dataset.

Neutrality is the whole design constraint, so the module obeys four rules:

- it never draws from any random number generator, so solver RNG state evolves
  identically whether archiving is on or off;
- it never mutates an argument, so candidate ordering and contents are untouched;
- it accumulates at most one task's records before flushing, so memory stays
  bounded (Kaggle gives 19.5 GB of writable space);
- every write is an append of a self-contained gzip member, so a run killed at
  any point leaves a readable prefix rather than a corrupt file.

Records are newline-delimited JSON inside a gzip stream. Two record kinds share
the file: `candidate`, written while solving, and `selection`, written during the
decode pass once ranks are known. They are joined on
`(task_id, test_index, grid_sha1)`.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
import zlib
from pathlib import Path

SCHEMA_VERSION = 3


def grid_digest(grid) -> str:
    """Stable identity for a predicted grid, used to join the two record kinds."""
    return hashlib.sha1(
        json.dumps(grid, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def to_grid(value) -> list:
    """Convert a numpy array or nested sequence to plain nested lists of int.

    Accepts whatever the solver happens to hold so callers never have to convert,
    which keeps the instrumentation call sites to a single line each.
    """
    if value is None:
        return []
    tolist = getattr(value, "tolist", None)
    if tolist is not None:
        value = tolist()
    return [[int(cell) for cell in row] for row in value]


def _jsonable(value):
    """Coerce numpy scalars and arrays to JSON-native types, recursively."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value
    item = getattr(value, "item", None)
    if item is not None and getattr(value, "ndim", None) == 0:
        return item()
    tolist = getattr(value, "tolist", None)
    if tolist is not None:
        return _jsonable(tolist())
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


class CandidateArchive:
    """Append-only archive for one RUN-001 execution.

    One instance per worker process. Workers write to distinct shard files so
    that concurrent GPU workers never interleave partial lines.
    """

    def __init__(self, run_dir, shard: str = "main", manifest: dict | None = None):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.shard = shard
        self.candidates_path = self.run_dir / f"candidates.{shard}.jsonl.gz"
        self.errors_path = self.run_dir / f"errors.{shard}.jsonl"
        self.summary_path = self.run_dir / f"task_summary.{shard}.csv"
        self._pending: list[dict] = []
        self._task_rows: list[dict] = []
        self._counts: dict[str, int] = {}
        if manifest is not None:
            self.write_manifest(manifest)
        if not self.summary_path.exists():
            self._append_text(self.summary_path, ",".join(_SUMMARY_COLUMNS) + "\n")

    # -- writing -----------------------------------------------------------

    @staticmethod
    def _append_text(path: Path, text: str) -> None:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

    def record_candidate(self, **fields) -> None:
        """Buffer one candidate. Cheap; no I/O until `flush_task`."""
        self._pending.append({"kind": "candidate", **_jsonable(fields)})

    def record_selection(self, **fields) -> None:
        """Buffer one post-aggregation ranking/selection fact."""
        self._pending.append({"kind": "selection", **_jsonable(fields)})

    def record_error(self, task_id, stage, exc, **extra) -> None:
        """Record an exception immediately; errors must survive a hard kill."""
        payload = {
            "task_id": task_id,
            "stage": stage,
            "exception_type": type(exc).__name__ if isinstance(exc, BaseException) else "str",
            "message": str(exc)[:2000],
            "wall_clock": time.time(),
            **_jsonable(extra),
        }
        self._append_text(
            self.errors_path, json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        )

    def flush_task(self, task_id: str, **summary) -> int:
        """Write this task's buffered records and one summary row, then fsync.

        Returns the number of records written. Safe to call with an empty
        buffer, which happens when a task times out before producing anything.
        """
        records, self._pending = self._pending, []
        if records:
            blob = "".join(
                json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in records
            )
            # Mode "ab" starts a fresh gzip member. Concatenated members are a
            # valid gzip stream, so a truncated file still reads back cleanly.
            with gzip.open(self.candidates_path, "ab", compresslevel=6) as handle:
                handle.write(blob.encode("utf-8"))
        self._counts[task_id] = self._counts.get(task_id, 0) + len(records)

        row = {"task_id": task_id, "n_records": len(records), **_jsonable(summary)}
        self._task_rows.append(row)
        self._append_text(self.summary_path, _summary_line(row))
        return len(records)

    def write_manifest(self, manifest: dict) -> None:
        path = self.run_dir / f"run_manifest.{self.shard}.json"
        path.write_text(
            json.dumps(_jsonable(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def write_runtime_summary(self, **fields) -> None:
        path = self.run_dir / f"runtime_summary.{self.shard}.json"
        payload = {
            "shard": self.shard,
            "tasks_flushed": len(self._task_rows),
            "records_total": sum(self._counts.values()),
            **_jsonable(fields),
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


_SUMMARY_COLUMNS = [
    "task_id",
    "n_records",
    "n_test_inputs",
    "n_candidates",
    "n_unique_grids",
    "ttt_seconds",
    "solve_seconds",
    "hit_time_guard",
    "gpu_index",
    "peak_mem_train_mib",
    "peak_mem_infer_mib",
]


def _summary_line(row: dict) -> str:
    values = []
    for column in _SUMMARY_COLUMNS:
        value = row.get(column, "")
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, float):
            value = f"{value:.4f}"
        text = str(value)
        values.append(f'"{text}"' if ("," in text or '"' in text) else text)
    return ",".join(values) + "\n"


def read_records(path):
    """Read back an archive shard, tolerating a truncated final member.

    A run killed mid-write leaves a partial gzip member; everything before it is
    still valid and must remain usable, which is the point of member-per-flush.
    """
    records = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    break
    except (EOFError, OSError, gzip.BadGzipFile, zlib.error):
        # A hard kill mid-write leaves a partial trailing member. zlib raises
        # zlib.error rather than an OSError for that case, so it must be caught
        # explicitly or crash recovery silently fails.
        pass
    return records
