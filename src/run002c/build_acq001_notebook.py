"""Build the ACQ-001 production acquisition Kaggle notebook.

Frozen C3 exactly (`experiments/EXP002C3/RESULTS.md`'s verdict: KEEP FROZEN
C3 — 3 processes/T4, plain library thread defaults, no explicit CPU
affinity, no reduced concurrency): the same `%%writefile`-verbatim
discipline every EXP002-C/C2/C3 notebook builder already uses for
`solve_task_cli.py` and the vendored CompressARC modules, extended to the
orchestration layer itself — `src/run002c/acquire_shard.py` (checkpointed,
retrying, archive-ingesting) is embedded verbatim rather than re-derived
as an inline string, so the code unit-tested locally
(`tests/run002c/test_acquire_shard.py`) is byte-identical to what runs on
Kaggle.

Run `python -m src.run002c.build_acq001_notebook --shard A` (or `--shard
B`, or `--shard VALIDATION` for the bounded 5-test-index production-path
check) to regenerate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPRESSARC_DIR = ROOT / "third_party" / "compressarc"
DRIVER = ROOT / "src" / "run002c" / "solve_task_cli.py"
ORCHESTRATOR = ROOT / "src" / "run002c" / "acquire_shard.py"
ARCHIVE_MODULE = ROOT / "src" / "run001" / "archive.py"
SHARD_DIR = ROOT / "artifacts" / "ACQ001"
OUTPUT_ROOT = ROOT / "kaggle" / "acq001"

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


def _code_cell(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source}


def _md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def _writefile_cell(path: str, content: str) -> dict:
    text = content if content.endswith("\n") else content + "\n"
    return _code_cell(f"%%writefile {path}\n{text}")


def _load_shard(name: str) -> dict:
    path = SHARD_DIR / f"shard_{name.lower()}.json"
    return json.loads(path.read_text())


RUNNER_SOURCE = '''import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, "/kaggle/working")
from acquire_shard import ProcessLauncher, ingest_archive, run_shard

try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False
    print("psutil not available: CPU/RAM/disk telemetry will be omitted, not fabricated")

RUN_DIR = Path("/kaggle/working/acq001_{shard_lower}")
RUN_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR = RUN_DIR / "per_task"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
MONITOR_LOG = RUN_DIR / "telemetry_monitor.log"
CHECKPOINT_PATH = RUN_DIR / "checkpoint_state.json"

SHARD_NAME = "{shard_name}"
TASK_IDS = {task_ids}
SLOTS_PER_GPU = {slots_per_gpu}
TIME_LIMIT_S = {time_limit_s}
N_ITERATIONS = {n_iterations}

CHALLENGES_CANDIDATES = (
    "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json",
    "/kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json",
)


def _resolve(candidates):
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(f"none of {{candidates}} exist")


CHALLENGES_PATH = _resolve(CHALLENGES_CANDIDATES)

print("torch:", end=" ")
import torch
print(torch.__version__, "cuda available:", torch.cuda.is_available(), "device count:", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(f"  cuda:{{i}} = {{torch.cuda.get_device_name(i)}}")

challenges = json.loads(Path(CHALLENGES_PATH).read_text())
for task_id in TASK_IDS:
    assert task_id in challenges, f"{{task_id}} missing from mounted training challenges"


def start_telemetry_monitor(interval=2.0):
    import subprocess
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


telemetry_stop, telemetry_thread = start_telemetry_monitor()

launcher = ProcessLauncher(
    solve_script=Path("solve_task_cli.py"), challenges_path=CHALLENGES_PATH,
    archive_dir=ARCHIVE_DIR, n_iterations=N_ITERATIONS, time_limit_s=TIME_LIMIT_S,
)
shard_result = run_shard(TASK_IDS, CHECKPOINT_PATH, launcher,
                          slots_per_gpu=SLOTS_PER_GPU, time_limit_s=TIME_LIMIT_S)

telemetry_stop.set()
telemetry_thread.join(timeout=5)

archive_summary = ingest_archive(
    TASK_IDS, shard_result["checkpoint"], ARCHIVE_DIR, RUN_DIR, SHARD_NAME,
    slots_per_gpu=SLOTS_PER_GPU, time_limit_s=TIME_LIMIT_S, n_iterations=N_ITERATIONS,
)
print(json.dumps(archive_summary, indent=2))
'''


def build(shard_name: str, task_ids_override: list[str] | None = None, time_limit_override: float | None = None) -> dict:
    if task_ids_override is not None:
        task_ids = task_ids_override
    else:
        task_ids = _load_shard(shard_name)["task_ids"]
    time_limit_s = time_limit_override if time_limit_override is not None else 2400
    n_iterations = 2000

    output_dir = OUTPUT_ROOT / f"shard_{shard_name.lower()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_notebook = output_dir / f"acq001_shard_{shard_name.lower()}.ipynb"

    runner_source = RUNNER_SOURCE.format(
        shard_lower=shard_name.lower(),
        shard_name=shard_name,
        task_ids=json.dumps(task_ids),
        slots_per_gpu=3,
        time_limit_s=time_limit_s,
        n_iterations=n_iterations,
    )

    cells = [
        _md_cell(
            f"# ACQ-001 production acquisition — Shard {shard_name}\n\n"
            f"Frozen C3 (3 processes/T4, plain thread defaults, no affinity — "
            "`experiments/EXP002C3/RESULTS.md`'s verdict). "
            f"{len(task_ids)} tasks, time_limit_s={time_limit_s}. "
            "`solve_task_cli.py`, every vendored CompressARC module, and "
            "`acquire_shard.py`'s orchestration logic are embedded verbatim — "
            "byte-identical to the locally unit-tested source in this repository."
        ),
    ]
    for name in VENDORED_MODULES:
        cells.append(_writefile_cell(name, (COMPRESSARC_DIR / name).read_text()))
    cells.append(_writefile_cell("solve_task_cli.py", DRIVER.read_text()))
    cells.append(_writefile_cell("archive.py", ARCHIVE_MODULE.read_text()))
    cells.append(_writefile_cell("acquire_shard.py", ORCHESTRATOR.read_text()))
    cells.append(_code_cell(runner_source))

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
    output_notebook.write_text(json.dumps(notebook, indent=1) + "\n")
    return {"cells": len(cells), "path": output_notebook, "n_tasks": len(task_ids)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", required=True, choices=["A", "B"])
    args = parser.parse_args()
    result = build(args.shard)
    print(f"wrote {result['path']} ({result['cells']} cells, {result['n_tasks']} tasks)")


if __name__ == "__main__":
    main()
