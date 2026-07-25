"""EXP002 support: per-task-index candidate/selection headroom on a RUN-001 archive.

Reads the archived NVARC candidate records (`candidates.jsonl.gz`) and
selection records (`candidates.ranking.jsonl.gz`), joins them, and, where
ground truth is available, measures generation vs. selection failure exactly
as `src.analysis.headroom` did for EXP001-A — but from real per-candidate
grids instead of hashed traces, which is what `src/run001/archive.py`'s
schema adds over CompressARC's logs.

Ground truth is optional per call. The ARC-AGI-2 `test` split ships no
solutions file (its tasks are training-split copies used only as a pipeline
smoke test, `README.md` "Data policy"), and a solver crash could in
principle stop before `evaluation` solutions are needed either. Neither case
is an error here: the ground-truth-dependent fields are simply omitted.

The selector's own numeric score is not archived (`candidates.ranking.jsonl.gz`
records a rank and a `selected` flag only, not the value that produced them,
`experiments/RUN001/INSTRUMENTATION_DIFF.md` cell 8). Where a score is needed
(the correct-vs-selected margin) it is reconstructed from what candidate
records do carry — generation vote count and the memoised augmentation-mean
score — following `score_kgmon = len(guesses) - mean(mean(score_aug))`
(`experiments/RUN001/BASELINE_SPEC.md` "Candidate scoring and ranking"). This
is an approximation of NVARC's selector score, not the literal value it used.
"""

from __future__ import annotations

import csv
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path

from src.run001.archive import grid_digest

ROOT = Path(__file__).resolve().parents[2]
COMPETITION = ROOT.parent / "competition_2026" / "extracted"


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
    except OSError:
        pass
    return records


def load_solutions(split: str) -> dict[str, list] | None:
    """Ground-truth grids per task, or None if this split has no solutions file.

    Never raises: an absent file is a legitimate case (the `test` split), not
    an error to surface to callers who just want whatever metrics are
    computable.
    """
    path = COMPETITION / f"arc-agi_{split}_solutions.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _num(value):
    if value in (None, ""):
        return None
    return float(value)


def load_task_summary(artifact_dir: Path) -> dict[str, dict]:
    path = artifact_dir / "task_summary.csv"
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    for row in csv.DictReader(path.open()):
        rows[row["task_id"]] = {
            "n_candidates": int(row["n_candidates"]) if row.get("n_candidates") else None,
            "ttt_seconds": _num(row.get("ttt_seconds")),
            "solve_seconds": _num(row.get("solve_seconds")),
            "hit_time_guard": row.get("hit_time_guard") == "1",
        }
    return rows


def _truth_digests(solutions: dict, task_id: str) -> list[str]:
    return [grid_digest(grid) for grid in solutions.get(task_id, [])]


def join_candidates_and_selection(candidates: list[dict], selection: list[dict]) -> dict:
    """Group both record kinds by (task_id, test_index)."""
    by_task_test: dict[tuple, dict] = defaultdict(lambda: {"candidates": [], "selection": {}})
    for record in candidates:
        if record.get("kind") != "candidate":
            continue
        key = (record.get("task_id"), record.get("test_index"))
        by_task_test[key]["candidates"].append(record)
    for record in selection:
        if record.get("kind") != "selection":
            continue
        key = (record.get("task_id"), record.get("test_index"))
        by_task_test[key]["selection"][record.get("grid_sha1")] = record
    return by_task_test


def augmentation_agreement(record: dict) -> float | None:
    """Proxy for cross-augmentation consistency on one candidate.

    1 minus the normalised spread of its 8 rescoring scores (`score_aug`).
    Higher means the augmented views agree more about this candidate; it is a
    relative consistency measure, not a probability.
    """
    scores = record.get("score_aug")
    if not scores or len(scores) < 2:
        return None
    mean = statistics.fmean(scores)
    spread = statistics.pstdev(scores)
    return max(0.0, 1.0 - spread / (abs(mean) + 1e-9))


def reconstruct_score_kgmon(candidates_for_grid: list[dict]) -> float | None:
    """Approximate `score_kgmon` for one unique grid: votes - mean(score_aug_mean)."""
    means = [c["score_aug_mean"] for c in candidates_for_grid if c.get("score_aug_mean") is not None]
    if not means:
        return None
    return len(candidates_for_grid) - statistics.fmean(means)


