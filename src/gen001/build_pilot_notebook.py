"""Build the GEN001-A 24-index pilot notebook from RUN-001's already-frozen,
already-validated instrumented notebook.

Generated, never hand-edited — the same discipline `src/run001/build_notebook.py`
already established. Every patch declares an anchor that must match exactly
once in its cell; a mismatch aborts the build, so a silent upstream drift in
`run001_instrumented.ipynb` cannot cause a patch to apply to the wrong place
or vanish.

Starting from RUN-001's notebook (not a fresh NVARC restoration) means this
pilot inherits an already-tested, behaviour-neutral candidate-archiving
instrumentation (`experiments/RUN001/INSTRUMENTATION_DIFF.md`) rather than
re-deriving it, per `NVARC_LINEAGE_AUDIT.md`'s "restores nothing new" scope.

Four patches beyond RUN-001's own two sanctioned changes:

1. Pilot budget and provenance (cell 0) — shorter global time cap, GEN001A
   identifiers.
2. Restrict the task queue to the 24 frozen pilot tasks, read from the
   ACQ-001 training-split corpus file instead of RUN-001's evaluation-split
   file, and skip already-completed tasks on resume (cell 6, `starter.py`).
3. Stamp every candidate record with `checkpoint_id`, `config_hash`,
   `contamination_status` (cell 5, `arc_solver.py`).
4. Replace the aggregation cell's data source with the training-split
   corpus and **remove the interactive self-scoring block entirely** — the
   reference notebook's non-rerun-mode path loads
   `arc-agi_evaluation_solutions.json` to print a "Reload score" (`docs/NVARC_2026_T4_BASELINE_AUDIT.md`
   §19); this pilot must never load any solutions file at any stage, so
   that code path is deleted rather than merely left unused (cell 8).

This build does not run the notebook and does not call `kaggle kernels
push` (`PILOT_PROTOCOL.md`'s launch gate) — it only assembles and locally
validates the artifact a future, separately-approved launch would submit.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.gen001.nvarc_adapter import FROZEN_PILOT_CONFIG, CONTAMINATION_STATUS

ROOT = Path(__file__).resolve().parents[2]
SOURCE_NOTEBOOK = ROOT / "kaggle" / "run001_nvarc_frozen" / "run001_instrumented.ipynb"
PILOT_MANIFEST = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"
OUTPUT_DIR = ROOT / "kaggle" / "gen001_nvarc_pilot"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "gen001a_pilot.ipynb"

GLOBAL_TIME_CAP_S = 18000  # 5h, per QUOTA_PROJECTION.md's ~4.5h pessimistic bound + margin
TRAINING_CHALLENGES_PATH = (
    "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json"
)


def _pilot_task_ids() -> list[str]:
    manifest = json.loads(PILOT_MANIFEST.read_text())
    return sorted({row["task_id"] for row in manifest["test_indices"]})


def _cell_0_patch(task_ids: list[str]) -> tuple[str, str, str]:
    anchor = (
        '# RUN-001 provenance\n'
        'RUN001_COMMIT = "131eba8144f99d561efe8624a5156d428935312e"\n'
        'RUN001_REFERENCE_SHA256 = "452dbb1fc050bad9cbba38a6802231bff91cc2970899eabb8c74e5f34f322a6c"\n'
        'import time\n'
        'global_end_time = time.time() + 12*3600 - 1200'
    )
    replacement = (
        "# GEN001-A pilot provenance — built from RUN-001's frozen instrumented notebook\n"
        'GEN001A_BASE_COMMIT = "131eba8144f99d561efe8624a5156d428935312e"\n'
        f'GEN001A_CHECKPOINT_ID = "{FROZEN_PILOT_CONFIG.checkpoint_id}"\n'
        f'GEN001A_CONFIG_HASH = "{FROZEN_PILOT_CONFIG.config_hash()}"\n'
        f'GEN001A_CONTAMINATION_STATUS = "{CONTAMINATION_STATUS}"\n'
        f"GEN001A_PILOT_TASK_IDS = {task_ids!r}\n"
        "import time\n"
        f"global_end_time = time.time() + {GLOBAL_TIME_CAP_S}"
    )
    return anchor, replacement, "pilot budget, provenance, and pinned identifiers"


def _cell_6_patch() -> tuple[str, str, str]:
    anchor = (
        "    rerun_mode = os.getenv(\"KAGGLE_IS_COMPETITION_RERUN\")\n"
        "\n"
        "    if rerun_mode:\n"
        '        test_path = "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json"\n'
        "    else:\n"
        '        test_path = "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json"\n'
        "\n"
        '    with open(test_path, "r") as f:\n'
        "        data = json.load(f)\n"
        "\n"
        "    queue = mp.Manager().Queue()\n"
        "\n"
        "    for key in sorted(data.keys()):\n"
        "        queue.put(key)\n"
        "    for _ in range(2):\n"
        "        queue.put(None)\n"
    )
    replacement = (
        "    # GEN001-A: fixed pilot corpus (ACQ-001 training-split tasks), never the\n"
        "    # evaluation or test split; never touches a solutions file.\n"
        f'    test_path = "{TRAINING_CHALLENGES_PATH}"\n'
        "\n"
        '    with open(test_path, "r") as f:\n'
        "        data = json.load(f)\n"
        "\n"
        "    checkpoint_path = \"/kaggle/working/run001/checkpoint_state.json\"\n"
        "    completed_ids = set()\n"
        "    if os.path.exists(checkpoint_path):\n"
        "        with open(checkpoint_path) as f:\n"
        "            completed_ids = set(json.load(f).get(\"completed_task_ids\", []))\n"
        "\n"
        "    queue = mp.Manager().Queue()\n"
        "\n"
        "    for key in GEN001A_PILOT_TASK_IDS:\n"
        "        if key in completed_ids:\n"
        "            continue\n"
        "        assert key in data, f\"pilot task {key} missing from training challenges file\"\n"
        "        queue.put(key)\n"
        "    for _ in range(2):\n"
        "        queue.put(None)\n"
    )
    return anchor, replacement, "restrict queue to the frozen 24-task pilot, training-split source, resume skip"


def _cell_5_data_source_patch() -> tuple[str, str, str]:
    anchor = (
        "    if rerun_mode:\n"
        '        test_path = "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json"\n'
        "    else:\n"
        '        test_path = "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json"\n'
        "\n"
        "    arc_test_set = ArcDataset.from_file(test_path)\n"
    )
    replacement = (
        "    # GEN001-A: the worker's own dataset load must match the training-split\n"
        "    # source the queue's task IDs were drawn from (patch: cell 6), never the\n"
        "    # evaluation or test split.\n"
        f'    test_path = "{TRAINING_CHALLENGES_PATH}"\n'
        "\n"
        "    arc_test_set = ArcDataset.from_file(test_path)\n"
    )
    return anchor, replacement, "worker's own dataset load must match the training-split source"


def _cell_5_patch() -> tuple[str, str, str]:
    anchor = (
        "                                beam_score=float(beam_score),\n"
        "                                score_aug=[float(s) for s in augmented_scores],"
    )
    replacement = (
        "                                beam_score=float(beam_score),\n"
        "                                score_aug=[float(s) for s in augmented_scores],\n"
        "                                checkpoint_id=GEN001A_CHECKPOINT_ID,\n"
        "                                config_hash=GEN001A_CONFIG_HASH,\n"
        "                                contamination_status=GEN001A_CONTAMINATION_STATUS,"
    )
    return anchor, replacement, "stamp checkpoint_id/config_hash/contamination_status on every candidate"


def _cell_8_patch() -> tuple[str, str, str]:
    anchor = (
        'rerun_mode = os.getenv("KAGGLE_IS_COMPETITION_RERUN")\n'
        "\n"
        "if rerun_mode:\n"
        '    data = ArcDataset.from_file("/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json")\n'
        "else:\n"
        '    data = ArcDataset.from_file("/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json")\n'
        '    data = data.load_replies("/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_solutions.json")\n'
    )
    replacement = (
        "# GEN001-A: fixed pilot corpus, never loads a solutions file at any stage.\n"
        "rerun_mode = os.getenv(\"KAGGLE_IS_COMPETITION_RERUN\")\n"
        f'data = ArcDataset.from_file("{TRAINING_CHALLENGES_PATH}")\n'
    )
    return anchor, replacement, "training-split source, remove solutions loading entirely"


def _cell_8_selfscore_patch() -> tuple[str, str, str]:
    anchor = (
        "if not rerun_mode:\n"
        "    decoder.benchmark_selection_algos()\n"
        '    with open("submission.json", "r") as f:\n'
        "        reload_submission = json.load(f)\n"
        '    print("*** Reload score:", data.validate_submission(reload_submission))'
    )
    replacement = (
        "# GEN001-A: no self-scoring against ground truth in any mode — the pilot\n"
        "# corpus's oracle status is computed later, offline, by\n"
        "# src/gen001/analyse_union.py, never inside this kernel.\n"
        'print("GEN001-A pilot run complete; no in-kernel scoring performed.")'
    )
    return anchor, replacement, "remove interactive self-scoring against ground truth"


def _cell_8_checkpoint_output_patch() -> tuple[str, str, str]:
    anchor = (
        '_summaries = sorted(_glob.glob(os.path.join(_run_dir, "task_summary.w*.csv")))\n'
        "if _summaries:\n"
        '    with open(os.path.join(_run_dir, "task_summary.csv"), "w", encoding="utf-8") as _out:\n'
        "        for _i, _p in enumerate(_summaries):\n"
        "            _lines = open(_p, encoding=\"utf-8\").read().splitlines(True)\n"
        "            _out.writelines(_lines if _i == 0 else _lines[1:])\n"
    )
    replacement = (
        anchor
        + "\n"
        + "# GEN001-A: required checkpoint/resume outputs, derived from the merged\n"
        + "# per-worker task summaries (whichever tasks actually flushed a record).\n"
        + "import csv as _csv\n"
        + "_completed_task_ids = []\n"
        + "_summary_csv = os.path.join(_run_dir, \"task_summary.csv\")\n"
        + "if os.path.exists(_summary_csv):\n"
        + "    with open(_summary_csv, newline=\"\", encoding=\"utf-8\") as _fh:\n"
        + "        _completed_task_ids = [_row[\"task_id\"] for _row in _csv.DictReader(_fh)]\n"
        + "json.dump(\n"
        + "    {\"completed_task_ids\": sorted(set(_completed_task_ids))},\n"
        + "    open(os.path.join(_run_dir, \"checkpoint_state.json\"), \"w\"), indent=2, sort_keys=True)\n"
        + "json.dump(\n"
        + "    sorted(set(_completed_task_ids)),\n"
        + "    open(os.path.join(_run_dir, \"completed_indices.json\"), \"w\"))\n"
    )
    return anchor, replacement, "write checkpoint_state.json and completed_indices.json for resume"


def _cell_8_selection_record_patch() -> tuple[str, str, str]:
    anchor = (
        '                "rank_after_aggregation": _rank,\n'
        '                "selected": _rank <= 2,\n'
        '                "selection_algorithm": "score_kgmon",\n'
        "            }\n"
    )
    replacement = (
        '                "rank_after_aggregation": _rank,\n'
        '                "selected": _rank <= 2,\n'
        '                "selection_algorithm": "score_kgmon",\n'
        '                "checkpoint_id": GEN001A_CHECKPOINT_ID,\n'
        '                "config_hash": GEN001A_CONFIG_HASH,\n'
        '                "contamination_status": GEN001A_CONTAMINATION_STATUS,\n'
        "            }\n"
    )
    return anchor, replacement, "stamp selection records with the same provenance fields"


PATCHES = [
    (0, *_cell_0_patch(_pilot_task_ids())),
    (5, *_cell_5_data_source_patch()),
    (5, *_cell_5_patch()),
    (6, *_cell_6_patch()),
    (8, *_cell_8_patch()),
    (8, *_cell_8_selfscore_patch()),
    (8, *_cell_8_checkpoint_output_patch()),
    (8, *_cell_8_selection_record_patch()),
]


def build() -> dict:
    notebook = json.loads(SOURCE_NOTEBOOK.read_text())
    applied = []
    for index, anchor, replacement, reason in PATCHES:
        source = "".join(notebook["cells"][index]["source"])
        count = source.count(anchor)
        if count != 1:
            raise AssertionError(f"cell {index}: anchor for {reason!r} matched {count} times, expected 1")
        source = source.replace(anchor, replacement)
        notebook["cells"][index]["source"] = source.splitlines(keepends=True)
        applied.append((index, reason))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_NOTEBOOK.write_text(json.dumps(notebook, indent=1))
    return {"output": str(OUTPUT_NOTEBOOK), "patches": applied}


def main() -> None:
    result = build()
    print(f"Wrote {result['output']}")
    for index, reason in result["patches"]:
        print(f"  cell {index}: {reason}")


if __name__ == "__main__":
    main()
