"""Phase 7: offline oracle/union analysis. Reads ground truth only after
generation has already completed (`s0_candidates.jsonl.gz`/
`s1_candidates.jsonl.gz` are read-only inputs here, produced by
`pilot_runner.py` before this module ever runs) — never during search.

Reports exactly the metrics `experiments/GEN002A/PLAN.md` Phase 7
predeclared. No verifier is fit here; this is oracle-membership set
arithmetic, per the acceptance message's "do not train a verifier" limit.
"""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN002A_DIR = ROOT / "artifacts" / "GEN002A"
PILOT_MANIFEST = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"
TRAINING_SOLUTIONS = ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_solutions.json"


def _read_jsonl_gz(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _oracle_hits(records: list[dict], solutions: dict) -> set[tuple[str, int]]:
    hits = set()
    for record in records:
        task_id, test_index = record["task_id"], record["test_index"]
        target = solutions.get(task_id)
        if target is None or test_index >= len(target):
            continue
        if record["candidate_grid"] == target[test_index]:
            hits.add((task_id, test_index))
    return hits


def run_oracle_analysis() -> dict:
    manifest = json.loads(PILOT_MANIFEST.read_text())["test_indices"]
    solutions = json.loads(TRAINING_SOLUTIONS.read_text())

    pilot_indices = {(r["task_id"], r["test_index"]) for r in manifest}
    group_of = {(r["task_id"], r["test_index"]): r["group"] for r in manifest}
    compressarc_oracle_indices = {
        (r["task_id"], r["test_index"]) for r in manifest if r["compressarc_oracle_hit"]
    }

    s0_records = _read_jsonl_gz(GEN002A_DIR / "s0_candidates.jsonl.gz")
    s1_records = _read_jsonl_gz(GEN002A_DIR / "s1_candidates.jsonl.gz")

    s0_hits = _oracle_hits(s0_records, solutions) & pilot_indices
    s1_hits = _oracle_hits(s1_records, solutions) & pilot_indices
    p_hits = s0_hits | s1_hits
    c_hits = compressarc_oracle_indices & pilot_indices

    n = len(pilot_indices)
    union = c_hits | p_hits
    overlap = c_hits & p_hits
    incremental = p_hits - c_hits
    c_only = c_hits - p_hits
    jaccard = len(overlap) / len(union) if union else 0.0

    def group_rescues(group: str) -> int:
        return sum(
            1 for key in incremental if group_of.get(key) == group
        )

    def group_redundancy(group: str) -> int:
        return sum(1 for key in overlap if group_of.get(key) == group)

    task_summary_path = GEN002A_DIR / "task_summary.csv"
    states = []
    timeouts = 0
    n_task_rows = 0
    if task_summary_path.exists():
        import csv

        with open(task_summary_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                n_task_rows += 1
                states.append(int(row["s0_states"]))
                states.append(int(row["s1_states"]))
                if row["s0_timed_out"] == "True":
                    timeouts += 1
                if row["s1_timed_out"] == "True":
                    timeouts += 1

    n_exact_programs = defaultdict(set)
    for record in s0_records + s1_records:
        n_exact_programs[(record["task_id"], record["test_index"])].add(record["program_source"])
    distinct_program_count = sum(len(v) for v in n_exact_programs.values())

    result = {
        "n_pilot_indices": n,
        "s0_candidate_oracle": len(s0_hits) / n if n else 0.0,
        "s1_candidate_oracle": len(s1_hits) / n if n else 0.0,
        "program_synthesis_union_oracle": len(p_hits) / n if n else 0.0,
        "compressarc_oracle_pilot_subset": len(c_hits) / n if n else 0.0,
        "union_c_p_oracle": len(union) / n if n else 0.0,
        "n_program_synthesis_only_rescues": len(incremental),
        "group_a_rescues": group_rescues("A"),
        "group_a_total": 12,
        "group_b_rescues": group_rescues("B"),
        "group_b_total": 6,
        "group_c_redundancy": group_redundancy("C"),
        "group_c_total": 6,
        "n_exact_program_task_indices": len(n_exact_programs),
        "n_distinct_programs_total": distinct_program_count,
        "n_distinct_candidates_s0": len({(r["task_id"], r["test_index"], tuple(map(tuple, r["candidate_grid"]))) for r in s0_records}),
        "n_distinct_candidates_s1": len({(r["task_id"], r["test_index"], tuple(map(tuple, r["candidate_grid"]))) for r in s1_records}),
        "mean_states_explored": sum(states) / len(states) if states else 0.0,
        "timeout_rate": timeouts / (2 * n_task_rows) if n_task_rows else 0.0,
        "n_p": len(p_hits),
        "n_p_minus_c": len(p_hits - c_hits),
        "n_p_intersect_c": len(p_hits & c_hits),
        "n_c_minus_p": len(c_only),
        "n_c_union_p": len(union),
        "jaccard_c_p": jaccard,
    }
    return result


def main() -> None:
    result = run_oracle_analysis()
    out_path = GEN002A_DIR / "oracle_analysis.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
