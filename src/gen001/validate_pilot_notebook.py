"""Static checks on the built GEN001-A pilot notebook. No GPU, no execution.

Mirrors `src/run001/validate_notebook.py`'s discipline: every check reads
the notebook JSON as text and asserts a property that would be dangerous or
wrong to get silently wrong (ground-truth access, wrong data split, missing
provenance stamping).
"""

from __future__ import annotations

import json

from src.gen001.build_pilot_notebook import OUTPUT_NOTEBOOK


def _full_source() -> str:
    notebook = json.loads(OUTPUT_NOTEBOOK.read_text())
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


def check_no_evaluation_split_loaded() -> list[str]:
    src = _full_source()
    errors = []
    if "arc-agi_evaluation_challenges" in src:
        errors.append("evaluation-split challenges file still referenced")
    if "arc-agi_evaluation_solutions" in src:
        errors.append("evaluation-split solutions file still referenced")
    return errors


def check_no_solutions_file_loaded() -> list[str]:
    src = _full_source()
    errors = []
    if ".load_replies(" in src:
        errors.append("load_replies (ground-truth loader) still called")
    if "data.validate_submission" in src:
        errors.append("in-kernel self-scoring against ground truth still present")
    return errors


def check_training_split_used() -> list[str]:
    src = _full_source()
    if src.count("arc-agi_training_challenges.json") < 2:
        return ["expected training-split challenges path in both worker and aggregation cells"]
    return []


def check_provenance_fields_stamped() -> list[str]:
    src = _full_source()
    errors = []
    for field in ("checkpoint_id", "config_hash", "contamination_status"):
        if src.count(field) < 2:  # candidate record + selection record
            errors.append(f"{field!r} not stamped on both candidate and selection records")
    return errors


def check_parses() -> list[str]:
    try:
        json.loads(OUTPUT_NOTEBOOK.read_text())
    except json.JSONDecodeError as exc:
        return [f"notebook is not valid JSON: {exc}"]
    return []


CHECKS = [
    check_parses,
    check_no_evaluation_split_loaded,
    check_no_solutions_file_loaded,
    check_training_split_used,
    check_provenance_fields_stamped,
]


def main() -> None:
    all_errors = []
    for check in CHECKS:
        errors = check()
        status = "PASS" if not errors else "FAIL"
        print(f"[{status}] {check.__name__}")
        for error in errors:
            print(f"    {error}")
        all_errors.extend(errors)
    if all_errors:
        raise SystemExit(f"{len(all_errors)} validation error(s)")
    print("All checks passed.")


if __name__ == "__main__":
    main()
