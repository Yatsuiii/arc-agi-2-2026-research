"""Solve one ARC-AGI-2 training task with vendored CompressARC, one process.

Run as a subprocess (one task per invocation), the same isolation upstream's
own `parallel_train.py` uses, so a crashed or OOM task cannot corrupt another
task's CUDA state. Not invoked by anything yet — `acquire_corpus.py` will call
this once EXP002-C is approved to run
(`experiments/EXP002C/PLAN.md` §12, gated on explicit approval).

Writes one JSON record per task: the two grids CompressARC's own selector
picked (`attempt_1`/`attempt_2`, matching the competition submission shape)
plus every distinct grid it produced along the way
(`third_party/compressarc/NOTICE.md`'s `solution_grids` instrumentation),
each with its accumulated log-sum-exp score. This is the full candidate set,
not just the top two, which is what `src/harness/` needs to compute anything
beyond the frozen selector's own choice.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

COMPRESSARC_DIR = Path(__file__).resolve().parents[2] / "third_party" / "compressarc"
sys.path.insert(0, str(COMPRESSARC_DIR))

DEFAULT_N_ITERATIONS = 2000
DEFAULT_LR = 0.01
DEFAULT_BETAS = (0.5, 0.9)


def solve(task_id: str, problem: dict, n_iterations: int, time_limit_s: float, device: str) -> dict:
    import torch

    import arc_compressor
    import preprocessing
    import solution_selection
    import train

    torch.set_default_device(device)
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()

    task = preprocessing.Task(task_id, problem, None)
    model = arc_compressor.ARCCompressor(task)
    optimizer = torch.optim.Adam(model.weights_list, lr=DEFAULT_LR, betas=DEFAULT_BETAS)
    logger = solution_selection.Logger(task)
    logger.solution_most_frequent = tuple(((0, 0), (0, 0)) for _ in range(task.n_test))
    logger.solution_second_most_frequent = tuple(((0, 0), (0, 0)) for _ in range(task.n_test))

    start = time.time()
    deadline = start + time_limit_s
    steps_run = 0
    for train_step in range(n_iterations):
        train.take_step(task, model, optimizer, train_step, logger)
        steps_run = train_step + 1
        if time.time() > deadline:
            break
    elapsed_s = time.time() - start

    peak_memory_bytes = torch.cuda.max_memory_allocated() if device.startswith("cuda") else 0

    candidates = [
        {
            "grid": [[int(cell) for cell in row] for row in grid],
            "accumulated_score": logger.solution_hashes_count[hashed],
        }
        for hashed, grid in logger.solution_grids.items()
    ]
    attempt_1 = [list(row) for row in logger.solution_most_frequent]
    attempt_2 = [list(row) for row in logger.solution_second_most_frequent]

    return {
        "task_id": task_id,
        "n_test": task.n_test,
        "steps_run": steps_run,
        "elapsed_s": elapsed_s,
        "peak_memory_bytes": peak_memory_bytes,
        "device": device,
        "attempt_1": attempt_1,
        "attempt_2": attempt_2,
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--challenges", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--n-iterations", type=int, default=DEFAULT_N_ITERATIONS)
    parser.add_argument("--time-limit-s", type=float, default=3600.0)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    problems = json.loads(args.challenges.read_text())
    problem = problems[args.task_id]
    result = solve(args.task_id, problem, args.n_iterations, args.time_limit_s, args.device)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result))


if __name__ == "__main__":
    main()
