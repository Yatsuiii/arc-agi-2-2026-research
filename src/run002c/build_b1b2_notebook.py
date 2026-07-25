"""Build the EXP002-C3 vCPU-aware throughput pilot Kaggle notebook.

Same discipline as `build_c3c4_notebook.py`: every vendored/instrumented
CompressARC module and the unmodified `solve_task_cli.py` driver are
embedded verbatim via `%%writefile` cells, so the code that runs on Kaggle
is byte-identical to what's committed here. `solve_task_cli.py` and every
vendored module are untouched by this experiment — B1/B2 only change
subprocess environment (numerical-library thread caps), CPU affinity, and
process-to-GPU concurrency, all in this orchestration layer. See
`experiments/EXP002C3/BASELINE_SPEC.md` for the exact freeze list, B1
affinity rule, and B2's pre-registered vCPU-derived concurrency rule.

Scope: the same 5 tasks preregistered in `experiments/EXP002C/
pilot_sample.json`, run once as B1 (C3 concurrency + thread caps + affinity)
and once as B2 (vCPU-derived concurrency, computed at runtime from this
kernel's own measured effective CPU quota, per BASELINE_SPEC.md §5's frozen
rule — not tuned after seeing a result). Run
`python -m src.run002c.build_b1b2_notebook` to regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPRESSARC_DIR = ROOT / "third_party" / "compressarc"
DRIVER = ROOT / "src" / "run002c" / "solve_task_cli.py"
PILOT_SAMPLE = ROOT / "experiments" / "EXP002C" / "pilot_sample.json"
OUTPUT_DIR = ROOT / "kaggle" / "exp002c3_b1b2"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "exp002c3_b1b2.ipynb"

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

RUN_DIR = "/kaggle/working/exp002c3_pilot"

# B1 reuses C3's exact GPU assignment (experiments/EXP002C2/BASELINE_SPEC.md
# §3) so the B0-vs-B1 delta isolates the thread-cap/affinity intervention.
B1_TASKS = [
    ("00576224", "cuda:0"),
    ("009d5c81", "cuda:0"),
    ("0520fde7", "cuda:0"),
    ("42f83767", "cuda:1"),
    ("8abad3cf", "cuda:1"),
]
# All 5 task_ids in a fixed order; B2's per-GPU split is computed at
# runtime from the measured effective CPU quota (BASELINE_SPEC.md §5).
ALL_TASK_IDS = ["00576224", "009d5c81", "0520fde7", "42f83767", "8abad3cf"]

TIME_LIMIT_S = 2400  # unchanged from C1/C3/C4 (BASELINE_SPEC.md §2 freeze list)

THREAD_CAP_VARS = (
    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)


def _code_cell(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source}


def _md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def _writefile_cell(path: str, content: str) -> dict:
    text = content if content.endswith("\n") else content + "\n"
    return _code_cell(f"%%writefile {path}\n{text}")


SETUP_SOURCE = f'''import json
import math
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
ALL_TASK_IDS = {json.dumps(ALL_TASK_IDS)}
TIME_LIMIT_S = {TIME_LIMIT_S}
THREAD_CAP_VARS = {json.dumps(list(THREAD_CAP_VARS))}

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


# --- Phase 1 host-topology measurement, done fresh in this kernel so B2's
# concurrency rule is evaluated against this exact run's measured quota,
# not a cross-kernel artifact (BASELINE_SPEC.md §5). ---
def measure_effective_cpu_quota():
    """Most conservative of: cgroup CPU quota (whole cores), sched affinity
    count, psutil logical CPU count. Recorded, not assumed."""
    candidates = []
    os_cpu = os.cpu_count()
    if os_cpu:
        candidates.append(("os_cpu_count", os_cpu))
    try:
        aff = len(os.sched_getaffinity(0))
        candidates.append(("sched_affinity_count", aff))
    except AttributeError:
        pass
    if HAVE_PSUTIL:
        logical = psutil.cpu_count(logical=True)
        if logical:
            candidates.append(("psutil_logical_cpu_count", logical))
    cgroup_v2 = None
    try:
        raw = Path("/sys/fs/cgroup/cpu.max").read_text().strip()
        quota, period = raw.split()
        if quota != "max":
            cgroup_v2 = int(quota) / int(period)
            candidates.append(("cgroup_v2_effective_cpus", cgroup_v2))
    except Exception:
        pass
    cgroup_v1 = None
    try:
        quota = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text().strip())
        period = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text().strip())
        if quota > 0:
            cgroup_v1 = quota / period
            candidates.append(("cgroup_v1_effective_cpus", cgroup_v1))
    except Exception:
        pass
    q = min(v for _, v in candidates) if candidates else 1
    return {{"components": candidates, "Q": max(1, math.floor(q))}}


quota_measurement = measure_effective_cpu_quota()
Q = quota_measurement["Q"]
U = max(1, Q - 1)  # reserve 1 effective CPU for orchestration/telemetry/I/O
W = min(3, max(1, U // 2))  # per-GPU worker count, never exceeding the validated 3/T4 cap
print(f"host CPU quota measurement: {{quota_measurement}}")
print(f"B2 rule: Q={{Q}}, U={{U}}, W={{W}} workers/GPU ({{2 * W}} total slots)")

b2_gpu0 = ALL_TASK_IDS[:W]
b2_gpu1 = ALL_TASK_IDS[W:min(5, 2 * W)]
b2_queue = ALL_TASK_IDS[min(5, 2 * W):]  # tasks queued for a second wave if slots < 5
B2_TASKS = [(t, "cuda:0") for t in b2_gpu0] + [(t, "cuda:1") for t in b2_gpu1]
print(f"B2 wave 1: GPU0={{b2_gpu0}} GPU1={{b2_gpu1}} queued={{b2_queue}}")


def start_telemetry_monitor(interval=2.0):
    """Extends EXP002-C2's monitor with per-core CPU, load average, and
    swap — the additional host-level signals this pilot's CPU-contention
    hypothesis needs."""
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
                        percpu = psutil.cpu_percent(interval=None, percpu=True)
                        mem = psutil.virtual_memory()
                        swap = psutil.swap_memory()
                        disk = psutil.disk_usage(str(RUN_DIR))
                        load1, load5, load15 = os.getloadavg()
                        host = (f"cpu={{cpu}};percpu={{percpu}};load1={{load1}};"
                                f"ram_used_mib={{mem.used // (1024*1024)}};ram_total_mib={{mem.total // (1024*1024)}};"
                                f"swap_used_mib={{swap.used // (1024*1024)}};disk_used_gib={{disk.used / (1024**3):.2f}}")
                    except Exception as exc:
                        host = f"ERROR:{{exc}}"
                handle.write(f"{{time.time()}}|gpu:{{gpu_out}}|host:{{host}}\\n")
                handle.flush()
                stop_event.wait(interval)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
    return stop_event, thread


def launch_task(task_id, device, config_name, thread_cap, core_id):
    """One `solve_task_cli.py` subprocess. `thread_cap`: if not None, sets
    every numerical-library thread-pool env var to that value in the
    child's environment (set before the child interpreter starts, so
    before NumPy/MKL/PyTorch read any of them on import — the child
    process is never mutated after launch for this). `core_id`: if not
    None and the platform supports it, pins the child to that CPU core via
    `os.sched_setaffinity` immediately after the process starts."""
    out_path = ARCHIVE_DIR / f"{{config_name}}_{{task_id}}.json"
    log_path = ARCHIVE_DIR / f"{{config_name}}_{{task_id}}.log"
    log_handle = open(log_path, "w")
    env = os.environ.copy()
    if thread_cap is not None:
        for var in THREAD_CAP_VARS:
            env[var] = str(thread_cap)
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
        env=env,
    )
    realised_affinity = None
    if core_id is not None:
        try:
            os.sched_setaffinity(proc.pid, {{core_id}})
            realised_affinity = sorted(os.sched_getaffinity(proc.pid))
        except (AttributeError, OSError) as exc:
            realised_affinity = f"unsupported_or_failed: {{exc}}"
    return proc, out_path, log_handle, log_path, realised_affinity


def _log_tail(log_path, n_chars=2000):
    try:
        text = log_path.read_text()
        return text[-n_chars:]
    except Exception:
        return "<unreadable>"


def _proc_snapshot(pid):
    """Best-effort per-process telemetry read at completion time: thread
    count, context switches, CPU time. `None` fields mean unavailable
    (process already exited / psutil missing), not zero."""
    if not HAVE_PSUTIL:
        return {{}}
    try:
        p = psutil.Process(pid)
        ctx = p.num_ctx_switches()
        cpu_times = p.cpu_times()
        return {{
            "num_threads": p.num_threads(),
            "voluntary_ctx_switches": ctx.voluntary,
            "involuntary_ctx_switches": ctx.involuntary,
            "cpu_user_s": cpu_times.user,
            "cpu_system_s": cpu_times.system,
        }}
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return {{"note": "process already reaped, snapshot unavailable"}}


def run_config(name, launches, time_limit_s, thread_cap=None, affinity_map=None):
    """`launches`: list of (task_id, device). `thread_cap`: None (B0-style,
    unused here since B0/C3 is reused not rerun) or an int (1 for B1/B2).
    `affinity_map`: dict task_id -> core_id, or None to skip affinity.
    Aborts only this config on a genuine stall (process alive 20+ minutes
    past its own time_limit_s deadline) or critical RAM exhaustion — same
    rule as EXP002-C2's fixed stall check, never using out_path existence
    as a progress signal (solve_task_cli.py writes it once, at the end)."""
    config_start = time.time()
    handles = []
    proc_snapshots_running = {{}}
    for task_id, device in launches:
        core_id = affinity_map.get(task_id) if affinity_map else None
        proc, out_path, log_handle, log_path, realised_affinity = launch_task(
            task_id, device, name, thread_cap, core_id)
        handles.append({{
            "task_id": task_id, "device": device, "pid": proc.pid,
            "proc": proc, "out_path": out_path, "log_handle": log_handle,
            "log_path": log_path, "start_time": time.time(), "end_time": None,
            "returncode": None, "requested_core_id": core_id,
            "realised_affinity": realised_affinity,
        }})
    print(f"config {{name}}: launched {{len(handles)}} processes (thread_cap={{thread_cap}}): " +
          ", ".join(f"{{h['task_id']}}@{{h['device']}}(pid={{h['pid']}},core={{h['requested_core_id']}})" for h in handles))

    aborted = False
    abort_reason = None
    last_abort_check = time.time()
    stall_deadline = config_start + time_limit_s + 1200  # 20 min grace past every process's own deadline

    while any(h["returncode"] is None for h in handles):
        time.sleep(5)
        for h in handles:
            if h["returncode"] is not None:
                continue
            # Snapshot per-process telemetry while still alive; overwritten
            # each poll so the last one before exit is what's kept.
            proc_snapshots_running[h["pid"]] = _proc_snapshot(h["pid"])
            rc = h["proc"].poll()
            if rc is not None:
                h["returncode"] = rc
                h["end_time"] = time.time()
                h["log_handle"].close()

        if time.time() - last_abort_check > 30:
            still_running = [h for h in handles if h["returncode"] is None]
            if still_running and time.time() > stall_deadline:
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
            "requested_core_id": h["requested_core_id"],
            "realised_affinity": h["realised_affinity"],
            "last_proc_snapshot": proc_snapshots_running.get(h["pid"], {{}}),
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
        "thread_cap": thread_cap,
        "quota_measurement": quota_measurement if name == "B2" else None,
        "processes": results,
    }}
    (RUN_DIR / f"config_{{name}}.json").write_text(json.dumps(record, indent=2))
    print(f"config {{name}}: {{config_wall_s:.1f}}s wall clock, aborted={{aborted}}"
          + (f" ({{abort_reason}})" if aborted else ""))
    return record


telemetry_stop, telemetry_thread = start_telemetry_monitor()
'''


def _b1_cell() -> str:
    affinity = {task_id: idx for idx, (task_id, _device) in enumerate(B1_TASKS)}
    return (
        "# B1: same GPU assignment as C3 (experiments/EXP002C2/BASELINE_SPEC.md §3),\n"
        "# thread-capped (1 thread per numerical library) and affinity-pinned,\n"
        "# consecutive core IDs by launch order (BASELINE_SPEC.md §4).\n"
        f"b1_launches = {json.dumps(B1_TASKS)}\n"
        f"b1_affinity = {json.dumps(affinity)}\n"
        'b1_record = run_config("B1", b1_launches, TIME_LIMIT_S, thread_cap=1, affinity_map=b1_affinity)\n'
    )


B2_CELL_SOURCE = '''# B2: vCPU-derived concurrency, computed above from this kernel's own
# measured effective CPU quota (BASELINE_SPEC.md §5's frozen rule — fixed
# before this run, not tuned after seeing B1's result). If slots < 5, the
# remaining tasks queue and launch when a slot frees.
b2_affinity = {task_id: idx for idx, task_id in enumerate(ALL_TASK_IDS[:2 * W])}
b2_record = run_config("B2", B2_TASKS, TIME_LIMIT_S, thread_cap=1, affinity_map=b2_affinity)

b2_all_processes = list(b2_record["processes"])
if b2_queue:
    print(f"B2 wave 2: launching queued tasks {b2_queue} onto freed slots")
    # Simple, deterministic policy: queued tasks reuse GPU0 if W<=len(b2_gpu0)
    # freed a slot there first, else GPU1 — both GPUs are idle by the time
    # wave 1 fully completes (run_config blocks until every wave-1 process
    # exits), so wave 2 always starts uncontended relative to wave 1.
    wave2_launches = [(t, "cuda:0" if i % 2 == 0 else "cuda:1") for i, t in enumerate(b2_queue)]
    wave2_affinity = {t: idx for idx, (t, _d) in enumerate(wave2_launches)}
    b2_wave2_record = run_config("B2_wave2", wave2_launches, TIME_LIMIT_S, thread_cap=1, affinity_map=wave2_affinity)
    b2_all_processes += b2_wave2_record["processes"]
    b2_record["wall_clock_s"] += b2_wave2_record["wall_clock_s"]
    b2_record["processes"] = b2_all_processes
    b2_record["wave2_aborted"] = b2_wave2_record["aborted"]
    b2_record["wave2_abort_reason"] = b2_wave2_record["abort_reason"]
'''


ANALYSIS_SOURCE = '''# Final analysis — same metric definitions as EXP002-C2's own analysis cell,
# extended with per-process CPU/context-switch/affinity fields this pilot's
# CPU-contention hypothesis needs.
import hashlib
import statistics

telemetry_stop.set()
telemetry_thread.join(timeout=5)


def grid_digest(grid):
    return hashlib.sha1(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()[:16]


def analyse_config(record):
    stats = {"config": record["config"], "wall_clock_s": record["wall_clock_s"],
              "aborted": record["aborted"], "abort_reason": record["abort_reason"],
              "thread_cap": record.get("thread_cap"),
              "quota_measurement": record.get("quota_measurement")}
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
            "requested_core_id": entry.get("requested_core_id"),
            "realised_affinity": entry.get("realised_affinity"),
            "last_proc_snapshot": entry.get("last_proc_snapshot", {}),
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
    "experiment": "EXP002-C3 vCPU-aware throughput pilot",
    "pilot_sample": PILOT_TASK_IDS,
    "time_limit_s": TIME_LIMIT_S,
    "host_quota_measurement": quota_measurement,
    "b2_rule": {"Q": Q, "U": U, "W": W, "total_slots": 2 * W},
    "configs": {name: analyse_config(json.loads((RUN_DIR / f"config_{name}.json").read_text()) if name != "B2" else b2_record)
                for name in ("B1", "B2")},
    "telemetry_log": str(MONITOR_LOG),
}
(RUN_DIR / "b1b2_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
print(json.dumps(report, indent=2, sort_keys=True))
'''


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = [
        _md_cell(
            "# EXP002-C3 vCPU-aware throughput pilot\n\n"
            "Runs the same 5 preregistered ARC-AGI-2 training tasks "
            "(`experiments/EXP002C/pilot_sample.json`) as B1 (C3's exact "
            "concurrency and GPU assignment, single-thread numerical-"
            "library caps, CPU affinity) and B2 (concurrency derived at "
            "runtime from this kernel's own measured effective CPU quota, "
            "per `experiments/EXP002C3/BASELINE_SPEC.md` §5's rule, fixed "
            "before this run). B0 (=C3) is reused from "
            "`experiments/EXP002C2/RESULTS.md`, not rerun. "
            "`solve_task_cli.py` and every vendored CompressARC module are "
            "byte-identical to EXP002-C/EXP002-C2 — this experiment only "
            "changes the orchestration layer."
        ),
    ]
    for name in VENDORED_MODULES:
        cells.append(_writefile_cell(name, (COMPRESSARC_DIR / name).read_text()))
    cells.append(_writefile_cell("solve_task_cli.py", DRIVER.read_text()))
    cells.append(_code_cell(SETUP_SOURCE))
    cells.append(_code_cell(_b1_cell()))
    cells.append(_code_cell(B2_CELL_SOURCE))
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
