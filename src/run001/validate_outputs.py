"""Validate RUN-001 output artifacts after download.

Composed by `validate` into independent checks, each returning `(stats,
findings)`. A check's severity (does a finding fail the run, or only get
noted) is a property of the check, declared once in `validate`, not inferred
from what it returns.

Checks: submission against the competition contract, candidate-archive
structure, archive-vs-submission cross reference, task_summary reconciliation,
selected-candidate identity against submission, bookkeeping files, and a
leakage check that no hidden answer was archived. `classify_run` turns the
combined report into one of COMPLETE / PARTIAL / TIMED_OUT / FAILED.

Run: `python -m src.run001.validate_outputs <artifact_dir> [--kernel-status S]`
"""

from __future__ import annotations

import argparse
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
CANDIDATE_REQUIRED_FIELDS = ("task_id", "grid_sha1")
SELECTION_REQUIRED_FIELDS = ("task_id", "grid_sha1", "rank_after_aggregation")
FAILED_KERNEL_STATUSES = {"ERROR", "CANCELLED", "CANCEL_REQUESTED"}
NONTERMINAL_KERNEL_STATUSES = {"RUNNING", "QUEUED"}


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


def check_submission_schema(submission: dict, challenges: dict) -> tuple[dict, list[str]]:
    """Submission against the 2026 competition contract.

    Contract: one entry per task in `challenges`, one `{attempt_1, attempt_2}`
    pair per test input, each attempt a well-formed grid (or the notebook's
    own `[[0]]` placeholder for a task that never finished).
    """
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


def check_candidates_structure(candidates: list[dict]) -> tuple[dict, list[str]]:
    """Structural validation of archive records, from either archive file.

    Every line must declare a `kind` and carry that kind's required fields
    (`src/run001/archive.py` schema). This is independent of whether the
    grids happen to match anything; it just checks the archive is legible.
    Callers pass the union of `candidates.jsonl.gz` and
    `candidates.ranking.jsonl.gz` records so both files get checked.
    """
    n_candidate = n_selection = n_malformed = 0
    bad_examples: list[str] = []
    for record in candidates:
        kind = record.get("kind")
        if kind == "candidate":
            n_candidate += 1
            required = CANDIDATE_REQUIRED_FIELDS
        elif kind == "selection":
            n_selection += 1
            required = SELECTION_REQUIRED_FIELDS
        else:
            n_malformed += 1
            if len(bad_examples) < 5:
                bad_examples.append(f"unknown kind {kind!r}")
            continue
        missing = [f for f in required if f not in record]
        if missing:
            n_malformed += 1
            if len(bad_examples) < 5:
                bad_examples.append(f"{kind} record missing {missing}")
    problems = [f"{n_malformed} malformed records, e.g. {bad_examples}"] if n_malformed else []
    stats = {
        "n_candidate_kind_records": n_candidate,
        "n_selection_kind_records": n_selection,
        "n_malformed_records": n_malformed,
    }
    return stats, problems


def check_archive_vs_submission(candidates: list[dict], submission: dict) -> tuple[dict, list[str]]:
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


def check_task_summary_reconciliation(
    candidates: list[dict], task_summary_rows: list[dict]
) -> tuple[dict, list[str]]:
    """Reconcile `task_summary.csv`'s own record counts against the archive.

    Each summary row was written by `flush_task` with `n_records` equal to
    the number of candidate+selection records buffered for that task at flush
    time. A mismatch means the archive was truncated after that flush (or,
    for the opposite sign, cannot happen without a bug) — either way it marks
    that task's data as not fully trustworthy.
    """
    actual_counts: dict[str, int] = defaultdict(int)
    for record in candidates:
        task_id = record.get("task_id")
        if task_id is not None:
            actual_counts[task_id] += 1

    mismatched: list[str] = []
    corrupted_tasks: list[str] = []
    for row in task_summary_rows:
        task_id = row.get("task_id")
        expected = int(row.get("n_records") or 0)
        actual = actual_counts.get(task_id, 0)
        if actual != expected:
            corrupted_tasks.append(task_id)
            if len(mismatched) < 10:
                mismatched.append(f"{task_id}: summary says {expected}, archive has {actual}")

    problems = (
        [f"{len(corrupted_tasks)} tasks disagree with task_summary.csv, e.g. {mismatched}"]
        if corrupted_tasks
        else []
    )
    return {
        "n_task_summary_rows_reconciled": len(task_summary_rows),
        "n_tasks_corrupted_or_truncated": len(corrupted_tasks),
    }, problems