def analyse_test_index(entry: dict, truth_digests: list[str] | None) -> dict:
    candidates = entry["candidates"]
    selection = entry["selection"]

    digests = [c.get("grid_sha1") or grid_digest(c.get("grid")) for c in candidates]
    n_candidates = len(candidates)
    n_unique = len(set(digests))

    by_grid: dict[str, list[dict]] = defaultdict(list)
    for candidate, sha1 in zip(candidates, digests):
        by_grid[sha1].append(candidate)
    reconstructed_scores = {sha1: reconstruct_score_kgmon(group) for sha1, group in by_grid.items()}

    selected = sorted(
        (r for r in selection.values() if r.get("selected")),
        key=lambda r: r.get("rank_after_aggregation", 1 << 30),
    )
    selected_digests = [r["grid_sha1"] for r in selected[:2]]

    agreements = [a for a in (augmentation_agreement(c) for c in candidates) if a is not None]

    result: dict = {
        "n_candidates": n_candidates,
        "n_unique_grids": n_unique,
        "duplicate_candidate_frequency": (1 - n_unique / n_candidates) if n_candidates else None,
        "n_selected": len(selected_digests),
        "augmentation_agreement_mean": statistics.fmean(agreements) if agreements else None,
    }

    if truth_digests is None:
        return result

    truth_set = set(truth_digests)
    generated = truth_set & set(digests)
    result["correct_candidate_generated"] = bool(generated)
    result["correct_candidate_selected"] = any(d in truth_set for d in selected_digests)

    truth_rank = None
    for sha1, record in selection.items():
        if sha1 in truth_set:
            rank = record.get("rank_after_aggregation")
            if rank is not None and (truth_rank is None or rank < truth_rank):
                truth_rank = rank
    result["rank_of_correct_candidate"] = truth_rank

    correct_scores = [reconstructed_scores[d] for d in generated if reconstructed_scores.get(d) is not None]
    selected_scores = [
        reconstructed_scores[d] for d in selected_digests if reconstructed_scores.get(d) is not None
    ]
    result["score_margin_correct_vs_selected"] = (
        max(selected_scores) - max(correct_scores)
        if correct_scores and selected_scores
        else None
    )

    return result


def analyse_run(artifact_dir: Path, split: str) -> dict:
    candidates = read_gz_jsonl(artifact_dir / "candidates.jsonl.gz")
    selection = read_gz_jsonl(artifact_dir / "candidates.ranking.jsonl.gz")
    summary = load_task_summary(artifact_dir)
    solutions = load_solutions(split)
    has_truth = solutions is not None

    joined = join_candidates_and_selection(candidates, selection)
    per_test_index: dict[str, dict] = {}
    for (task_id, test_index), entry in joined.items():
        truth_digests = _truth_digests(solutions, task_id) if has_truth else None
        per_test_index[f"{task_id}:{test_index}"] = analyse_test_index(entry, truth_digests)

    n = len(per_test_index)
    report: dict = {
        "split": split,
        "ground_truth_available": has_truth,
        "n_test_indices": n,
        "per_task_runtime": summary,
        "per_test_index": per_test_index,
    }
    if has_truth and n:
        oracle_hits = sum(1 for r in per_test_index.values() if r["correct_candidate_generated"])
        selected_hits = sum(1 for r in per_test_index.values() if r["correct_candidate_selected"])
        report["oracle_candidate_accuracy"] = oracle_hits / n
        report["selected_accuracy"] = selected_hits / n
        report["selection_headroom"] = (oracle_hits - selected_hits) / n
        report["n_oracle_hits"] = oracle_hits
        report["n_selected_hits"] = selected_hits
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--split", default="evaluation", choices=["training", "evaluation", "test"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = analyse_run(args.artifact_dir, args.split)
    out = args.out or (ROOT / "artifacts" / "exp002" / "candidate_headroom.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"ground_truth_available     = {report['ground_truth_available']}")
    print(f"n_test_indices             = {report['n_test_indices']}")
    if report["ground_truth_available"]:
        print(f"oracle_candidate_accuracy  = {report.get('oracle_candidate_accuracy')}")
        print(f"selected_accuracy          = {report.get('selected_accuracy')}")
        print(f"selection_headroom         = {report.get('selection_headroom')}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
