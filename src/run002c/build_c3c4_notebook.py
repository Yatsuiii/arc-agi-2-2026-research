"""Build the EXP002-C2 oversubscription pilot Kaggle notebook.

Generates a self-contained `.ipynb`, same discipline as
`build_pilot_notebook.py`: every vendored/instrumented CompressARC module and
the unmodified `solve_task_cli.py` driver are embedded verbatim via
`%%writefile` cells, so the code that runs on Kaggle is byte-identical to
what's committed here. Adds C3/C4 oversubscribed-concurrency orchestration
and extended telemetry (PID tracking, power/temperature, CPU/RAM/disk) on
top of the frozen EXP002-C solver path — see
`experiments/EXP002C2/BASELINE_SPEC.md` for the exact freeze list and GPU
assignment this notebook implements.

Scope: exactly the 5 tasks preregistered in
`experiments/EXP002C/pilot_sample.json`, run once as C3 (3 processes/GPU)
and once as C4 (4 processes/GPU). Does not touch C1 (reused from
`experiments/EXP002C/PILOT_RESULTS.md`, not rerun). Run
`python -m src.run002c.build_c3c4_notebook` to regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPRESSARC_DIR = ROOT / "third_party" / "compressarc"
DRIVER = ROOT / "src" / "run002c" / "solve_task_cli.py"
PILOT_SAMPLE = ROOT / "experiments" / "EXP002C" / "pilot_sample.json"
OUTPUT_DIR = ROOT / "kaggle" / "exp002c2_oversubscription"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "exp002c2_oversubscription.ipynb"

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
]

RUN_DIR = "/kaggle/working/exp002c2_pilot"

# C3: 3 processes/GPU (6 slots, 5 tasks used). C4: 4 processes/GPU (8 slots,
# 5 tasks used). `42f83767` (BASELINE_SPEC.md's measured outlier) isolated on
# GPU1 in both, so its known intrinsic slowness cannot be misread as a
# contention symptom, and C4's GPU1 slot is a genuinely uncontended re-check.
CONFIGS = {
    "C3": [
        ("00576224", "cuda:0"),
        ("009d5c81", "cuda:0"),
        ("0520fde7", "cuda:0"),
        ("42f83767", "cuda:1"),
        ("8abad3cf", "cuda:1"),
    ],
    "C4": [
        ("00576224", "cuda:0"),
        ("009d5c81", "cuda:0"),
        ("0520fde7", "cuda:0"),
        ("8abad3cf", "cuda:0"),
        ("42f83767", "cuda:1"),
    ],
}
TIME_LIMIT_S = 2400  # unchanged from C1 (BASELINE_SPEC.md §2 freeze list)


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

try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False
    print("psutil not available: CPU/RAM/disk telemetry will be omitted, not fabricated")

RUN_DIR = Path("{RUN_DIR}")
RUN_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR = RUN_DIR / "per_task"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
MONITOR_LOG = RUN_DIR / "telemetry_monitor.log"

PILOT_TASK_IDS = {json.dumps(json.loads(PILOT_SAMPLE.read_text())["task_ids"])}
TIME_LIMIT_S = {TIME_LIMIT_S}

CHALLENGES_CANDIDATES = (
    "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json",
    "/kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json",
)
SOLUTIONS_CANDIDATES = (
    "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_training_solutions.json",
    "/kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_solutions.json",
)


def _resolve(candidates):
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(f"none of {{candidates}} exist")


CHALLENGES_PATH = _resolve(CHALLENGES_CANDIDATES)
SOLUTIONS_PATH = _resolve(SOLUTIONS_CANDIDATES)

print("torch:", end=" ")
import torch
print(torch.__version__, "cuda available:", torch.cuda.is_available(), "device count:", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(f"  cuda:{{i}} = {{torch.cuda.get_device_name(i)}}")

challenges = json.loads(Path(CHALLENGES_PATH).read_text())
solutions = json.loads(Path(SOLUTIONS_PATH).read_text())
for task_id in PILOT_TASK_IDS:
    assert task_id in challenges, f"{{task_id}} missing from mounted training challenges"


def start_telemetry_monitor(interval=2.0):
    """Extended version of EXP002-C's gpu_monitor: adds power/temperature
    per GPU and, where psutil is available, host CPU/RAM/disk. Runs for the
    whole notebook lifetime; per-config windows are sliced out afterward the
    same way `build_pilot_notebook.py`'s analysis cell sliced phases."""
    stop_event = threading.Event()

    def _poll():
        with open(MONITOR_LOG, "a") as handle:
            while not stop_event.is_set():
                fields = ["nvidia-smi",
                          "--query-gpu=index,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu",
                          "--format=csv,noheader,nounits"]
                try:
                    gpu_out = subprocess.check_output(fields, text=True).strip().replace("\\n", ";")
                except Exception as exc:
                    gpu_out = f"ERROR:{{exc}}"
                host = ""
                if HAVE_PSUTIL:
                    try:
                        cpu = psutil.cpu_percent(interval=None)
                        mem = psutil.virtual_memory()
                        disk = psutil.disk_usage(str(RUN_DIR))
                        host = f"cpu={{cpu}};ram_used_mib={{mem.used // (1024*1024)}};ram_total_mib={{mem.total // (1024*1024)}};disk_used_gib={{disk.used / (1024**3):.2f}}"
                    except Exception as exc:
                        host = f"ERROR:{{exc}}"
                handle.write(f"{{time.time()}}|gpu:{{gpu_out}}|host:{{host}}\\n")
                handle.flush()
                stop_event.wait(interval)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
    return stop_event, thread


