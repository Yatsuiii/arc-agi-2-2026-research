"""Build the RUN-001 instrumented notebook from the frozen reference.

The instrumented notebook is generated, never hand-edited, so that every
difference from the reference is one declared patch with a stated reason. Run
`python -m src.run001.build_notebook` to regenerate; run
`python -m src.run001.validate_notebook` to check the result.

Each patch is (anchor, replacement, reason). Anchors must match exactly once in
their cell, which is asserted, so a silent upstream change cannot let a patch
apply to the wrong place or vanish.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "kaggle" / "run001_nvarc_frozen" / "reference_source.ipynb"
ARCHIVE_MODULE = ROOT / "src" / "run001" / "archive.py"
OUTPUT_DIR = ROOT / "kaggle" / "run001_nvarc_frozen"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "run001_instrumented.ipynb"

RUN_DIR = "/kaggle/working/run001"

# ---------------------------------------------------------------------------
# Patch 0: the model mount path.
#
# NOT one of the two sanctioned changes. It is required because Kaggle's model
# mount path has drifted since the reference notebook was written: the notebook
# hardcodes /kaggle/input/<slug>/... and the checkpoint now mounts at
# /kaggle/input/models/<owner>/<slug>/... Verified by probe kernel
# run001-asset-probe v3. Without it the notebook cannot load the checkpoint at
# all and there is no run.
#
# It is written to prefer the original path whenever that path exists, so if
# Kaggle ever restores the old layout the behaviour is byte-identical to the
# reference. It selects the same checkpoint either way; no solver property
# changes.
# ---------------------------------------------------------------------------

MODEL_RESOLVER = '''

RUN001_MODEL_CANDIDATES = [
    "/kaggle/input/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
    "/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
]


def run001_resolve_model_dir():
    """First existing mount, preferring the reference notebook's original path."""
    for path in RUN001_MODEL_CANDIDATES:
        if os.path.isdir(path):
            return path
    raise FileNotFoundError(f"checkpoint not found in {RUN001_MODEL_CANDIDATES}")


RUN001_MODEL_DIR = run001_resolve_model_dir()
'''

ARCHIVE_SETUP = f'''
    archive = CandidateArchive({RUN_DIR!r}, shard=f"w{{rank}}")
    run001_task_holder = ["<none>"]
    run001_prev_hook = sys.excepthook

    def run001_excepthook(exc_type, exc_value, exc_tb):
        # Records and then re-raises through the original hook, so control flow
        # is unchanged and a crash that would have killed the worker still does.
        try:
            archive.record_error(
                run001_task_holder[0], "worker", exc_value, gpu_index=rank
            )
        except Exception:
            pass
        run001_prev_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = run001_excepthook
'''

RECORD_CANDIDATE = '''
                        try:
                            archive.record_candidate(
                                task_id=bk.split("_")[0],
                                test_index=int(bk.split("_")[1]),
                                base_key=bk,
                                augmentation_key=subkey,
                                inverse_augmentation=subkey.split(".", 1)[-1],
                                candidate_index=len(decoded_result),
                                generation_order=run001_generation_order[0],
                                grid=to_grid(solution),
                                grid_sha1=grid_digest(to_grid(solution)),
                                n_rows=len(solution),
                                n_cols=len(solution[0]) if len(solution) else 0,
                                beam_score=float(beam_score),
                                score_aug=[float(s) for s in augmented_scores],
                                score_aug_mean=float(np.mean(augmented_scores)),
                                model_id="sorokin/qwen3_4b_grids15_sft139",
                                solver_branch="nvarc_architects_qwen3_4b",
                                decoding="turbo_dfs",
                                dfs_max_score=float(max_score),
                                max_new_tokens=int(max_new_tokens),
                                ttt_seed=1,
                                eval_seed=2,
                                global_seed=42,
                                ttt_augmentations=16,
                                gpu_index=rank,
                                candidate_latency_s=time.time() - run001_cand_clock[0],
                                cumulative_task_s=time.time() - start_time,
                            )
                        except Exception:
                            pass
                        run001_generation_order[0] += 1
                        run001_cand_clock[0] = time.time()
'''

FLUSH_TASK = '''
        try:
            archive.flush_task(
                key,
                n_test_inputs=len(puzzle_ds_multi.keys),
                n_candidates=run001_generation_order[0],
                solve_seconds=spend_time,
                hit_time_guard=bool(spend_time > 1200),
                gpu_index=rank,
                peak_mem_infer_mib=memory_allocated,
            )
        except Exception:
            pass
'''

DECODER_TAIL = f'''

# --- RUN-001 instrumentation: ranking/selection records and artifact collection.
import glob as _glob
import gzip as _gzip
import shutil as _shutil

_run_dir = {RUN_DIR!r}
os.makedirs(_run_dir, exist_ok=True)

_selected = decoder.run_selection_algo()
_ranking_path = os.path.join(_run_dir, "candidates.ranking.jsonl.gz")
with _gzip.open(_ranking_path, "wt", encoding="utf-8") as _fh:
    for _bk, _ordered in _selected.items():
        for _rank, _grid in enumerate(_ordered, start=1):
            _g = _grid.tolist() if hasattr(_grid, "tolist") else _grid
            _rec = {{
                "kind": "selection",
                "task_id": _bk.split("_")[0],
                "test_index": int(_bk.split("_")[1]),
                "base_key": _bk,
                "grid_sha1": grid_digest(_g),
                "rank_after_aggregation": _rank,
                "selected": _rank <= 2,
                "selection_algorithm": "score_kgmon",
            }}
            _fh.write(json.dumps(_rec, sort_keys=True, separators=(",", ":")) + "\\n")

