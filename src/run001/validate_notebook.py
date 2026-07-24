"""Static gate for the RUN-001 instrumented notebook.

Everything here must pass before the notebook is pushed to Kaggle. The checks
are the static half of the behaviour-neutrality gate; the dynamic half is
`tests/test_run001_archive.py::test_logging_is_behaviour_neutral`.

Run: `python -m src.run001.validate_notebook`
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "kaggle" / "run001_nvarc_frozen" / "reference_source.ipynb"
INSTRUMENTED = ROOT / "kaggle" / "run001_nvarc_frozen" / "run001_instrumented.ipynb"
METADATA = ROOT / "kaggle" / "run001_nvarc_frozen" / "kernel-metadata.json"
ARCHIVE_MODULE = ROOT / "src" / "run001" / "archive.py"

# Solver knobs that must be byte-identical to the reference. If any of these
# strings changes, the run is no longer a faithful baseline.
FROZEN_SOLVER_STRINGS = [
    "r=256,",
    "lora_alpha=32,",
    "use_rslora=True,",
    'lr_scheduler_type="cosine",',
    "learning_rate=5e-5,",
    'optim="adamw_8bit",',
    "num_train_epochs=1,",
    "max_seq_length = 8192",
    "max_score = -np.log(0.2)",
    "augment(n=16, shfl_keys=True, seed=1)",
    "augment(n=2, seed=2)",
    "seed=42,",
    "load_in_4bit=True,",
    'attn_implementation="eager",',
    "mp.spawn(local_worker, args=(queue, args.end_time), nprocs=2)",
    "global_end_time = time.time() + 12*3600 - 1200",
    "if spend_time > 1200 or time.time() > end_time:",
    "while time.time() - start_time < 540 and time.time() < end_time:",
    "score_kgmon",
    "n_guesses=2",
]

BANNED_IN_ARCHIVE = ["solutions.json", "arc-agi_evaluation_solutions", "replies["]


def _source(cell) -> str:
    return cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])


def _cells(path: Path) -> list[str]:
    return [_source(c) for c in json.loads(path.read_text())["cells"]]


def check_parses() -> list[str]:
    problems = []
    try:
        import nbformat

        nbformat.validate(nbformat.read(str(INSTRUMENTED), as_version=4))
    except ImportError:
        problems.append("NOTE: nbformat unavailable; fell back to json + ast only")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"nbformat validation failed: {exc}")

    for index, source in enumerate(_cells(INSTRUMENTED)):
        body = source
        if body.startswith("%%writefile"):
            body = body.split("\n", 1)[1]
        if any(line.startswith("!") or line.startswith("%") for line in body.splitlines()):
            continue  # shell/magic cell, not plain Python
        try:
            ast.parse(body)
        except SyntaxError as exc:
            problems.append(f"cell {index} does not parse: {exc}")
    return problems


def check_frozen_solver() -> list[str]:
    """Every reference line carrying a solver setting must survive verbatim.

    Comparing occurrence counts would be wrong in both directions: instrumentation
    legitimately adds lines that happen to contain a needle as a substring (a
    recorded `global_seed=42` label, the string "score_kgmon" written as
    provenance), while a genuinely altered setting shows up as its original line
    disappearing. Line-presence is the property we actually care about.
    """
    reference_lines = {line.strip() for cell in _cells(REFERENCE) for line in cell.splitlines()}
    instrumented_lines = {
        line.strip() for cell in _cells(INSTRUMENTED) for line in cell.splitlines()
    }
    problems = []
    for needle in FROZEN_SOLVER_STRINGS:
        carrying = {line for line in reference_lines if needle in line}
        if not carrying:
            problems.append(f"needle {needle!r} not found in reference; check is stale")
            continue
        for line in sorted(carrying - instrumented_lines):
            problems.append(f"solver line lost or altered: {line!r}")
    return problems


def check_debug_filter_removed() -> list[str]:
    instrumented = "\n".join(_cells(INSTRUMENTED))
    ids = ["0934a4d8", "36a08778", "981571dc", "aa4ec2a5"]
    return [f"debug filter task id {i} still present" for i in ids if i in instrumented]


def check_archive_module_matches() -> list[str]:
    for source in _cells(INSTRUMENTED):
        if source.startswith("%%writefile arc_archive.py"):
            embedded = source.split("\n", 1)[1]
            if embedded == ARCHIVE_MODULE.read_text():
                return []
            return ["embedded arc_archive.py differs from src/run001/archive.py"]
    return ["no arc_archive.py cell found"]


def check_no_ground_truth_archived() -> list[str]:
    """The archive must never persist hidden answers."""
    problems = []
    for index, source in enumerate(_cells(INSTRUMENTED)):
        for line in source.splitlines():
            if "archive.record_" in line or "_fh.write" in line:
                for banned in BANNED_IN_ARCHIVE:
                    if banned in line:
                        problems.append(f"cell {index}: archive line references {banned!r}")
    return problems


def check_no_rng_in_archive() -> list[str]:
    """Instrumentation must not consume randomness."""
    tree = ast.parse(ARCHIVE_MODULE.read_text())
    banned = {"random", "numpy.random", "np.random", "secrets"}
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in banned:
                    problems.append(f"archive.py imports {alias.name}")
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in banned:
            problems.append(f"archive.py imports from {node.module}")
    return problems


def check_metadata() -> list[str]:
    if not METADATA.exists():
        return ["kernel-metadata.json missing"]
    meta = json.loads(METADATA.read_text())
    problems = []
    expected = {
        "enable_internet": False,
        "enable_gpu": True,
        "is_private": True,
        "machine_shape": "NvidiaTeslaT4",
    }
    for key, value in expected.items():
        if meta.get(key) != value:
            problems.append(f"metadata {key}={meta.get(key)!r}, expected {value!r}")
    if meta.get("competition_sources") != ["arc-prize-2026-arc-agi-2"]:
        problems.append(f"competition_sources={meta.get('competition_sources')}")
    if meta.get("model_sources") != [
        "sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1"
    ]:
        problems.append(f"model_sources={meta.get('model_sources')}")
    if meta.get("kernel_sources") != ["sorokin/pip-install-unsloth-flash-patch"]:
        problems.append(f"kernel_sources={meta.get('kernel_sources')}")
    if not re.match(r"^gcr\.io/kaggle-private-byod/python@sha256:[0-9a-f]{64}$",
                    meta.get("docker_image", "")):
        problems.append(f"docker_image not pinned: {meta.get('docker_image')!r}")
    if meta.get("code_file") != INSTRUMENTED.name:
        problems.append(f"code_file={meta.get('code_file')!r}")
    return problems


def check_kaggle_paths() -> list[str]:
    instrumented = "\n".join(_cells(INSTRUMENTED))
    problems = []
    required = [
        "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json",
        "/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
        "/kaggle/working/run001",
    ]
    for path in required:
        if path not in instrumented:
            problems.append(f"expected path absent: {path}")
    return problems


CHECKS = [
    ("notebook parses", check_parses),
    ("solver settings frozen", check_frozen_solver),
    ("debug filter removed", check_debug_filter_removed),
    ("embedded archive matches source", check_archive_module_matches),
    ("no ground truth archived", check_no_ground_truth_archived),
    ("no RNG use in archive", check_no_rng_in_archive),
    ("kernel metadata correct", check_metadata),
    ("kaggle paths present", check_kaggle_paths),
]


def main() -> int:
    print(f"reference    sha256 {hashlib.sha256(REFERENCE.read_bytes()).hexdigest()}")
    print(f"instrumented sha256 {hashlib.sha256(INSTRUMENTED.read_bytes()).hexdigest()}")
    print()
    failures = 0
    for name, check in CHECKS:
        problems = check()
        hard = [p for p in problems if not p.startswith("NOTE:")]
        status = "FAIL" if hard else "pass"
        failures += bool(hard)
        print(f"[{status}] {name}")
        for problem in problems:
            print(f"        {problem}")
    print()
    print("GATE FAILED" if failures else "GATE PASSED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
