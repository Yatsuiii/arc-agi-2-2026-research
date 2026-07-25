"""Build the EXP002-C smoke-pilot Kaggle notebook.

Generates a self-contained `.ipynb` from files already in this repository —
never hand-edited, same discipline as `src/run001/build_notebook.py`. Every
vendored/instrumented CompressARC module and the driver script
(`solve_task_cli.py`) are embedded verbatim via `%%writefile` cells, so the
code that runs on Kaggle is byte-identical to the code reviewed and committed
here, not a hand-retyped copy.

Scope: exactly the 5 tasks preregistered in
`experiments/EXP002C/pilot_sample.json`, per the user's explicit approval of
"the bounded EXP002-C smoke pilot only." Does not sample, does not scale,
does not touch NVARC. Run `python -m src.run002c.build_pilot_notebook` to
regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPRESSARC_DIR = ROOT / "third_party" / "compressarc"
DRIVER = ROOT / "src" / "run002c" / "solve_task_cli.py"
PILOT_SAMPLE = ROOT / "experiments" / "EXP002C" / "pilot_sample.json"
OUTPUT_DIR = ROOT / "kaggle" / "exp002c_pilot"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "exp002c_pilot.ipynb"

VENDORED_MODULES = [
    "multitensor_systems.py",
    "initializers.py",
    "layers.py",
    "preprocessing.py",
    "arc_compressor.py",
    "scoring.py",
    "visualization.py",
    "solution_selection.py",
    "train.py",
]  # visualization.py is a bare `import visualization` in train.py; needed
   # even though `solve_task_cli.py`'s call path never invokes its plotting
   # functions (confirmed by the flat-directory smoke test below).

RUN_DIR = "/kaggle/working/exp002c_pilot"
CHALLENGES_PATH = "/kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "/kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_solutions.json"


def _code_cell(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source}


def _md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def _writefile_cell(path: str, content: str) -> dict:
    text = content if content.endswith("\n") else content + "\n"
    return _code_cell(f"%%writefile {path}\n{text}")


SETUP_SOURCE = f'''import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

RUN_DIR = Path("{RUN_DIR}")
RUN_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR = RUN_DIR / "per_task"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
MONITOR_LOG = RUN_DIR / "gpu_monitor.log"
SUMMARY_PATH = RUN_DIR / "summary.json"

PILOT_TASK_IDS = {json.dumps(json.loads(PILOT_SAMPLE.read_text())["task_ids"])}

print("torch:", end=" ")
import torch
print(torch.__version__, "cuda available:", torch.cuda.is_available(), "device count:", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(f"  cuda:{{i}} = {{torch.cuda.get_device_name(i)}}")

challenges = json.loads(Path("{CHALLENGES_PATH}").read_text())
solutions = json.loads(Path("{SOLUTIONS_PATH}").read_text())
for task_id in PILOT_TASK_IDS:
    assert task_id in challenges, f"{{task_id}} missing from mounted training challenges"


def start_gpu_monitor(interval=2.0):
    """Background nvidia-smi poller. Runs for the whole notebook lifetime so
    every phase's window can be sliced out of one continuous log afterward."""
    stop_event = threading.Event()

    def _poll():
        with open(MONITOR_LOG, "a") as handle:
            while not stop_event.is_set():
                try:
                    out = subprocess.check_output(
                        [
                            "nvidia-smi",
                            "--query-gpu=index,utilization.gpu,memory.used,memory.total",
                            "--format=csv,noheader,nounits",
                        ],
                        text=True,
                    )
                    line = out.strip().replace("\\n", ";")
                    handle.write(f"{{time.time()}}|{{line}}\\n")
                except Exception as exc:  # nvidia-smi transient failure must not kill the pilot
                    handle.write(f"{{time.time()}}|ERROR:{{exc}}\\n")
                handle.flush()
                stop_event.wait(interval)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
    return stop_event, thread


