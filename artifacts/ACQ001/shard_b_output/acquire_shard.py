"""ACQ-001 production acquisition orchestrator: frozen C3, checkpointed,
retrying, archive-ingesting driver for one shard.

Embedded verbatim into the ACQ-001 Kaggle notebooks via `%%writefile`
(`build_acq001_notebook.py`), so the code that runs on Kaggle is
byte-identical to this file — the same discipline every EXP002-C/C2/C3
notebook builder already uses for `solve_task_cli.py` and the vendored
CompressARC modules. Written as a real, importable module (not only an
f-string notebook cell, unlike the earlier EXP002-C2/C3 orchestration
scripts) specifically so its checkpoint/retry/archive-ingestion logic can
be unit-tested locally, on stubbed subprocess launches, before any Kaggle
GPU time is spent on it — the validation EXP002-C3's B1 wave-2 affinity
bug (an untested boundary condition in orchestration code) showed is worth
doing.

Frozen C3 per `experiments/EXP002C3/RESULTS.md`'s verdict (KEEP FROZEN
C3): 3 processes/T4, plain library thread defaults, no explicit CPU
affinity, no reduced concurrency. `solve_task_cli.py` and every vendored
CompressARC module remain untouched — this module only orchestrates
subprocess launches, checkpointing, retries, and archive ingestion.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SLOTS_PER_GPU = 3  # frozen C3
TIME_LIMIT_S = 2400  # unchanged freeze list value
N_ITERATIONS = 2000  # unchanged freeze list value
MAX_ATTEMPTS = 2  # 1 retry on a genuine crash, not a timeout


def build_waves(task_ids: list[str], slots_per_gpu: int = SLOTS_PER_GPU) -> list[list[tuple[str, str]]]:
    """Deterministic wave plan: `slots_per_gpu` tasks to cuda:0, the next
    `slots_per_gpu` to cuda:1, repeating, in the given list's own order.
    No re-sorting here — task ordering is fixed once, when a shard is
    written (`experiments/ACQ001/SHARDING_PLAN.md`)."""
    waves = []
    i = 0
    while i < len(task_ids):
        chunk = task_ids[i:i + 2 * slots_per_gpu]
        wave = [(t, "cuda:0" if j < slots_per_gpu else "cuda:1") for j, t in enumerate(chunk)]
        waves.append(wave)
        i += 2 * slots_per_gpu
    return waves


def load_checkpoint(checkpoint_path: Path) -> dict:
    if checkpoint_path.exists():
        return json.loads(checkpoint_path.read_text())
    return {}


def save_checkpoint(checkpoint_path: Path, state: dict) -> None:
    checkpoint_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def _log_tail(log_path: Path, n_chars: int = 2000) -> str:
    try:
        return log_path.read_text()[-n_chars:]
    except Exception:
        return "<unreadable>"


class ProcessLauncher:
    """Isolates the one real side effect (`subprocess.Popen`) so tests can
    substitute a fake launcher without touching `run_wave`'s control flow."""

    def __init__(self, solve_script: Path, challenges_path: str, archive_dir: Path,
                 n_iterations: int = N_ITERATIONS, time_limit_s: float = TIME_LIMIT_S):
        self.solve_script = solve_script
        self.challenges_path = challenges_path
        self.archive_dir = archive_dir
        self.n_iterations = n_iterations
        self.time_limit_s = time_limit_s

    def launch(self, task_id: str, device: str):
        out_path = self.archive_dir / f"{task_id}.json"
        log_path = self.archive_dir / f"{task_id}.log"
        log_handle = open(log_path, "w")
        proc = subprocess.Popen(
            [
                sys.executable, str(self.solve_script),
                "--task-id", task_id, "--challenges", self.challenges_path,
                "--out", str(out_path), "--n-iterations", str(self.n_iterations),
                "--time-limit-s", str(self.time_limit_s), "--device", device,
            ],
            stdout=log_handle, stderr=subprocess.STDOUT,
        )
        return proc, out_path, log_handle, log_path


def _launch_wave(launches, checkpoint: dict, launcher) -> list[dict]:
    handles = []
    for task_id, device in launches:
        proc, out_path, log_handle, log_path = launcher.launch(task_id, device)
        handles.append({
            "task_id": task_id, "device": device, "pid": proc.pid, "proc": proc,
            "out_path": out_path, "log_handle": log_handle, "log_path": log_path,
            "start_time": time.time(), "end_time": None, "returncode": None,
            "attempt": checkpoint.get(task_id, {}).get("attempts", 0) + 1,
        })
    return handles