def launch_task(task_id, device, config_name):
    """One `solve_task_cli.py` subprocess. Returns (proc, out_path, log_handle, log_path)
    so the caller can track PID, poll liveness, and read the log tail on failure."""
    out_path = ARCHIVE_DIR / f"{{config_name}}_{{task_id}}.json"
    log_path = ARCHIVE_DIR / f"{{config_name}}_{{task_id}}.log"
    log_handle = open(log_path, "w")
    proc = subprocess.Popen(
        [
            sys.executable,
            "solve_task_cli.py",
            "--task-id", task_id,
            "--challenges", CHALLENGES_PATH,
            "--out", str(out_path),
            "--n-iterations", "2000",
            "--time-limit-s", str(TIME_LIMIT_S),
            "--device", device,
        ],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc, out_path, log_handle, log_path


def _log_tail(log_path, n_chars=2000):
    try:
        text = log_path.read_text()
        return text[-n_chars:]
    except Exception:
        return "<unreadable>"


def run_config(name, launches, time_limit_s):
    """Launches every (task_id, device) in `launches` simultaneously (one
    subprocess each), tracks PID/start/end per process, watches for the
    early-abort conditions (a process still alive well past its own
    time_limit_s deadline — a genuine stall, since `solve_task_cli.py`
    checks its own deadline once per training step and should self-exit at
    or shortly after `time_limit_s` regardless of concurrency level — or
    critical system RAM), and aborts only this config (killing its own
    remaining processes) if triggered — never the whole kernel.

    Does NOT use `out_path`'s existence/size as a progress signal:
    `solve_task_cli.py` writes its output file exactly once, after the
    training loop finishes, not incrementally — treating "no file yet" as
    "stalled" would fire on every normal in-progress run."""
    config_start = time.time()
    handles = []
    for task_id, device in launches:
        proc, out_path, log_handle, log_path = launch_task(task_id, device, name)
        handles.append({{
            "task_id": task_id, "device": device, "pid": proc.pid,
            "proc": proc, "out_path": out_path, "log_handle": log_handle,
            "log_path": log_path, "start_time": time.time(), "end_time": None,
            "returncode": None,
        }})
    print(f"config {{name}}: launched {{len(handles)}} processes: " +
          ", ".join(f"{{h['task_id']}}@{{h['device']}}(pid={{h['pid']}})" for h in handles))

    aborted = False
    abort_reason = None
    last_abort_check = time.time()
    stall_deadline = config_start + time_limit_s + 1200  # 20 min grace past every process's own deadline

    while any(h["returncode"] is None for h in handles):
        time.sleep(5)
        for h in handles:
            if h["returncode"] is not None:
                continue
            rc = h["proc"].poll()
            if rc is not None:
                h["returncode"] = rc
                h["end_time"] = time.time()
                h["log_handle"].close()

        # Early-abort checks, at most every 30s.
        if time.time() - last_abort_check > 30:
            still_running = [h for h in handles if h["returncode"] is None]
            if still_running and time.time() > stall_deadline:
                # A process outlived its own time_limit_s by 20+ minutes:
                # it did not self-terminate on schedule, a genuine stall.
                aborted = True
                abort_reason = "process still alive 20+ minutes past its own time_limit_s deadline"
            if HAVE_PSUTIL:
                ram_pct = psutil.virtual_memory().percent
                if ram_pct > 95:
                    aborted = True
                    abort_reason = f"system RAM critically exhausted ({{ram_pct}}%)"
            last_abort_check = time.time()

        if aborted:
            for h in handles:
                if h["returncode"] is None:
                    h["proc"].kill()
                    h["returncode"] = "killed_on_abort"
                    h["end_time"] = time.time()
                    h["log_handle"].close()
            break

    config_wall_s = time.time() - config_start

    results = []
    for h in handles:
        entry = {{
            "task_id": h["task_id"], "device": h["device"], "pid": h["pid"],
            "start_time": h["start_time"], "end_time": h["end_time"],
            "wall_clock_s": (h["end_time"] or time.time()) - h["start_time"],
            "returncode": h["returncode"],
        }}
        if h["returncode"] == 0 and h["out_path"].exists():
            entry["result"] = json.loads(h["out_path"].read_text())
        else:
            entry["failed"] = True
            entry["oom"] = "out of memory" in _log_tail(h["log_path"]).lower()
            entry["log_tail"] = _log_tail(h["log_path"])
        results.append(entry)

    record = {{
        "config": name,
        "wall_clock_s": config_wall_s,
        "aborted": aborted,
        "abort_reason": abort_reason,
        "processes": results,
    }}
    (RUN_DIR / f"config_{{name}}.json").write_text(json.dumps(record, indent=2))
    print(f"config {{name}}: {{config_wall_s:.1f}}s wall clock, aborted={{aborted}}"
          + (f" ({{abort_reason}})" if aborted else ""))
    return record


telemetry_stop, telemetry_thread = start_telemetry_monitor()
'''


def _config_cell(name: str) -> str:
    launches = CONFIGS[name]
    return (
        f"# Configuration {name}: {len([d for _, d in launches if d == 'cuda:0'])} on GPU0, "
        f"{len([d for _, d in launches if d == 'cuda:1'])} on GPU1, all launched simultaneously.\n"
        f"{name.lower()}_launches = {json.dumps(launches)}\n"
        f'{name.lower()}_record = run_config("{name}", {name.lower()}_launches, TIME_LIMIT_S)\n'
    )


ANALYSIS_SOURCE = '''# Final analysis — same metric definitions as EXP002-C's own analysis cell
# (grid_digest, singleton detection, oracle coverage), extended with the
# throughput/resource metrics this pilot's objectives require.
import hashlib
import statistics

telemetry_stop.set()
telemetry_thread.join(timeout=5)


def grid_digest(grid):
    return hashlib.sha1(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()[:16]


def analyse_config(record):
    stats = {"config": record["config"], "wall_clock_s": record["wall_clock_s"],
              "aborted": record["aborted"], "abort_reason": record["abort_reason"]}
    total_candidates = total_unique = total_test_indices = singleton_test_indices = oracle_hits = 0
    per_task = {}
    failures = []
    for entry in record["processes"]:
        task_id = entry["task_id"]
        if entry.get("failed"):
            failures.append({"task_id": task_id, "returncode": entry["returncode"],
                              "oom": entry.get("oom", False), "log_tail": entry.get("log_tail", "")})
            continue
        result = entry["result"]
        if result.get("timed_out"):
            pass  # expected at the 2400s cap, not a failure (see BASELINE_SPEC.md)
        n_test = result["n_test"]
        truth = solutions[task_id]
        per_index_shas = [set() for _ in range(n_test)]
        per_index_hit = [False] * n_test
        for candidate in result["candidates"]:
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
        per_task[task_id] = {
            "device": entry["device"], "pid": entry["pid"],
            "wall_clock_s": entry["wall_clock_s"],
            "steps_run": result["steps_run"], "timed_out": result["timed_out"],
            "peak_memory_bytes": result["peak_memory_bytes"],
            "n_candidates": len(result["candidates"]),
            "steps_per_s": result["steps_run"] / entry["wall_clock_s"] if entry["wall_clock_s"] else None,
        }

    n_completed = len(per_task)
    stats.update({
        "n_completed": n_completed,
        "n_failed": len(failures),
        "failures": failures,
        "total_candidates": total_candidates,
        "total_unique_candidates": total_unique,
        "total_test_indices": total_test_indices,
        "singleton_test_indices": singleton_test_indices,
        "singleton_frequency": singleton_test_indices / total_test_indices if total_test_indices else None,
        "candidate_oracle_coverage": oracle_hits / total_test_indices if total_test_indices else None,
        "completed_tasks_per_wall_clock_hour": n_completed / (record["wall_clock_s"] / 3600) if record["wall_clock_s"] else None,
        "gpu_hours": sum(e["wall_clock_s"] for e in record["processes"]) / 3600,
        "per_task": per_task,
    })
    return stats


report = {
    "experiment": "EXP002-C2 oversubscription pilot",
    "pilot_sample": PILOT_TASK_IDS,
    "time_limit_s": TIME_LIMIT_S,
    "configs": {name: analyse_config(json.loads((RUN_DIR / f"config_{name}.json").read_text()))
                for name in ("C3", "C4")},
    "telemetry_log": str(MONITOR_LOG),
}
(RUN_DIR / "c3c4_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
print(json.dumps(report, indent=2, sort_keys=True))
'''


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = [
        _md_cell(
            "# EXP002-C2 oversubscription and throughput pilot\n\n"
            "Runs the same 5 preregistered ARC-AGI-2 training tasks "
            "(`experiments/EXP002C/pilot_sample.json`) at two new "
            "concurrency levels, C3 (3 processes/GPU) and C4 (4 "
            "processes/GPU), against the frozen CompressARC solver path. "
            "C1 (1 process/GPU) is reused from "
            "`experiments/EXP002C/PILOT_RESULTS.md`, not rerun. See "
            "`experiments/EXP002C2/PLAN.md` and `BASELINE_SPEC.md` for the "
            "full freeze list and GPU assignment reasoning."
        ),
    ]
    for name in VENDORED_MODULES:
        cells.append(_writefile_cell(name, (COMPRESSARC_DIR / name).read_text()))
    cells.append(_writefile_cell("solve_task_cli.py", DRIVER.read_text()))
    cells.append(_code_cell(SETUP_SOURCE))
    cells.append(_code_cell(_config_cell("C3")))
    cells.append(_code_cell(_config_cell("C4")))
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
