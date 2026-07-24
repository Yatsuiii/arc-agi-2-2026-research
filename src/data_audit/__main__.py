"""Regenerate every artifact under artifacts/data_audit/.

Deterministic, CPU only, no network. Run from the repository root:

    python -m src.data_audit
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from . import duplicates, schema, statistics
from .corpus import load_github, load_kaggle

WORKSPACE = Path(__file__).resolve().parents[3]
KAGGLE = WORKSPACE / "competition_2026" / "extracted"
BENCHMARK = WORKSPACE / "benchmark" / "ARC-AGI-2" / "data"
OUTPUT = Path(__file__).resolve().parents[2] / "artifacts" / "data_audit"


def _load_all():
    return {
        "kaggle_training": load_kaggle(
            KAGGLE / "arc-agi_training_challenges.json",
            KAGGLE / "arc-agi_training_solutions.json",
            "kaggle_training",
        ),
        "kaggle_evaluation": load_kaggle(
            KAGGLE / "arc-agi_evaluation_challenges.json",
            KAGGLE / "arc-agi_evaluation_solutions.json",
            "kaggle_evaluation",
        ),
        "kaggle_test": load_kaggle(
            KAGGLE / "arc-agi_test_challenges.json", None, "kaggle_test"
        ),
        "github_training": load_github(BENCHMARK / "training", "github_training"),
        "github_evaluation": load_github(BENCHMARK / "evaluation", "github_evaluation"),
    }


def _write_json(name: str, payload) -> None:
    (OUTPUT / name).write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    print(f"wrote {OUTPUT / name}")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    corpora = _load_all()

    rows = [
        dict(statistics.describe(task), split=name)
        for name, corpus in corpora.items()
        for task in corpus
    ]
    _write_json(
        "task_statistics.json",
        {name: statistics.summarise(corpus) for name, corpus in corpora.items()},
    )
    with (OUTPUT / "task_statistics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT / 'task_statistics.csv'} ({len(rows)} rows)")

    _write_json(
        "duplicate_report.json",
        duplicates.report(
            [
                corpora["kaggle_training"],
                corpora["kaggle_evaluation"],
                corpora["kaggle_test"],
            ]
        ),
    )

    _write_json(
        "schema_report.json",
        {
            "validation": [schema.validate(c) for c in corpora.values()],
            "kaggle_vs_github_training": schema.compare(
                corpora["kaggle_training"], corpora["github_training"]
            ),
            "kaggle_vs_github_evaluation": schema.compare(
                corpora["kaggle_evaluation"], corpora["github_evaluation"]
            ),
            "submission_contract": schema.submission_contract(
                KAGGLE / "sample_submission.json", corpora["kaggle_test"]
            ),
        },
    )


if __name__ == "__main__":
    main()
