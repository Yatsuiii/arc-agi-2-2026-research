"""Validate RUN-001 output artifacts after download.

Four independent checks, composed by `validate`: the submission against the
competition contract, the archive against the submission, the bookkeeping files,
and a leakage check that no hidden answer was archived.

Run: `python -m src.run001.validate_outputs <artifact_dir>`
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPETITION = ROOT.parent / "competition_2026" / "extracted"

MAX_DIMENSION = 30
VALID_COLOURS = set(range(10))
ANSWER_FIELDS = ("solution", "ground_truth", "answer", "label", "correct")
PLACEHOLDER = [[0]]


def digest(grid) -> str:
    return hashlib.sha1(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()[:16]


def read_gz_jsonl(path: Path) -> list[dict]:
    """Read a gzip JSONL archive, tolerating a truncated final member."""
    records: list[dict] = []
    if not path.exists():
        return records
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    break
    except Exception:  # noqa: BLE001 - a truncated tail is expected after a kill
        pass
    return records


def _grid_problems(grid, where: str) -> list[str]:
    if not isinstance(grid, list) or not grid:
        return [f"{where}: not a non-empty list"]
    widths = set()
    for row in grid:
        if not isinstance(row, list) or not row:
            return [f"{where}: row is not a non-empty list"]
        widths.add(len(row))
        bad = {c for c in row if c not in VALID_COLOURS}
        if bad:
            return [f"{where}: colours outside 0..9 {sorted(bad)}"]
    problems = []
    if len(widths) > 1:
        problems.append(f"{where}: ragged rows {sorted(widths)}")
    if len(grid) > MAX_DIMENSION or max(widths) > MAX_DIMENSION:
        problems.append(f"{where}: exceeds {MAX_DIMENSION}x{MAX_DIMENSION}")
    return problems


def check_submission(submission: dict, challenges: dict) -> tuple[dict, list[str]]:
    """Submission against the competition contract."""
    problems = []
    missing = sorted(set(challenges) - set(submission))
    extra = sorted(set(submission) - set(challenges))
    if missing:
        problems.append(f"{len(missing)} task ids missing, e.g. {missing[:3]}")
    if extra:
        problems.append(f"{len(extra)} unexpected task ids, e.g. {extra[:3]}")

    placeholder = attempts = 0
    for task_id, entries in submission.items():
        expected = len(challenges.get(task_id, {}).get("test", []))
        if len(entries) != expected:
            problems.append(f"{task_id}: {len(entries)} entries, expected {expected}")
        for index, entry in enumerate(entries):
            if set(entry) != {"attempt_1", "attempt_2"}:
                problems.append(f"{task_id}[{index}]: keys {sorted(entry)}")
                continue
            for attempt, grid in entry.items():
                attempts += 1
                if grid == PLACEHOLDER:
                    placeholder += 1
                elif len(problems) < 20:
                    problems.extend(_grid_problems(grid, f"{task_id}[{index}].{attempt}"))
    stats = {
        "n_tasks_submission": len(submission),
        "n_attempts_total": attempts,
        "n_placeholder_attempts": placeholder,
        "pct_placeholder": round(100 * placeholder / max(attempts, 1), 2),
    }
    return stats, problems


def check_archive(candidates: list[dict], submission: dict) -> tuple[dict, list[str]]:
    """Archive completeness against what was actually submitted."""
    archived: dict[str, set[str]] = defaultdict(set)
    per_task: dict[str, int] = defaultdict(int)
    for record in candidates:
        if record.get("kind") != "candidate":
            continue
        per_task[record.get("task_id", "?")] += 1
        if "grid_sha1" in record:
            archived[record.get("task_id")].add(record["grid_sha1"])

    unmatched = 0
    for task_id, entries in submission.items():
        if task_id not in archived:
            continue
        for entry in entries:
            for grid in entry.values():
                if grid != PLACEHOLDER and digest(grid) not in archived[task_id]:
                    unmatched += 1
    notes = []
    if unmatched:
        notes.append(
            f"{unmatched} submitted grids absent from the archive; expected only if the "
            "run was interrupted between a flush and the submission write"
        )
    return {
        "n_candidate_records": sum(per_task.values()),
        "n_tasks_with_candidates": len(per_task),
        "submission_grids_not_in_archive": unmatched,
    }, notes


def check_bookkeeping(artifact_dir: Path) -> tuple[dict, list[str]]:
    stats: dict[str, object] = {}
    problems = []
    summary = artifact_dir / "task_summary.csv"
    if summary.exists():
        rows = list(csv.DictReader(summary.open()))
        stats["n_task_summary_rows"] = len(rows)
        stats["n_hit_time_guard"] = sum(1 for r in rows if r.get("hit_time_guard") == "1")
    else:
        problems.append("task_summary.csv missing")
    errors = artifact_dir / "errors.jsonl"
    stats["n_errors"] = (
        len([ln for ln in errors.read_text().splitlines() if ln.strip()])
        if errors.exists()
        else 0
    )
    if not (artifact_dir / "run_manifest.json").exists() and not list(
        artifact_dir.glob("run_manifest.*.json")
    ):
        problems.append("no run manifest present")
    return stats, problems


def check_no_leakage(candidates: list[dict]) -> tuple[dict, list[str]]:
    """No archive record may carry a ground-truth field."""
    leaked = [r for r in candidates if any(f in r for f in ANSWER_FIELDS)]
    problems = (
        [f"{len(leaked)} archive records carry an answer-like field"] if leaked else []
    )
    return {"archive_has_answer_fields": len(leaked)}, problems


def validate(artifact_dir: Path) -> dict:
    report: dict[str, object] = {"artifact_dir": str(artifact_dir)}
    submission_path = artifact_dir / "submission.json"
    if not submission_path.exists():
        return {**report, "problems": ["submission.json missing"], "notes": [], "ok": False}
    submission = json.loads(submission_path.read_text())

    runtime = artifact_dir / "runtime_summary.json"
    rerun = bool(json.loads(runtime.read_text()).get("rerun_mode")) if runtime.exists() else False
    split = "test" if rerun else "evaluation"
    challenges = json.loads((COMPETITION / f"arc-agi_{split}_challenges.json").read_text())
    report["split"] = split

    candidates = read_gz_jsonl(artifact_dir / "candidates.jsonl.gz")
    report["n_selection_records"] = len(
        read_gz_jsonl(artifact_dir / "candidates.ranking.jsonl.gz")
    )

    problems: list[str] = []
    notes: list[str] = []

    # Each check reports either hard problems (fail the run) or soft notes
    # (record but do not fail). Which is which is a property of the check, so it
    # is stated here rather than inferred from the returned keys.
    for severity, (stats, found) in (
        ("problem", check_submission(submission, challenges)),
        ("note", check_archive(candidates, submission)),
        ("problem", check_bookkeeping(artifact_dir)),
        ("problem", check_no_leakage(candidates)),
    ):
        report.update(stats)
        (problems if severity == "problem" else notes).extend(found)

    covered = int(report.get("n_tasks_with_candidates", 0))
    if covered < len(challenges):
        notes.append(
            f"PARTIAL RUN: {covered} of {len(challenges)} tasks produced candidates"
        )
    notes.append(
        "Predicted grids coinciding with ground truth are solver output, not leakage."
    )

    report["problems"] = problems
    report["notes"] = notes
    report["ok"] = not problems
    return report


def main() -> int:
    artifact_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts" / "run001"
    report = validate(artifact_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
