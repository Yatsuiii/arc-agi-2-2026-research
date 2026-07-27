from __future__ import annotations

import csv
import gzip
import json
import resource
import time
from collections import Counter
from pathlib import Path

from src.gen002b.core import ArcTask, TaskRun, grid_sha1, load_task
from src.gen002b.search.compositional_search import (
    FALLBACK_S0_MAX_STATES,
    FALLBACK_S0_TIMEOUT_S,
    FALLBACK_S1_MAX_STATES,
    FALLBACK_S1_TIMEOUT_S,
    run_compositional_search,
)
from src.gen002b.search.constraints import derive_constraints
from src.gen002b.search.relational_search import run_relational_search
from src.gen002b.search.template_search import run_template_search

ROOT = Path(__file__).resolve().parents[2]
COMPETITION = ROOT.parent / "competition_2026" / "extracted"
TRAIN_CHALLENGES = COMPETITION / "arc-agi_training_challenges.json"
TRAIN_SOLUTIONS = COMPETITION / "arc-agi_training_solutions.json"
DEV_CHALLENGES = COMPETITION / "arc-agi_evaluation_challenges.json"
DEV_SOLUTIONS = COMPETITION / "arc-agi_evaluation_solutions.json"
TASK_STATS = ROOT / "artifacts" / "data_audit" / "task_statistics.csv"
OLD_PILOT = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"
VALIDATION_MANIFEST = ROOT / "artifacts" / "GEN002B" / "validation_manifest.json"


def frozen_config_payload() -> dict:
    return {
        "acquisition": "GEN002B",
        "stage_order": ["S2-A", "S2-B", "S2-C"],
        "background_hypotheses_per_task": 2,
        "connectivity_hypotheses": [4, 8],
        "fallback": {
            "s0_max_states": FALLBACK_S0_MAX_STATES,
            "s0_timeout_s": FALLBACK_S0_TIMEOUT_S,
            "s1_max_states": FALLBACK_S1_MAX_STATES,
            "s1_timeout_s": FALLBACK_S1_TIMEOUT_S,
        },
    }


def _load_old_task_ids() -> set[str]:
    rows = json.loads(OLD_PILOT.read_text())["test_indices"]
    return {row["task_id"] for row in rows}


def _load_validation_task_ids() -> set[str]:
    rows = json.loads(VALIDATION_MANIFEST.read_text())["test_indices"]
    return {row["task_id"] for row in rows}


def build_benchmark_task_ids(n_train: int = 50, n_dev: int = 25) -> dict[str, list[str]]:
    old = _load_old_task_ids()
    validation = _load_validation_task_ids()
    blocked = old | validation
    rows = list(csv.DictReader(TASK_STATS.open()))

    def pick(split: str, n: int) -> list[str]:
        pool = [row for row in rows if row["split"] == split and row["task_id"] not in blocked]
        pool.sort(
            key=lambda row: (
                row["size_relation"],
                row["large_grid"],
                int(row["n_input_colours"]),
                float(row["objects_input_mean"]),
                row["task_id"],
            )
        )
        if len(pool) <= n:
            return [row["task_id"] for row in pool]
        stride = len(pool) / n
        picks = sorted({int(i * stride) for i in range(n)})
        while len(picks) < n:
            for idx in range(len(pool)):
                if idx not in picks:
                    picks.append(idx)
                    break
            picks = sorted(picks)
        return [pool[idx]["task_id"] for idx in picks[:n]]

    return {
        "train_task_ids": pick("kaggle_training", n_train),
        "dev_task_ids": pick("kaggle_evaluation", n_dev),
    }


def _load_tasks(path: Path) -> dict[str, ArcTask]:
    data = json.loads(path.read_text())
    return {task_id: load_task(task_id, payload) for task_id, payload in data.items()}


def solve_task(task: ArcTask) -> TaskRun:
    start = time.monotonic()
    _constraints = derive_constraints(task)
    template_summary = run_template_search(task)
    relational_summary = run_relational_search(task)
    if template_summary.exact_programs or relational_summary.exact_programs:
        from src.gen002b.core import StageSummary

        compositional_summary = StageSummary(stage="S2-C")
    else:
        compositional_summary = run_compositional_search(task)
    stage_summaries = {"S2-A": template_summary, "S2-B": relational_summary, "S2-C": compositional_summary}

    exact_programs = []
    seen_programs = set()
    for stage in ("S2-A", "S2-B", "S2-C"):
        for program in stage_summaries[stage].exact_programs:
            canonical = program.canonical()
            if canonical in seen_programs:
                continue
            seen_programs.add(canonical)
            exact_programs.append(program)

    candidates_by_index: dict[int, list[dict]] = {}
    for test_index, test_input in enumerate(task.test_inputs):
        rows = []
        seen_grids = set()
        for discovery_order, program in enumerate(sorted(exact_programs, key=lambda p: (p.cost, p.canonical()))):
            try:
                grid = program.apply(test_input)
            except Exception:  # noqa: BLE001
                continue
            digest = grid_sha1(grid)
            if digest in seen_grids:
                continue
            seen_grids.add(digest)
            rows.append(
                {
                    "task_id": task.task_id,
                    "test_index": test_index,
                    "candidate_grid": [list(row) for row in grid],
                    "grid_sha1": digest,
                    "program_source": program.canonical(),
                    "program_cost": program.cost,
                    "stage": program.stage,
                    "family": program.family,
                    "discovery_order": discovery_order,
                }
            )
        candidates_by_index[test_index] = rows

    return TaskRun(
        task_id=task.task_id,
        exact_programs=exact_programs,
        candidates_by_index=candidates_by_index,
        stage_summaries=stage_summaries,
        elapsed_s=time.monotonic() - start,
    )


