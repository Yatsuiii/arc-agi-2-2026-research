"""EXP002-C driver: acquire a clean ARC-AGI-2 candidate corpus via CompressARC.

NOT executed by this pass. Per `experiments/EXP002C/PLAN.md` §12 and the
project's "no long GPU run without explicit approval" rule
(`paper/EXPERIMENT_REGISTRY.md` rule 1 makes the same point for any run: a
committed preregistration is what makes execution legitimate, and this file
existing is not that commit's execution). Running this module is the GPU run
that needs separate approval — see `experiments/EXP002C/FEASIBILITY.md` for
why it is not run automatically once written.

One subprocess per task (`solve_task_cli.py`), matching upstream's own
process-per-task isolation, so a task's OOM or CUDA fault cannot take down the
whole acquisition run. Writes into `src.run001.archive.CandidateArchive`
(`artifacts/EXP002C/run002c/`), the same schema RUN-001 used, so
`src/analysis/exp002_verifier_eval.py` and `exp002b_verifier_eval.py` read
this corpus with a path change and nothing else.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from src.run001.archive import CandidateArchive, grid_digest

ROOT = Path(__file__).resolve().parents[2]
SOLVE_TASK_CLI = ROOT / "src" / "run002c" / "solve_task_cli.py"
TRAINING_CHALLENGES = (
    ROOT.parent / "competition_2026" / "extracted" / "arc-agi_training_challenges.json"
)


def run_one_task(task_id: str, n_iterations: int, time_limit_s: float, device: str, scratch: Path) -> dict:
    out_path = scratch / f"{task_id}.json"
    subprocess.run(
        [
            sys.executable,
            str(SOLVE_TASK_CLI),
            "--task-id", task_id,
            "--challenges", str(TRAINING_CHALLENGES),
            "--out", str(out_path),
            "--n-iterations", str(n_iterations),
            "--time-limit-s", str(time_limit_s),
            "--device", device,
        ],
        check=True,
    )
    return json.loads(out_path.read_text())


def acquire(sample_path: Path, run_dir: Path, n_iterations: int, time_limit_s: float, device: str) -> None:
    sample = json.loads(sample_path.read_text())
    archive = CandidateArchive(
        run_dir,
        manifest={
            "experiment": "EXP002-C",
            "solver": "CompressARC (vendored + grid-persistence instrumentation)",
            "n_iterations": n_iterations,
            "time_limit_s": time_limit_s,
            "device": device,
            "sample": sample,
        },
    )
    scratch = run_dir / "scratch"
    started = time.time()
    for task_id in sample["task_ids"]:
        try:
            result = run_one_task(task_id, n_iterations, time_limit_s, device, scratch)
        except subprocess.CalledProcessError as exc:
            archive.record_error(task_id, "solve", exc)
            archive.flush_task(task_id)
            continue

        n_candidates = 0
        for test_index in range(result["n_test"]):
            for candidate in result["candidates"]:
                # `candidate["grid"]` is one grid per test example (matches
                # `solution_selection.Logger.solution_grids`' tuple-of-grids
                # shape, see `third_party/compressarc/NOTICE.md`).
                grid = candidate["grid"][test_index]
                sha1 = grid_digest(grid)
                archive.record_candidate(
                    task_id=task_id,
                    test_index=test_index,
                    grid=grid,
                    grid_sha1=sha1,
                    solver_branch="compressarc",
                    beam_score=candidate["accumulated_score"],
                )
            for rank, attempt in enumerate((result["attempt_1"], result["attempt_2"]), start=1):
                grid = attempt[test_index]
                archive.record_selection(
                    task_id=task_id,
                    test_index=test_index,
                    grid_sha1=grid_digest(grid),
                    rank=rank,
                    selected=True,
                    algorithm="compressarc_top2",
                )
            n_candidates += len(result["candidates"])

        archive.flush_task(
            task_id,
            n_test_inputs=result["n_test"],
            n_candidates=n_candidates,
            solve_seconds=result["elapsed_s"],
            peak_mem_train_mib=result["peak_memory_bytes"] / (1024 * 1024),
        )

    archive.write_runtime_summary(wall_clock_s=time.time() - started)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--n-iterations", type=int, default=2000)
    parser.add_argument("--time-limit-s", type=float, default=3600.0)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    acquire(args.sample, args.run_dir, args.n_iterations, args.time_limit_s, args.device)


if __name__ == "__main__":
    main()