for _pattern, _target in [("candidates.w*.jsonl.gz", "candidates.jsonl.gz"),
                          ("errors.w*.jsonl", "errors.jsonl")]:
    _parts = sorted(_glob.glob(os.path.join(_run_dir, _pattern)))
    if _parts:
        with open(os.path.join(_run_dir, _target), "wb") as _out:
            for _p in _parts:
                with open(_p, "rb") as _in:
                    _shutil.copyfileobj(_in, _out)

_summaries = sorted(_glob.glob(os.path.join(_run_dir, "task_summary.w*.csv")))
if _summaries:
    with open(os.path.join(_run_dir, "task_summary.csv"), "w", encoding="utf-8") as _out:
        for _i, _p in enumerate(_summaries):
            _lines = open(_p, encoding="utf-8").read().splitlines(True)
            _out.writelines(_lines if _i == 0 else _lines[1:])

_shutil.copyfile("submission.json", os.path.join(_run_dir, "submission.json"))

_runtimes = sorted(_glob.glob(os.path.join(_run_dir, "runtime_summary.w*.json")))
json.dump(
    {{"shards": [json.load(open(_p)) for _p in _runtimes],
      "n_tasks_in_submission": len(submission),
      "rerun_mode": bool(rerun_mode)}},
    open(os.path.join(_run_dir, "runtime_summary.json"), "w"), indent=2, sort_keys=True)

print("RUN-001 artifacts:", sorted(os.listdir(_run_dir)))
'''

PATCHES: list[tuple[int, str, str, str]] = [
    (
        4,
        "logging.disable(logging.WARNING)\n",
        "logging.disable(logging.WARNING)\n"
        "\nimport sys\nfrom arc_archive import CandidateArchive, grid_digest, to_grid\n"
        + MODEL_RESOLVER,
        "P0/P2 model-path resolver and archive import",
    ),
    (
        4,
        '        model_name="/kaggle/input/qwen3_4b_grids15_sft139/transformers/bfloat16/1",\n',
        "        model_name=RUN001_MODEL_DIR,\n",
        "P0 use the resolved checkpoint path",
    ),
    (
        4,
        '    dir_outputs = "/kaggle/inference_outputs"\n    os.makedirs(dir_outputs, exist_ok=True)\n',
        '    dir_outputs = "/kaggle/inference_outputs"\n    os.makedirs(dir_outputs, exist_ok=True)\n'
        + ARCHIVE_SETUP,
        "P2 create the per-worker archive and exception hook",
    ),
    (
        4,
        "        key = queue.get()\n        if key is None:\n            break\n",
        "        key = queue.get()\n        if key is None:\n            break\n"
        "        run001_task_holder[0] = key\n"
        "        run001_generation_order = [0]\n"
        "        run001_cand_clock = [time.time()]\n",
        "P2 per-task archive counters",
    ),
    (
        4,
        '                        decoded_result.append({\n'
        '                            "beam_score": beam_score,\n'
        '                            "score_aug": augmented_scores,\n'
        '                            "solution": solution,\n'
        "                        })\n",
        '                        decoded_result.append({\n'
        '                            "beam_score": beam_score,\n'
        '                            "score_aug": augmented_scores,\n'
        '                            "solution": solution,\n'
        "                        })\n" + RECORD_CANDIDATE,
        "P2 record each candidate (append-only, after the solver's own append)",
    ),
    (
        4,
        '        print(f"[Rank {rank}] finished {key} in {spend_time:.1f}s")',
        '        print(f"[Rank {rank}] finished {key} in {spend_time:.1f}s")\n' + FLUSH_TASK,
        "P2 flush the archive once per completed task",
    ),
    (
        5,
        '        if not rerun_mode:\n'
        '            if key not in ["0934a4d8", "36a08778", "981571dc", "aa4ec2a5"]:\n'
        "                continue\n",
        "",
        "P1 remove the hardcoded four-task debug filter",
    ),
    (
        7,
        'with open("submission.json", "w") as f:\n    json.dump(submission, f)\n',
        'with open("submission.json", "w") as f:\n    json.dump(submission, f)\n'
        "\nfrom arc_archive import grid_digest\n" + DECODER_TAIL,
        "P2 selection records and artifact collection",
    ),
]


def _source(cell) -> str:
    return cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])


def build() -> dict:
    notebook = json.loads(REFERENCE.read_text())
    cells = notebook["cells"]

    applied = []
    for index, anchor, replacement, reason in PATCHES:
        text = _source(cells[index])
        count = text.count(anchor)
        if count != 1:
            raise AssertionError(
                f"cell {index}: anchor for {reason!r} matched {count} times, expected 1"
            )
        cells[index]["source"] = text.replace(anchor, replacement)
        applied.append((index, reason))

    archive_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": "%%writefile arc_archive.py\n" + ARCHIVE_MODULE.read_text(),
    }
    cells.insert(2, archive_cell)

    OUTPUT_NOTEBOOK.write_text(json.dumps(notebook, indent=1) + "\n")
    return {"patches": applied, "cells": len(cells)}


if __name__ == "__main__":
    result = build()
    for index, reason in result["patches"]:
        print(f"  cell {index}: {reason}")
    print(f"wrote {OUTPUT_NOTEBOOK} ({result['cells']} cells)")
