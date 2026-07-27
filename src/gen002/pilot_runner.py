"""Runs S0 and S1 over GEN001-A's frozen 24-index pilot sample.

Search runs once per **task** (using that task's visible training pairs);
a task's exact programs are then applied to each pilot test-index belonging
to that task to produce candidate grids — the search itself never looks at
a test index's input beyond what `evaluate()` needs to render a candidate
(Phase 5's "a program may generate a test candidate only when it exactly
matches every training pair" gate, `is_exact_match`, already enforced
inside `search_enumerative`/`search_best_first`).

Reads `artifacts/GEN001A/pilot_manifest.json` and ACQ-001's corpus
manifest read-only (`experiments/GEN002A/LEAKAGE_POLICY.md` §2) — never
writes to either. Never reads a solutions file (`arc-agi_training_solutions.json`
is not imported anywhere in this module).

`run_task` returns only JSON-safe data (never a `Program`/`SearchResult`
object) so a worker's result can be persisted to `partial/<task_id>.json`
immediately and a resumed run can skip any task whose partial file already
exists — the resume mechanism this module supports.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from src.gen002.dsl.program import evaluate
from src.gen002.grid import from_nested_list, to_nested_list
from src.gen002.search.best_first import BEAM_WIDTH, search_best_first
from src.gen002.search.enumerative import search_enumerative
from src.gen002.search.pruning import MAX_COST, MAX_DEPTH

ROOT = Path(__file__).resolve().parents[2]
PILOT_MANIFEST = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"
TRAINING_CHALLENGES = ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_challenges.json"
OUT_DIR = ROOT / "artifacts" / "GEN002A"

S0_TIMEOUT_S = 20.0
S1_TIMEOUT_S = 45.0
S0_MAX_STATES = 20000
S1_MAX_STATES = 20000


def config_hash() -> str:
    payload = json.dumps(
        {
            "max_depth": MAX_DEPTH,
            "max_cost": MAX_COST,
            "beam_width": BEAM_WIDTH,
            "s0_timeout_s": S0_TIMEOUT_S,
            "s1_timeout_s": S1_TIMEOUT_S,
            "s0_max_states": S0_MAX_STATES,
            "s1_max_states": S1_MAX_STATES,
        },
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def load_manifest() -> list[dict]:
    return json.loads(PILOT_MANIFEST.read_text())["test_indices"]


def load_challenges() -> dict:
    return json.loads(TRAINING_CHALLENGES.read_text())


def _train_pairs(challenges: dict, task_id: str):
    task = challenges[task_id]
    inputs = tuple(from_nested_list(p["input"]) for p in task["train"])
    outputs = tuple(from_nested_list(p["output"]) for p in task["train"])
    return inputs, outputs


def _render_candidates(policy: str, task_id: str, test_index: int, test_input, result, cfg_hash: str):
    records = []
    seen_grids: set[tuple] = set()
    for order, program in enumerate(result.exact_programs):
        try:
            grid = evaluate(program, test_input)
        except Exception:  # noqa: BLE001 - a candidate that fails on the test input is simply dropped
            continue
        key = tuple(tuple(row) for row in grid)
        if key in seen_grids:
            continue
        seen_grids.add(key)
        records.append(
            {
                "task_id": task_id,
                "test_index": test_index,
                "candidate_grid": to_nested_list(key),
                "program_source": program.canonical(),
                "canonical_ast": program.canonical(),
                "program_cost": program.cost(),
                "search_policy": policy,
                "discovery_order": order,
                "runtime_s": result.elapsed_s,
                "n_states_explored": result.states_explored,
                "n_dead": result.n_dead,
                "n_duplicate": result.n_duplicate,
                "timed_out": result.timed_out,
                "config_hash": cfg_hash,
            }
        )
    return records


def run_task(task_id: str, train_inputs, train_outputs, test_indices: dict[int, object], cfg_hash: str) -> dict:
    """Runs both policies once for a task and renders candidates for every
    pilot test-index belonging to it. Returns JSON-safe data only — no
    `Program`/`SearchResult` object crosses the process boundary."""
    s0 = search_enumerative(
        train_inputs, train_outputs, max_states=S0_MAX_STATES, timeout_s=S0_TIMEOUT_S
    )
    s1 = search_best_first(
        train_inputs, train_outputs, max_states=S1_MAX_STATES, timeout_s=S1_TIMEOUT_S
    )
    per_index = {}
    for test_index, test_input in test_indices.items():
        s0_records = _render_candidates("S0", task_id, test_index, test_input, s0, cfg_hash)
        s1_records = _render_candidates("S1", task_id, test_index, test_input, s1, cfg_hash)
        per_index[str(test_index)] = {"s0_candidates": s0_records, "s1_candidates": s1_records}
    return {
        "task_id": task_id,
        "per_index": per_index,
        "s0_summary": {
            "states_explored": s0.states_explored,
            "n_exact_programs": len(s0.exact_programs),
            "n_dead": s0.n_dead,
            "n_duplicate": s0.n_duplicate,
            "timed_out": s0.timed_out,
            "elapsed_s": s0.elapsed_s,
        },
        "s1_summary": {
            "states_explored": s1.states_explored,
            "n_exact_programs": len(s1.exact_programs),
            "n_dead": s1.n_dead,
            "n_duplicate": s1.n_duplicate,
            "timed_out": s1.timed_out,
            "elapsed_s": s1.elapsed_s,
        },
    }


def run_pilot(*, run_dir: Path = OUT_DIR, max_workers: int | None = None) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = load_manifest()
    challenges = load_challenges()
    cfg_hash = config_hash()

    manifest = {
        "acquisition": "GEN002A",
        "config_hash": cfg_hash,
        "n_pilot_indices": len(rows),
        "max_depth": MAX_DEPTH,
        "max_cost": MAX_COST,
        "beam_width": BEAM_WIDTH,
        "s0_timeout_s": S0_TIMEOUT_S,
        "s1_timeout_s": S1_TIMEOUT_S,
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    task_to_indices: dict[str, list[int]] = {}
    row_by_task: dict[str, list[dict]] = {}
    for row in rows:
        task_to_indices.setdefault(row["task_id"], []).append(row["test_index"])
        row_by_task.setdefault(row["task_id"], []).append(row)
    task_ids = sorted(task_to_indices)
    workers = max_workers or min(4, os.cpu_count() or 1)

    errors_path = run_dir / "errors.jsonl"
    if not errors_path.exists():
        errors_path.write_text("")
    partial_dir = run_dir / "partial"
    partial_dir.mkdir(exist_ok=True)

    task_results: dict[str, dict] = {}
    for task_id in task_ids:
        partial_path = partial_dir / f"{task_id}.json"
        if partial_path.exists():
            task_results[task_id] = json.loads(partial_path.read_text())

    remaining = [t for t in task_ids if t not in task_results]
    start = time.monotonic()

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for task_id in remaining:
            train_inputs, train_outputs = _train_pairs(challenges, task_id)
            test_inputs = {
                idx: from_nested_list(challenges[task_id]["test"][idx]["input"])
                for idx in task_to_indices[task_id]
            }
            futures[pool.submit(run_task, task_id, train_inputs, train_outputs, test_inputs, cfg_hash)] = task_id
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                result = future.result()
                task_results[task_id] = result
                (partial_dir / f"{task_id}.json").write_text(json.dumps(result))
            except Exception as exc:  # noqa: BLE001 - archived, not swallowed
                with open(errors_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"task_id": task_id, "error": str(exc)}) + "\n")

    s0_records, s1_records, task_summary_rows = [], [], []
    for task_id, result in task_results.items():
        for row in row_by_task[task_id]:
            test_index = row["test_index"]
            index_data = result["per_index"][str(test_index)]
            s0_records.extend(index_data["s0_candidates"])
            s1_records.extend(index_data["s1_candidates"])
            task_summary_rows.append(
                {
                    "task_id": task_id,
                    "test_index": test_index,
                    "group": row["group"],
                    "s0_states": result["s0_summary"]["states_explored"],
                    "s0_exact_programs": result["s0_summary"]["n_exact_programs"],
                    "s0_candidates": len(index_data["s0_candidates"]),
                    "s0_timed_out": result["s0_summary"]["timed_out"],
                    "s0_runtime_s": round(result["s0_summary"]["elapsed_s"], 3),
                    "s1_states": result["s1_summary"]["states_explored"],
                    "s1_exact_programs": result["s1_summary"]["n_exact_programs"],
                    "s1_candidates": len(index_data["s1_candidates"]),
                    "s1_timed_out": result["s1_summary"]["timed_out"],
                    "s1_runtime_s": round(result["s1_summary"]["elapsed_s"], 3),
                }
            )

    _write_jsonl_gz(run_dir / "s0_candidates.jsonl.gz", s0_records)
    _write_jsonl_gz(run_dir / "s1_candidates.jsonl.gz", s1_records)
    _write_csv(run_dir / "task_summary.csv", sorted(task_summary_rows, key=lambda r: (r["task_id"], r["test_index"])))

    runtime_summary = {
        "n_pilot_indices": len(rows),
        "n_tasks": len(task_ids),
        "n_tasks_completed": len(task_results),
        "total_wall_clock_s": round(time.monotonic() - start, 3),
        "n_s0_candidates": len(s0_records),
        "n_s1_candidates": len(s1_records),
        "config_hash": cfg_hash,
        "max_workers": workers,
    }
    (run_dir / "runtime_summary.json").write_text(json.dumps(runtime_summary, indent=2, sort_keys=True))
    return runtime_summary


def _write_jsonl_gz(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    summary = run_pilot()
    print(json.dumps(summary, indent=2))