def launch_task(task_id, device, time_limit_s):
    """One `solve_task_cli.py` subprocess, matching upstream's own
    process-per-task isolation. Returns the Popen handle (non-blocking) so
    callers can launch two in parallel for the concurrency test."""
    out_path = ARCHIVE_DIR / f"{{task_id}}.json"
    log_path = ARCHIVE_DIR / f"{{task_id}}.log"
    log_handle = open(log_path, "w")
    proc = subprocess.Popen(
        [
            sys.executable,
            "solve_task_cli.py",
            "--task-id", task_id,
            "--challenges", "{CHALLENGES_PATH}",
            "--out", str(out_path),
            "--n-iterations", "2000",
            "--time-limit-s", str(time_limit_s),
            "--device", device,
        ],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc, out_path, log_handle


def run_phase(name, launches, time_limit_s):
    """launches: list of (task_id, device). Runs all of them concurrently
    (one subprocess each), waits for every one, records wall clock and
    per-task results. Flushes to disk immediately on return, so a kill
    between phases still leaves every prior phase's results intact."""
    phase_start = time.time()
    handles = [(task_id, device, *launch_task(task_id, device, time_limit_s)) for task_id, device in launches]
    results = []
    for task_id, device, proc, out_path, log_handle in handles:
        returncode = proc.wait()
        log_handle.close()
        entry = {{"task_id": task_id, "device": device, "returncode": returncode}}
        if returncode == 0 and out_path.exists():
            entry["result"] = json.loads(out_path.read_text())
        else:
            entry["failed"] = True
        results.append(entry)
    phase_wall_s = time.time() - phase_start

    record = {{"phase": name, "wall_clock_s": phase_wall_s, "tasks": results}}
    phase_path = RUN_DIR / f"phase_{{name}}.json"
    phase_path.write_text(json.dumps(record, indent=2))  # incremental: survives a later phase's timeout
    print(f"phase {{name}}: {{phase_wall_s:.1f}}s wall clock, {{len(results)}} task(s)")
    return record


gpu_monitor_stop, gpu_monitor_thread = start_gpu_monitor()
'''

PHASE1_SOURCE = '''# Phase 1 — solo baseline: one task, one GPU, other GPU idle.
# Establishes the per-task time/VRAM figure this notebook exists to measure,
# uncontended, before asking whether a second concurrent task changes it.
phase1 = run_phase("1_solo_baseline", [(PILOT_TASK_IDS[0], "cuda:0")], time_limit_s=2400)
'''

PHASE2_SOURCE = '''# Phase 2 — concurrency test: two tasks, one per GPU, launched simultaneously.
# If both finish in roughly phase 1's solo time (not ~2x it), the two T4s are
# processing independently; if wall clock roughly doubles, they are not.
phase2 = run_phase(
    "2_concurrent",
    [(PILOT_TASK_IDS[1], "cuda:0"), (PILOT_TASK_IDS[2], "cuda:1")],
    time_limit_s=2400,
)
'''

PHASE3_SOURCE = '''# Phase 3 — second concurrency sample, for robustness against phase 2 being
# a fluke (cold-start effects, thermal throttling, first-CUDA-call overhead).
phase3 = run_phase(
    "3_concurrent",
    [(PILOT_TASK_IDS[3], "cuda:0"), (PILOT_TASK_IDS[4], "cuda:1")],
    time_limit_s=2400,
)

gpu_monitor_stop.set()
gpu_monitor_thread.join(timeout=5)
'''

ANALYSIS_SOURCE = '''# Final analysis — every number the pilot's preregistered objectives ask for,
# computed once, from the three phase_*.json files already on disk (never
# recomputed from a re-run, matching this project's figure-generation rule).
import hashlib
import statistics


def grid_digest(grid):
    return hashlib.sha1(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()[:16]


all_task_results = {}
for phase_name in ("1_solo_baseline", "2_concurrent", "3_concurrent"):
    record = json.loads((RUN_DIR / f"phase_{phase_name}.json").read_text())
    for entry in record["tasks"]:
        if "result" in entry:
            all_task_results[entry["task_id"]] = entry["result"]

per_task_stats = {}
total_candidates = 0
total_unique = 0
total_test_indices = 0
singleton_test_indices = 0
oracle_hits = 0
all_scores = []
failures = []

for task_id in PILOT_TASK_IDS:
    if task_id not in all_task_results:
        failures.append({"task_id": task_id, "reason": "no result file (subprocess failure)"})
        continue
    result = all_task_results[task_id]
    if result.get("timed_out"):
        failures.append({"task_id": task_id, "reason": f"timed out at {result['steps_run']} steps"})

    n_test = result["n_test"]
    truth = solutions[task_id]
    per_index_shas = [set() for _ in range(n_test)]
    per_index_hit = [False] * n_test
    for candidate in result["candidates"]:
        all_scores.append(candidate["accumulated_score"])
        for test_index in range(n_test):
            grid = candidate["grid"][test_index]
            sha = grid_digest(grid)
            per_index_shas[test_index].add(sha)
            total_candidates += 1
            if grid == truth[test_index]:
                per_index_hit[test_index] = True

    for test_index in range(n_test):
        total_unique += len(per_index_shas[test_index])
        total_test_indices += 1
        if len(per_index_shas[test_index]) <= 1:
            singleton_test_indices += 1
        if per_index_hit[test_index]:
            oracle_hits += 1

    per_task_stats[task_id] = {
        "n_test": n_test,
        "steps_run": result["steps_run"],
        "timed_out": result["timed_out"],
        "elapsed_s": result["elapsed_s"],
        "peak_memory_bytes": result["peak_memory_bytes"],
        "n_candidates": len(result["candidates"]),
        "n_unique_by_test_index": [len(s) for s in per_index_shas],
        "oracle_hit_by_test_index": per_index_hit,
    }

score_stats = None
if all_scores:
    score_stats = {
        "min": min(all_scores),
        "max": max(all_scores),
        "mean": statistics.fmean(all_scores),
        "stdev": statistics.pstdev(all_scores) if len(all_scores) > 1 else 0.0,
        "n": len(all_scores),
    }

solo_elapsed = per_task_stats.get(PILOT_TASK_IDS[0], {}).get("elapsed_s")
concurrent_pair_elapsed = [
    per_task_stats[t]["elapsed_s"] for t in PILOT_TASK_IDS[1:5] if t in per_task_stats
]

report = {
    "experiment": "EXP002-C smoke pilot",
    "pilot_sample": PILOT_TASK_IDS,
    "objective_1_runtime": {
        "per_task_elapsed_s": {t: per_task_stats[t]["elapsed_s"] for t in per_task_stats},
        "per_task_per_test_index_s": {
            t: per_task_stats[t]["elapsed_s"] / max(1, per_task_stats[t]["n_test"])
            for t in per_task_stats
        },
    },
    "objective_2_vram": {
        "per_task_peak_memory_mib": {
            t: per_task_stats[t]["peak_memory_bytes"] / (1024 * 1024) for t in per_task_stats
        },
        "gpu_monitor_log": str(MONITOR_LOG),
    },
    "objective_3_concurrency": {
        "solo_baseline_elapsed_s": solo_elapsed,
        "concurrent_pair_elapsed_s": concurrent_pair_elapsed,
        "phase2_wall_clock_s": phase2["wall_clock_s"],
        "phase3_wall_clock_s": phase3["wall_clock_s"],
        "interpretation": (
            "concurrent tasks finished within ~1x solo time: two T4s process independently"
            if concurrent_pair_elapsed and solo_elapsed and max(concurrent_pair_elapsed) < 1.5 * solo_elapsed
            else "concurrent tasks took roughly as long as serial: no effective concurrency observed"
        ),
    },
    "objective_4_candidates": {
        "total_candidates": total_candidates,
        "total_unique_candidates": total_unique,
        "total_test_indices": total_test_indices,
        "singleton_test_indices": singleton_test_indices,
        "singleton_frequency": singleton_test_indices / total_test_indices if total_test_indices else None,
        "native_score_distribution": score_stats,
        "candidate_oracle_coverage": oracle_hits / total_test_indices if total_test_indices else None,
        "archive_integrity": {
            "expected_tasks": len(PILOT_TASK_IDS),
            "recovered_tasks": len(all_task_results),
            "per_task_files_present": {
                t: (ARCHIVE_DIR / f"{t}.json").exists() for t in PILOT_TASK_IDS
            },
        },
        "failures": failures,
    },
    "per_task": per_task_stats,
}

# Objective 5/6: compare against the preregistered 210-290 GPU-hour estimate
# and extrapolate. Uses the mean observed per-task elapsed time; every task
# here ran the full 2000-iteration budget CompressARC's own paper uses, same
# as the estimate in PLAN.md, so no step-count rescaling is needed.
observed = [per_task_stats[t]["elapsed_s"] for t in per_task_stats]
if observed:
    mean_task_s = statistics.fmean(observed)
    mean_task_hours = mean_task_s / 3600
    report["objective_5_6_extrapolation"] = {
        "mean_observed_task_s": mean_task_s,
        "preregistered_estimate_range_gpu_hours": [210, 290],
        "serial_gpu_hours": {
            "100_tasks": mean_task_hours * 100,
            "250_tasks": mean_task_hours * 250,
            "500_tasks": mean_task_hours * 500,
        },
        "dual_t4_wall_clock_hours_if_perfectly_parallel": {
            "100_tasks": mean_task_hours * 100 / 2,
            "250_tasks": mean_task_hours * 250 / 2,
            "500_tasks": mean_task_hours * 500 / 2,
        },
    }

(RUN_DIR / "pilot_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
print(json.dumps(report, indent=2, sort_keys=True))
'''


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = [
        _md_cell(
            "# EXP002-C smoke pilot\n\n"
            "Runs exactly the 5 ARC-AGI-2 training tasks preregistered in "
            "`experiments/EXP002C/pilot_sample.json` through vendored, "
            "instrumented CompressARC. Approved scope only: measure runtime, "
            "VRAM, 2xT4 concurrency and candidate yield. **Does not** scale "
            "to more tasks, tune the solver, or inspect held-out results — "
            "see `experiments/EXP002C/PLAN.md`."
        ),
    ]
    for name in VENDORED_MODULES:
        cells.append(_writefile_cell(name, (COMPRESSARC_DIR / name).read_text()))
    cells.append(_writefile_cell("solve_task_cli.py", DRIVER.read_text()))
    cells.append(_code_cell(SETUP_SOURCE))
    cells.append(_code_cell(PHASE1_SOURCE))
    cells.append(_code_cell(PHASE2_SOURCE))
    cells.append(_code_cell(PHASE3_SOURCE))
    cells.append(_code_cell(ANALYSIS_SOURCE))

    notebook = {
        "metadata": {
            "kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
            "kaggle": {
                "accelerator": "nvidiaTeslaT4x2",
                "dataSources": [{"sourceType": "competition", "sourceId": 133469}],
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
                "isGpuEnabled": True,
            },
        },
        "nbformat_minor": 4,
        "nbformat": 4,
        "cells": cells,
    }
    OUTPUT_NOTEBOOK.write_text(json.dumps(notebook, indent=1) + "\n")
    return {"cells": len(cells)}


if __name__ == "__main__":
    result = build()
    print(f"wrote {OUTPUT_NOTEBOOK} ({result['cells']} cells)")
