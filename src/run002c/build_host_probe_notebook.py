"""Build the EXP002-C3 host-topology probe Kaggle notebook.

Metadata-only: no CompressARC, no task solving, no GPU compute beyond
`torch.cuda`'s own device-enumeration calls. Answers the question
`experiments/EXP002C3/PLAN.md` Q1 depends on before B1/B2 can be designed
for real: what CPU/thread/affinity/cgroup limits does the Kaggle 2xT4
container actually expose, and are numerical libraries defaulting to large
per-process thread pools. Run `python -m src.run002c.build_host_probe_notebook`
to regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "kaggle" / "exp002c3_host_probe"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "exp002c3_host_probe.ipynb"


def _code_cell(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source}


def _md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


PROBE_SOURCE = r'''import json
import os
import platform
import subprocess
import sys
from pathlib import Path

report = {}

# --- logical / physical CPU counts ---
report["os_cpu_count"] = os.cpu_count()
try:
    report["sched_affinity_count"] = len(os.sched_getaffinity(0))
    report["sched_affinity_set"] = sorted(os.sched_getaffinity(0))
except AttributeError:
    report["sched_affinity_count"] = None
    report["sched_affinity_set"] = None

try:
    import psutil
    report["psutil_logical_cpu_count"] = psutil.cpu_count(logical=True)
    report["psutil_physical_cpu_count"] = psutil.cpu_count(logical=False)
    report["load_average"] = os.getloadavg()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    report["ram_total_mib"] = mem.total // (1024 * 1024)
    report["ram_available_mib"] = mem.available // (1024 * 1024)
    report["swap_total_mib"] = swap.total // (1024 * 1024)
except ImportError:
    report["psutil_available"] = False

# --- cgroup CPU quota (v1 and v2 paths, whichever exists) ---
def _read(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None

cgroup_v2_max = _read("/sys/fs/cgroup/cpu.max")
cgroup_v1_quota = _read("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
cgroup_v1_period = _read("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
report["cgroup_v2_cpu_max"] = cgroup_v2_max
report["cgroup_v1_cfs_quota_us"] = cgroup_v1_quota
report["cgroup_v1_cfs_period_us"] = cgroup_v1_period
if cgroup_v2_max and cgroup_v2_max != "max":
    quota, period = cgroup_v2_max.split()
    report["cgroup_v2_effective_cpus"] = int(quota) / int(period)
elif cgroup_v1_quota and cgroup_v1_period and int(cgroup_v1_quota) > 0:
    report["cgroup_v1_effective_cpus"] = int(cgroup_v1_quota) / int(cgroup_v1_period)

report["cpuset_cpus"] = _read("/sys/fs/cgroup/cpuset.cpus")
report["cpuset_cpus_v1"] = _read("/sys/fs/cgroup/cpuset/cpuset.cpus")

# --- NUMA topology, if available ---
try:
    numa_out = subprocess.run(["numactl", "--hardware"], capture_output=True, text=True, timeout=10)
    report["numa_hardware"] = numa_out.stdout if numa_out.returncode == 0 else f"numactl exit {numa_out.returncode}: {numa_out.stderr}"
except FileNotFoundError:
    report["numa_hardware"] = "numactl not installed"
except Exception as exc:
    report["numa_hardware"] = f"error: {exc}"

# --- environment: thread-pool env vars as inherited by this process by default ---
for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
            "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
    report[f"env_{var}"] = os.environ.get(var)

report["python_version"] = sys.version
report["multiprocessing_start_method"] = __import__("multiprocessing").get_start_method(allow_none=True)
import multiprocessing
report["multiprocessing_default_start_method"] = multiprocessing.get_start_method()

# --- PyTorch CPU-thread defaults ---
try:
    import torch
    report["torch_version"] = torch.__version__
    report["torch_num_threads_default"] = torch.get_num_threads()
    report["torch_num_interop_threads_default"] = torch.get_num_interop_threads()
    report["torch_cuda_available"] = torch.cuda.is_available()
    report["torch_cuda_device_count"] = torch.cuda.device_count()
    report["torch_cuda_devices"] = [
        {
            "index": i,
            "name": torch.cuda.get_device_name(i),
            "total_memory_mib": torch.cuda.get_device_properties(i).total_memory // (1024 * 1024),
        }
        for i in range(torch.cuda.device_count())
    ]
except Exception as exc:
    report["torch_probe_error"] = str(exc)

# --- nvidia-smi topology matrix, if available (CPU-GPU affinity where reported) ---
try:
    topo = subprocess.run(["nvidia-smi", "topo", "-m"], capture_output=True, text=True, timeout=10)
    report["nvidia_smi_topo"] = topo.stdout if topo.returncode == 0 else f"exit {topo.returncode}: {topo.stderr}"
except FileNotFoundError:
    report["nvidia_smi_topo"] = "nvidia-smi not found"
except Exception as exc:
    report["nvidia_smi_topo"] = f"error: {exc}"

# --- whether numerical libraries spawn large thread pools unprompted: measured,
# not inferred, by launching a throwaway subprocess with a clean env and reading
# torch's own reported thread count back ---
probe_script = (
    "import torch, json; "
    "print(json.dumps({'num_threads': torch.get_num_threads(), "
    "'num_interop_threads': torch.get_num_interop_threads()}))"
)
clean_env_result = subprocess.run(
    [sys.executable, "-c", probe_script],
    capture_output=True, text=True, timeout=60,
    env={k: v for k, v in os.environ.items() if "THREADS" not in k},
)
report["torch_threads_with_env_vars_stripped"] = (
    json.loads(clean_env_result.stdout) if clean_env_result.returncode == 0 else clean_env_result.stderr
)

out_path = Path("/kaggle/working/host_topology_report.json")
out_path.write_text(json.dumps(report, indent=2, default=str))
print(json.dumps(report, indent=2, default=str))
'''


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = [
        _md_cell(
            "# EXP002-C3 host-topology probe\n\n"
            "Metadata-only: records the Kaggle 2xT4 container's effective "
            "CPU quota, affinity, cgroup limits, NUMA topology, thread-pool "
            "defaults and GPU topology, so `experiments/EXP002C3/"
            "BASELINE_SPEC.md`'s B2 concurrency rule can be evaluated "
            "against real numbers instead of `os.cpu_count()` alone. "
            "No CompressARC code runs in this kernel."
        ),
        _code_cell(PROBE_SOURCE),
    ]
    notebook = {
        "metadata": {
            "kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
            "kaggle": {
                "accelerator": "nvidiaTeslaT4x2",
                "dataSources": [],
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
