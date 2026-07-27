from __future__ import annotations

import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION_MANIFEST = ROOT / "artifacts" / "GEN002B" / "validation_manifest.json"
CANDIDATES = ROOT / "artifacts" / "GEN002B" / "candidates.jsonl.gz"
TASK_SUMMARY = ROOT / "artifacts" / "GEN002B" / "task_summary.csv"
RUNTIME_SUMMARY = ROOT / "artifacts" / "GEN002B" / "runtime_summary.json"
SOLUTIONS = ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_solutions.json"
OUT_ANALYSIS = ROOT / "artifacts" / "GEN002B" / "offline_analysis.json"


def _read_candidates() -> list[dict]:
    rows = []
    if not CANDIDATES.exists():
        return rows
    with gzip.open(CANDIDATES, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def analyse() -> dict:
    manifest = json.loads(VALIDATION_MANIFEST.read_text())
    solutions = json.loads(SOLUTIONS.read_text())
    runtime = json.loads(RUNTIME_SUMMARY.read_text())
    task_rows = list(csv.DictReader(TASK_SUMMARY.open()))
    candidates = _read_candidates()

    candidates_by_index: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in candidates:
        candidates_by_index[(row["task_id"], int(row["test_index"]))].append(row)

    task_summary_by_index = {
        (row["task_id"], int(row["test_index"])): row for row in task_rows
    }

    classification_counts = Counter()
    group_counts = Counter()
    hit_indices = []
    incremental = []
    rows = []
    exact_program_total = 0
    unique_candidates = 0

    for row in manifest["test_indices"]:
        key = (row["task_id"], int(row["test_index"]))
        truth = solutions[row["task_id"]][row["test_index"]]
        emitted = candidates_by_index.get(key, [])
        summary = task_summary_by_index[key]
        correct = any(candidate["candidate_grid"] == truth for candidate in emitted)
        has_exact_program = int(summary["n_exact_programs"]) > 0
        if correct:
            classification = "success"
            hit_indices.append({"task_id": row["task_id"], "test_index": row["test_index"], "group": row["group"]})
        elif has_exact_program:
            classification = "generalization_failure"
        elif int(summary["best_n_solved_fallback"]) > 0:
            classification = "search_failure"
        else:
            classification = "missing_language"
        if classification == "success" and not row["compressarc_oracle_hit"]:
            incremental.append({"task_id": row["task_id"], "test_index": row["test_index"], "group": row["group"]})
        classification_counts[classification] += 1
        if correct:
            group_counts[f"{row['group']}_success"] += 1
        exact_program_total += int(summary["n_exact_programs"])
        unique_candidates += len(emitted)
        rows.append(
            {
                "task_id": row["task_id"],
                "test_index": row["test_index"],
                "group": row["group"],
                "compressarc_oracle_hit": bool(row["compressarc_oracle_hit"]),
                "n_candidates": len(emitted),
                "n_exact_programs": int(summary["n_exact_programs"]),
                "classification": classification,
                "correct": correct,
            }
        )

    compressarc_oracle = sum(1 for row in manifest["test_indices"] if row["compressarc_oracle_hit"])
    gen002b_oracle = sum(1 for row in rows if row["correct"])
    union_oracle = sum(
        1 for row, analysis_row in zip(manifest["test_indices"], rows) if row["compressarc_oracle_hit"] or analysis_row["correct"]
    )

    analysis = {
        "manifest_id": manifest["manifest_id"],
        "n_validation_indices": len(manifest["test_indices"]),
        "indices_with_candidates": sum(1 for row in rows if row["n_candidates"] > 0),
        "exact_program_total": exact_program_total,
        "unique_candidates": unique_candidates,
        "group_a2_rescues": group_counts["A2_success"],
        "group_b2_rescues": group_counts["B2_success"],
        "group_c2_successes": group_counts["C2_success"],
        "gen002b_oracle": gen002b_oracle,
        "compressarc_oracle": compressarc_oracle,
        "union_oracle": union_oracle,
        "incremental_indices": incremental,
        "classification_counts": dict(classification_counts),
        "rows": rows,
        "runtime_summary": runtime,
    }
    OUT_ANALYSIS.write_text(json.dumps(analysis, indent=2, sort_keys=True))
    return analysis


def main() -> None:
    analysis = analyse()
    print(json.dumps(analysis, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
