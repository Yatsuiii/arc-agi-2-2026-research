"""EXP002-D Phase 1: reconstruct the canonical candidate table from ACQ-001's
immutable archives. Read-only against ACQ-001 -- writes only under
`artifacts/EXP002D/`.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from src.run001.archive import read_records

REPO_ROOT = Path(__file__).resolve().parents[3]
SOLUTIONS_PATH = Path(
    "/home/Yatsuiii/arc-agi-2-2026/competition_2026/extracted/arc-agi_training_solutions.json"
)
CHALLENGES_PATH = Path(
    "/home/Yatsuiii/arc-agi-2-2026/competition_2026/extracted/arc-agi_training_challenges.json"
)
SHARD_ARCHIVES = {
    "A": REPO_ROOT / "artifacts/ACQ001/shard_a_output/acq001_a/archive/candidates.A.jsonl.gz",
    "B": REPO_ROOT / "artifacts/ACQ001/shard_b_output/acq001_b/archive/candidates.B.jsonl.gz",
}
TASK_STATS_CSV = REPO_ROOT / "artifacts/data_audit/task_statistics.csv"


def _load_task_families() -> dict[str, str]:
    with open(TASK_STATS_CSV, newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["task_id"]: row["size_relation"] for row in rows}


def _grid_key(grid) -> str:
    return json.dumps(grid, separators=(",", ":"))


def build_canonical_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (canonical_candidate_index, test_index_summary), both
    keyed off ACQ-001's raw archives only. `is_correct` is joined on last,
    after grouping/discovery-order is computed independent of ground truth."""
    solutions = json.loads(SOLUTIONS_PATH.read_text())

    candidate_groups: dict[tuple[str, int, str], dict] = {}
    discovery_counter: dict[tuple[str, int], int] = defaultdict(int)
    selection_records: list[dict] = []

    for shard, path in SHARD_ARCHIVES.items():
        for rec in read_records(path):
            task_id, test_index = rec["task_id"], rec["test_index"]
            if rec.get("kind") == "candidate":
                order = discovery_counter[(task_id, test_index)]
                discovery_counter[(task_id, test_index)] += 1
                key = (task_id, test_index, rec["grid_sha1"])
                if key not in candidate_groups:
                    candidate_groups[key] = {
                        "task_id": task_id,
                        "test_index": test_index,
                        "grid_sha1": rec["grid_sha1"],
                        "grid": rec["grid"],
                        "shard": shard,
                        "multiplicity": 0,
                        "beam_scores": [],
                        "first_discovery_order": order,
                    }
                group = candidate_groups[key]
                group["multiplicity"] += 1
                group["beam_scores"].append(rec["beam_score"])
                group["first_discovery_order"] = min(group["first_discovery_order"], order)
            elif rec.get("kind") == "selection":
                selection_records.append({**rec, "shard": shard})

    selection_by_key: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for rec in selection_records:
        selection_by_key[(rec["task_id"], rec["test_index"], rec["grid_sha1"])].append(rec)

    families = _load_task_families()

    rows = []
    for (task_id, test_index, grid_sha1), group in candidate_groups.items():
        scores = group["beam_scores"]
        sel = selection_by_key.get((task_id, test_index, grid_sha1), [])
        native_rank = min((s["rank"] for s in sel), default=None)
        truth = solutions[task_id][test_index]
        is_correct = group["grid"] == truth
        rows.append(
            {
                "task_id": task_id,
                "test_index": test_index,
                "grid_sha1": grid_sha1,
                "shard": group["shard"],
                "family": families.get(task_id, "unknown"),
                "multiplicity": group["multiplicity"],
                "beam_score_best": max(scores),
                "beam_score_mean": sum(scores) / len(scores),
                "beam_score_min": min(scores),
                "first_discovery_order": group["first_discovery_order"],
                "native_selected": native_rank is not None,
                "native_rank": native_rank,
                "is_correct": is_correct,
                "grid": group["grid"],
            }
        )

    candidate_index = pd.DataFrame(rows)

    summaries = []
    for (task_id, test_index), sub in candidate_index.groupby(["task_id", "test_index"]):
        n_candidates_total = int(sub["multiplicity"].sum())
        oracle_hit = bool(sub["is_correct"].any())
        native_selected = sub[sub["native_selected"]]
        native_top2_hit = bool(native_selected["is_correct"].any()) if len(native_selected) else False
        native_top1_hit = bool(
            native_selected[native_selected["native_rank"] == 1]["is_correct"].any()
        ) if len(native_selected) else False
        summaries.append(
            {
                "task_id": task_id,
                "test_index": test_index,
                "shard": sub["shard"].iloc[0],
                "family": sub["family"].iloc[0],
                "n_unique_candidates": len(sub),
                "n_candidates_total": n_candidates_total,
                "n_correct_unique": int(sub["is_correct"].sum()),
                "oracle_hit": oracle_hit,
                "native_top1_hit": native_top1_hit,
                "native_top2_hit": native_top2_hit,
            }
        )
    test_index_summary = pd.DataFrame(summaries)
    return candidate_index, test_index_summary


def main() -> None:
    out_dir = REPO_ROOT / "artifacts/EXP002D"
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_index, test_index_summary = build_canonical_tables()

    candidate_index_path = out_dir / "canonical_candidate_index.parquet"
    summary_path = out_dir / "test_index_summary.parquet"
    candidate_index.to_parquet(candidate_index_path, index=False)
    test_index_summary.to_parquet(summary_path, index=False)

    n_tasks = test_index_summary["task_id"].nunique()
    n_test_indices = len(test_index_summary)
    raw_candidate_records = int(candidate_index["multiplicity"].sum())
    n_unique = len(candidate_index)
    unique_fraction = n_unique / raw_candidate_records
    oracle_coverage = test_index_summary["oracle_hit"].mean()
    native_top2 = test_index_summary["native_top2_hit"].mean()

    print(f"n_tasks={n_tasks} n_test_indices={n_test_indices}")
    print(f"raw_candidate_records={raw_candidate_records} n_unique={n_unique} "
          f"unique_fraction={unique_fraction:.4f}")
    print(f"oracle_coverage={oracle_coverage:.4f} native_top2={native_top2:.4f}")


if __name__ == "__main__":
    main()