def _write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def run_benchmark(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = build_benchmark_task_ids()
    payload = frozen_config_payload() | selected
    tasks = _load_tasks(TRAIN_CHALLENGES)
    dev_tasks = _load_tasks(DEV_CHALLENGES)
    train_solutions = json.loads(TRAIN_SOLUTIONS.read_text())
    dev_solutions = json.loads(DEV_SOLUTIONS.read_text())

    all_rows = []
    all_candidates = []
    classification_counts = Counter()
    template_usage = Counter()
    total_states = 0
    total_runtime = 0.0
    exact_program_tasks = 0
    correct_test_indices = 0
    total_test_indices = 0

    for split_name, task_ids, source_tasks, source_solutions in (
        ("train", selected["train_task_ids"], tasks, train_solutions),
        ("dev", selected["dev_task_ids"], dev_tasks, dev_solutions),
    ):
        for task_id in task_ids:
            run = solve_task(source_tasks[task_id])
            total_runtime += run.elapsed_s
            if run.exact_programs:
                exact_program_tasks += 1
            for stage_summary in run.stage_summaries.values():
                template_usage.update(stage_summary.template_usage)
                total_states += stage_summary.states_explored
            for test_index, candidates in run.candidates_by_index.items():
                truth = source_solutions[task_id][test_index]
                total_test_indices += 1
                correct = any(row["candidate_grid"] == truth for row in candidates)
                if correct:
                    correct_test_indices += 1
                    classification = "success"
                elif run.exact_programs:
                    classification = "generalization_failure"
                elif run.stage_summaries["S2-C"].best_n_solved > 0:
                    classification = "search_failure"
                else:
                    classification = "missing_language"
                classification_counts[classification] += 1
                all_rows.append(
                    {
                        "split": split_name,
                        "task_id": task_id,
                        "test_index": test_index,
                        "n_exact_programs": len(run.exact_programs),
                        "n_candidates": len(candidates),
                        "classification": classification,
                        "elapsed_s": round(run.elapsed_s, 4),
                        "states_explored": sum(s.states_explored for s in run.stage_summaries.values()),
                    }
                )
                all_candidates.extend(candidates)

    benchmark = {
        "selected": selected,
        "config": payload,
        "n_tasks": len(selected["train_task_ids"]) + len(selected["dev_task_ids"]),
        "n_test_indices": total_test_indices,
        "exact_program_task_coverage": exact_program_tasks / max(1, len(selected["train_task_ids"]) + len(selected["dev_task_ids"])),
        "held_out_accuracy": correct_test_indices / max(1, total_test_indices),
        "states_explored": total_states,
        "total_runtime_s": round(total_runtime, 4),
        "peak_ram_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3),
        "template_usage": dict(template_usage),
        "classification_counts": dict(classification_counts),
    }
    (out_dir / "benchmark_rows.json").write_text(json.dumps(all_rows, indent=2))
    _write_jsonl_gz(out_dir / "benchmark_candidates.jsonl.gz", all_candidates)
    (out_dir / "benchmark_summary.json").write_text(json.dumps(benchmark, indent=2, sort_keys=True))
    return benchmark


def run_validation_generation(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VALIDATION_MANIFEST.read_text())
    selected = {(row["task_id"], row["test_index"]): row for row in manifest["test_indices"]}
    tasks = _load_tasks(TRAIN_CHALLENGES)
    run_manifest = {
        "acquisition": "GEN002B",
        "manifest_id": manifest["manifest_id"],
        "config": frozen_config_payload(),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True))

    candidate_rows = []
    task_summary_rows = []
    completed_indices = []
    errors = []
    total_runtime = 0.0
    total_states = 0

    by_task: dict[str, list[int]] = {}
    for task_id, test_index in selected:
        by_task.setdefault(task_id, []).append(test_index)

    for task_id in sorted(by_task):
        try:
            run = solve_task(tasks[task_id])
            total_runtime += run.elapsed_s
            total_states += sum(s.states_explored for s in run.stage_summaries.values())
            for test_index in sorted(by_task[task_id]):
                candidates = run.candidates_by_index[test_index]
                candidate_rows.extend(candidates)
                completed_indices.append({"task_id": task_id, "test_index": test_index})
                task_summary_rows.append(
                    {
                        "task_id": task_id,
                        "test_index": test_index,
                        "n_candidates": len(candidates),
                        "n_exact_programs": len(run.exact_programs),
                        "elapsed_s": round(run.elapsed_s, 4),
                        "states_explored": sum(s.states_explored for s in run.stage_summaries.values()),
                        "template_stage_exact": len(run.stage_summaries["S2-A"].exact_programs),
                        "relational_stage_exact": len(run.stage_summaries["S2-B"].exact_programs),
                        "compositional_stage_exact": len(run.stage_summaries["S2-C"].exact_programs),
                        "best_n_solved_fallback": run.stage_summaries["S2-C"].best_n_solved,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"task_id": task_id, "error": str(exc)})

    _write_jsonl_gz(out_dir / "candidates.jsonl.gz", candidate_rows)
    with (out_dir / "errors.jsonl").open("w", encoding="utf-8") as handle:
        for row in errors:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    with (out_dir / "task_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(task_summary_rows[0]) if task_summary_rows else ["task_id", "test_index"])
        writer.writeheader()
        writer.writerows(task_summary_rows)
    (out_dir / "completed_indices.json").write_text(json.dumps(completed_indices, indent=2))
    runtime_summary = {
        "n_completed_indices": len(completed_indices),
        "total_runtime_s": round(total_runtime, 4),
        "states_explored": total_states,
        "peak_ram_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3),
    }
    (out_dir / "runtime_summary.json").write_text(json.dumps(runtime_summary, indent=2, sort_keys=True))
    return runtime_summary