def _poll_wave(handles: list[dict], stall_deadline: float, poll_interval_s: float) -> tuple[bool, str | None]:
    """Blocks until every process exits or a stall/abort condition fires.
    Mutates `handles` in place with returncode/end_time. Returns
    (aborted, abort_reason)."""
    aborted, abort_reason = False, None
    last_abort_check = time.time()
    while any(h["returncode"] is None for h in handles):
        time.sleep(poll_interval_s)
        for h in handles:
            if h["returncode"] is not None:
                continue
            rc = h["proc"].poll()
            if rc is not None:
                h["returncode"] = rc
                h["end_time"] = time.time()
                h["log_handle"].close()

        if time.time() - last_abort_check > 30:
            still_running = any(h["returncode"] is None for h in handles)
            if still_running and time.time() > stall_deadline:
                aborted = True
                abort_reason = "process still alive 20+ minutes past its own time_limit_s deadline"
            last_abort_check = time.time()

        if aborted:
            for h in handles:
                if h["returncode"] is None:
                    h["proc"].kill()
                    h["returncode"] = "killed_on_abort"
                    h["end_time"] = time.time()
                    h["log_handle"].close()
            break
    return aborted, abort_reason


def _score_wave(handles: list[dict], checkpoint: dict, max_attempts: int, aborted: bool) -> list[str]:
    """Updates `checkpoint` in place from each handle's outcome. Returns the
    retry queue (tasks that crashed, not timed out, and have attempts
    left). When the wave itself aborted (a stall or RAM-exhaustion kill,
    `run_shard` stops the whole shard immediately without ever launching a
    retry wave), every unsuccessful task is recorded `failed`, never
    `pending_retry` -- a `pending_retry` status must only exist when a
    retry wave is actually about to run, or the checkpoint would claim a
    retry is coming that never happens."""
    retry_queue = []
    for h in handles:
        task_id = h["task_id"]
        succeeded = h["returncode"] == 0 and h["out_path"].exists()
        if succeeded:
            checkpoint[task_id] = {"status": "complete", "attempts": h["attempt"],
                                    "device": h["device"], "wall_clock_s": h["end_time"] - h["start_time"]}
            continue
        oom = "out of memory" in _log_tail(h["log_path"]).lower()
        if h["attempt"] < max_attempts and not oom and not aborted:
            checkpoint[task_id] = {"status": "pending_retry", "attempts": h["attempt"],
                                    "last_error": _log_tail(h["log_path"], 500)}
            retry_queue.append(task_id)
        else:
            checkpoint[task_id] = {"status": "failed", "attempts": h["attempt"],
                                    "oom": oom, "aborted": aborted,
                                    "last_error": _log_tail(h["log_path"], 2000)}
    return retry_queue


def run_wave(wave_index, launches, checkpoint: dict, launcher, checkpoint_path: Path,
             time_limit_s: float = TIME_LIMIT_S, max_attempts: int = MAX_ATTEMPTS,
             poll_interval_s: float = 5.0) -> tuple[list[str], bool, str | None]:
    """Launches every (task_id, device) in `launches` simultaneously, tracks
    PID/start/end, retries a task once if its process exits nonzero (a
    genuine crash -- a timeout is `returncode == 0` with `timed_out: true`
    in its own output, the expected outcome, not a retry trigger). Persists
    checkpoint state after the wave completes. Returns (retry_queue,
    aborted, abort_reason)."""
    config_start = time.time()
    handles = _launch_wave(launches, checkpoint, launcher)
    print(f"wave {wave_index}: launched {len(handles)} processes: " +
          ", ".join(f"{h['task_id']}@{h['device']}(pid={h['pid']},attempt={h['attempt']})" for h in handles))

    aborted, abort_reason = _poll_wave(handles, config_start + time_limit_s + 1200, poll_interval_s)
    wave_wall_s = time.time() - config_start
    retry_queue = _score_wave(handles, checkpoint, max_attempts, aborted)

    save_checkpoint(checkpoint_path, checkpoint)
    print(f"wave {wave_index}: {wave_wall_s:.1f}s, aborted={aborted}"
          + (f" ({abort_reason})" if aborted else "")
          + (f", retry_queue={retry_queue}" if retry_queue else ""))
    return retry_queue, aborted, abort_reason


def run_shard(task_ids: list[str], checkpoint_path: Path, launcher,
              slots_per_gpu: int = SLOTS_PER_GPU, time_limit_s: float = TIME_LIMIT_S,
              max_attempts: int = MAX_ATTEMPTS, poll_interval_s: float = 5.0) -> dict:
    """Top-level driver: skip already-complete tasks (checkpoint resume),
    run every remaining task in waves, retry crashes once, stop the whole
    shard immediately (not just the wave) if any wave aborts."""
    checkpoint = load_checkpoint(checkpoint_path)
    already_done = {tid for tid, rec in checkpoint.items() if rec.get("status") == "complete"}
    remaining = [t for t in task_ids if t not in already_done]
    print(f"{len(already_done)} already complete, {len(remaining)} remaining")

    waves = build_waves(remaining, slots_per_gpu)
    any_aborted = False
    for wave_index, wave in enumerate(waves):
        retry_queue, aborted, abort_reason = run_wave(
            wave_index, wave, checkpoint, launcher, checkpoint_path,
            time_limit_s=time_limit_s, max_attempts=max_attempts, poll_interval_s=poll_interval_s)
        if aborted:
            any_aborted = True
            print(f"ABORT: wave {wave_index} aborted ({abort_reason}); stopping shard")
            break
        if retry_queue:
            retry_launches = [(t, "cuda:0" if i % 2 == 0 else "cuda:1") for i, t in enumerate(retry_queue)]
            run_wave(f"{wave_index}_retry", retry_launches, checkpoint, launcher, checkpoint_path,
                     time_limit_s=time_limit_s, max_attempts=max_attempts, poll_interval_s=poll_interval_s)

    return {"checkpoint": checkpoint, "any_aborted": any_aborted}