def check_selected_matches_submission(
    candidates: list[dict], submission: dict
) -> tuple[dict, list[str]]:
    """Every non-placeholder submitted grid must be a record the selector marked `selected`.

    Selection records carry only `grid_sha1` (`INSTRUMENTATION_DIFF.md` cell
    8), so this compares digests, not full grids. It cannot verify which
    attempt slot a given rank landed in — the archive does not record that
    mapping — only that the submitted grid was among the selector's picks for
    that task and test index.
    """
    selected_by_task_test: dict[tuple, set[str]] = defaultdict(set)
    for record in candidates:
        if record.get("kind") != "selection" or not record.get("selected"):
            continue
        key = (record.get("task_id"), record.get("test_index"))
        selected_by_task_test[key].add(record.get("grid_sha1"))

    checked = mismatched = 0
    examples: list[str] = []
    for task_id, entries in submission.items():
        for test_index, entry in enumerate(entries):
            expected = selected_by_task_test.get((task_id, test_index))
            if expected is None:
                continue  # no selection records for this task/test index to check against
            for attempt, grid in entry.items():
                if grid == PLACEHOLDER:
                    continue
                checked += 1
                if digest(grid) not in expected:
                    mismatched += 1
                    if len(examples) < 5:
                        examples.append(f"{task_id}[{test_index}].{attempt}")

    notes = (
        [f"{mismatched} of {checked} submitted grids not found among that task's selected set, "
         f"e.g. {examples}"]
        if mismatched
        else []
    )
    return {
        "n_submitted_grids_checked_against_selection": checked,
        "n_selected_mismatches": mismatched,
    }, notes


def check_bookkeeping(artifact_dir: Path) -> tuple[dict, list[dict], list[str]]:
    """Bookkeeping files. Returns stats, the parsed task_summary rows, and problems."""
    stats: dict[str, object] = {}
    problems = []
    rows: list[dict] = []
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
    return stats, rows, problems


def check_no_leakage(candidates: list[dict]) -> tuple[dict, list[str]]:
    """No archive record may carry a ground-truth field."""
    leaked = [r for r in candidates if any(f in r for f in ANSWER_FIELDS)]
    problems = (
        [f"{len(leaked)} archive records carry an answer-like field"] if leaked else []
    )
    return {"archive_has_answer_fields": len(leaked)}, problems


def classify_run(report: dict, kernel_status: str | None) -> str:
    """Reduce the combined report to one of COMPLETE / PARTIAL / TIMED_OUT / FAILED.

    `kernel_status` is the Kaggle-reported worker status, if known; a missing
    value falls back to inferring purely from the artifacts, which is the
    only signal available once a kernel's history has scrolled off.
    """
    if kernel_status in FAILED_KERNEL_STATUSES:
        return "FAILED"
    if report["problems"]:
        return "FAILED"

    n_expected = report.get("n_tasks_expected", 0)
    n_covered = report.get("n_tasks_with_candidates", 0)
    n_guard = report.get("n_hit_time_guard", 0)

    if n_expected and n_covered == 0:
        return "FAILED"
    if n_expected and n_covered < n_expected:
        return "TIMED_OUT" if n_guard else "PARTIAL"
    return "COMPLETE"


def validate(artifact_dir: Path, kernel_status: str | None = None) -> dict:
    report: dict[str, object] = {"artifact_dir": str(artifact_dir)}
    submission_path = artifact_dir / "submission.json"
    if not submission_path.exists():
        report.update(
            problems=["submission.json missing"],
            notes=[],
            ok=False,
            classification="FAILED" if kernel_status not in NONTERMINAL_KERNEL_STATUSES else "PARTIAL",
        )
        return report
    submission = json.loads(submission_path.read_text())

    runtime = artifact_dir / "runtime_summary.json"
    rerun = bool(json.loads(runtime.read_text()).get("rerun_mode")) if runtime.exists() else False
    split = "test" if rerun else "evaluation"
    challenges = json.loads((COMPETITION / f"arc-agi_{split}_challenges.json").read_text())
    report["split"] = split
    report["n_tasks_expected"] = len(challenges)

    candidates = read_gz_jsonl(artifact_dir / "candidates.jsonl.gz")
    ranking_records = read_gz_jsonl(artifact_dir / "candidates.ranking.jsonl.gz")
    report["n_selection_records"] = len(ranking_records)
    # Selection identity and structure checks need both record kinds together.
    all_records = candidates + ranking_records

    bookkeeping_stats, task_summary_rows, bookkeeping_problems = check_bookkeeping(artifact_dir)

    problems: list[str] = []
    notes: list[str] = []

    for severity, (stats, found) in (
        ("problem", check_submission_schema(submission, challenges)),
        ("problem", check_candidates_structure(all_records)),
        ("note", check_archive_vs_submission(candidates, submission)),
        ("problem", check_task_summary_reconciliation(candidates, task_summary_rows)),
        ("note", check_selected_matches_submission(all_records, submission)),
        ("problem", (bookkeeping_stats, bookkeeping_problems)),
        ("problem", check_no_leakage(all_records)),
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
    report["classification"] = classify_run(report, kernel_status)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", nargs="?", default=str(ROOT / "artifacts" / "run001"))
    parser.add_argument(
        "--kernel-status",
        default=None,
        help="Kaggle KernelWorkerStatus at download time, if known (e.g. COMPLETE, ERROR).",
    )
    args = parser.parse_args()
    report = validate(Path(args.artifact_dir), args.kernel_status)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
