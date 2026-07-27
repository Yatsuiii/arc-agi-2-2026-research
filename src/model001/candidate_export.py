from __future__ import annotations

import gzip
import json
from pathlib import Path

from src.run001.archive import grid_digest


def export_candidates(path: Path, predictions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in predictions:
            grid = row["grid"]
            payload = {
                "kind": "candidate",
                "task_id": row["task_id"],
                "test_index": row.get("test_index", 0),
                "grid": grid,
                "grid_sha1": grid_digest(grid),
                "solver_branch": "model001",
                "rank": row.get("rank", 0),
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

