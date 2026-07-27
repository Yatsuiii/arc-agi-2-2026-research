"""Phase 8 failure taxonomy for the frozen GEN002-A pilot.

Search diagnostics use training demonstrations only. Ground truth is read
only after generation, to distinguish a correct emitted candidate from a
program that fit every demonstration but generalized incorrectly.
"""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.gen002.grid import from_nested_list
from src.gen002.pilot_runner import (
    OUT_DIR,
    PILOT_MANIFEST,
    S1_MAX_STATES,
    S1_TIMEOUT_S,
    TRAINING_CHALLENGES,
)
from src.gen002.search.best_first import search_best_first

TRAINING_SOLUTIONS = (
    Path(__file__).resolve().parents[2]
    .parent
    / "competition_2026"
    / "extracted"
    / "arc-agi_training_solutions.json"
)
GEN002A_DIR = OUT_DIR


def classify_failure(
    *,
    has_correct_candidate: bool,
    has_candidate: bool,
    best_n_solved: int,
) -> str:
    """Apply the frozen operational taxonomy to one pilot test-index."""
    if has_correct_candidate:
        return "success"
    if has_candidate:
        return "generalization_failure"
    if best_n_solved > 0:
        return "search_failure"
    return "missing_language"


def _diagnose_task(payload: tuple[str, dict]) -> tuple[str, dict]:
    task_id, task = payload
    train_inputs = tuple(from_nested_list(pair["input"]) for pair in task["train"])
    train_outputs = tuple(from_nested_list(pair["output"]) for pair in task["train"])
    result = search_best_first(
        train_inputs,
        train_outputs,
        max_states=S1_MAX_STATES,
        timeout_s=S1_TIMEOUT_S,
    )
    return task_id, {
        "n_train_pairs": len(train_inputs),
        "best_n_solved": result.best_n_solved,
        "best_pixel_agreement": result.best_pixel_agreement,
        "states_explored": result.states_explored,
        "timed_out": result.timed_out,
    }


def collect_search_diagnostics(*, max_workers: int = 4) -> dict[str, dict]:
    """Rerun the frozen S1 policy and retain analysis-only summaries."""
    manifest = json.loads(PILOT_MANIFEST.read_text())["test_indices"]
    challenges = json.loads(TRAINING_CHALLENGES.read_text())
    task_ids = sorted({row["task_id"] for row in manifest})
    payloads = [(task_id, challenges[task_id]) for task_id in task_ids]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return dict(pool.map(_diagnose_task, payloads))


def _read_candidates(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_taxonomy(
    diagnostics: dict[str, dict],
    *,
    manifest: list[dict] | None = None,
    solutions: dict | None = None,
    s0_records: list[dict] | None = None,
    s1_records: list[dict] | None = None,
) -> tuple[list[dict], dict]:
    manifest = manifest or json.loads(PILOT_MANIFEST.read_text())["test_indices"]
    solutions = solutions or json.loads(TRAINING_SOLUTIONS.read_text())
    s0_records = s0_records if s0_records is not None else _read_candidates(
        GEN002A_DIR / "s0_candidates.jsonl.gz"
    )
    s1_records = s1_records if s1_records is not None else _read_candidates(
        GEN002A_DIR / "s1_candidates.jsonl.gz"
    )

    candidates: dict[tuple[str, int], list[dict]] = {}
    for record in s0_records + s1_records:
        key = (record["task_id"], record["test_index"])
        candidates.setdefault(key, []).append(record)

    rows = []
    for item in manifest:
        task_id, test_index = item["task_id"], item["test_index"]
        records = candidates.get((task_id, test_index), [])
        target = solutions[task_id][test_index]
        has_correct = any(record["candidate_grid"] == target for record in records)
        diagnostic = diagnostics[task_id]
        category = classify_failure(
            has_correct_candidate=has_correct,
            has_candidate=bool(records),
            best_n_solved=diagnostic["best_n_solved"],
        )
        rows.append(
            {
                "task_id": task_id,
                "test_index": test_index,
                "group": item["group"],
                "category": category,
                "n_train_pairs": diagnostic["n_train_pairs"],
                "best_n_solved": diagnostic["best_n_solved"],
                "best_pixel_agreement": round(
                    diagnostic["best_pixel_agreement"], 6
                ),
                "s1_states_explored": diagnostic["states_explored"],
                "s1_timed_out": diagnostic["timed_out"],
                "n_emitted_candidates": len(records),
                "compressarc_oracle_hit": item["compressarc_oracle_hit"],
            }
        )

    counts = Counter(row["category"] for row in rows)
    summary = {
        "n_pilot_indices": len(rows),
        "category_counts": dict(sorted(counts.items())),
        "category_counts_by_group": {
            group: dict(
                sorted(
                    Counter(
                        row["category"] for row in rows if row["group"] == group
                    ).items()
                )
            )
            for group in ("A", "B", "C")
        },
        "classification_rule": {
            "success": "at least one emitted candidate equals the test target",
            "generalization_failure": "training-exact candidate(s) emitted, none equals the test target",
            "search_failure": "no candidate emitted, but an explored program exactly solved at least one training pair",
            "missing_language": "no candidate emitted and no explored program exactly solved any training pair",
        },
    }
    return rows, summary


def run_error_taxonomy(*, max_workers: int = 4) -> dict:
    diagnostics = collect_search_diagnostics(max_workers=max_workers)
    rows, summary = build_taxonomy(diagnostics)
    GEN002A_DIR.mkdir(parents=True, exist_ok=True)
    (GEN002A_DIR / "search_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n"
    )
    with open(
        GEN002A_DIR / "error_taxonomy.csv", "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (GEN002A_DIR / "error_taxonomy_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(run_error_taxonomy(), indent=2, sort_keys=True))