def _ingest_one_task(archive, task_id: str, record: dict, archive_dir: Path, grid_digest) -> bool:
    """Reads one task's `solve_task_cli.py` output and writes it into
    `archive`. Returns whether ingestion succeeded (missing file or
    unparseable JSON are recorded as archive errors, not raised)."""
    out_path = archive_dir / f"{task_id}.json"
    if not out_path.exists():
        archive.record_error(task_id, "archive_ingest", RuntimeError("checkpoint says complete but output file missing"))
        return False
    try:
        result = json.loads(out_path.read_text())
    except json.JSONDecodeError as exc:
        archive.record_error(task_id, "archive_ingest_parse", exc)
        return False

    n_candidates = 0
    for test_index in range(result["n_test"]):
        for candidate in result["candidates"]:
            grid = candidate["grid"][test_index]
            sha1 = grid_digest(grid)
            archive.record_candidate(
                task_id=task_id, test_index=test_index, grid=grid, grid_sha1=sha1,
                solver_branch="compressarc", beam_score=candidate["accumulated_score"],
            )
        for rank, attempt in enumerate((result["attempt_1"], result["attempt_2"]), start=1):
            grid = attempt[test_index]
            archive.record_selection(
                task_id=task_id, test_index=test_index, grid_sha1=grid_digest(grid),
                rank=rank, selected=True, algorithm="compressarc_top2",
            )
        n_candidates += len(result["candidates"])

    archive.flush_task(
        task_id, n_test_inputs=result["n_test"], n_candidates=n_candidates,
        solve_seconds=result["elapsed_s"], hit_time_guard=result["timed_out"],
        peak_mem_train_mib=result["peak_memory_bytes"] / (1024 * 1024),
        gpu_index=record.get("device", ""),
    )
    return True


def ingest_archive(task_ids: list[str], checkpoint: dict, archive_dir: Path, run_dir: Path,
                    shard_name: str, slots_per_gpu: int = SLOTS_PER_GPU,
                    time_limit_s: float = TIME_LIMIT_S, n_iterations: int = N_ITERATIONS) -> dict:
    """Reads every completed per-task JSON and ingests it into the same
    `CandidateArchive` schema RUN-001's own archive uses. Returns a summary
    dict; also writes `completed_tasks.json` and re-saves the checkpoint
    into `run_dir`."""
    try:
        # Repo layout (local tests, `python -m src.run002c...`).
        from src.run001.archive import CandidateArchive, grid_digest
    except ModuleNotFoundError:
        # Kaggle's flat /kaggle/working layout: archive.py is %%writefile'd
        # alongside this module, not under a `src` package (matches
        # `solve_task_cli.py`'s own precedent of a runtime path/import
        # fallback rather than two divergent copies of the same logic).
        from archive import CandidateArchive, grid_digest

    archive = CandidateArchive(
        run_dir / "archive", shard=shard_name,
        manifest={
            "acquisition": "ACQ-001", "shard": shard_name,
            "solver": "CompressARC (vendored + grid-persistence instrumentation)",
            "n_iterations": n_iterations, "time_limit_s": time_limit_s,
            "concurrency": f"C3 frozen: {slots_per_gpu} processes/T4",
            "task_ids": task_ids,
        },
    )

    started = time.time()
    completed_tasks = [
        task_id for task_id, record in sorted(checkpoint.items())
        if record.get("status") == "complete"
        and _ingest_one_task(archive, task_id, record, archive_dir, grid_digest)
    ]

    for task_id, record in sorted(checkpoint.items()):
        if record.get("status") == "failed":
            archive.record_error(task_id, "solve", RuntimeError(record.get("last_error", "")[:500]),
                                  attempts=record.get("attempts"), oom=record.get("oom", False))

    n_failed = sum(1 for r in checkpoint.values() if r.get("status") == "failed")
    archive.write_runtime_summary(
        wall_clock_s=time.time() - started, shard_task_count=len(task_ids),
        n_completed=len(completed_tasks), n_failed=n_failed,
    )

    (run_dir / "completed_tasks.json").write_text(json.dumps(sorted(completed_tasks), indent=2))
    (run_dir / "checkpoint_state.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

    return {"shard": shard_name, "n_tasks": len(task_ids), "n_completed": len(completed_tasks), "n_failed": n_failed}
