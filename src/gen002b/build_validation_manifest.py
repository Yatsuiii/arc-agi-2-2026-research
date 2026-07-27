"""Freeze GEN002-B's fresh 24-index validation manifest.

Deterministic, CPU-only, and based only on already-frozen ACQ-001 /
EXP002-D metadata plus visible ARC training-task structure. The original
24-task GEN001-A / GEN002-A pilot is excluded at the task level.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OLD_PILOT = ROOT / "artifacts" / "GEN001A" / "pilot_manifest.json"
ERROR_TAXONOMY = ROOT / "artifacts" / "EXP002D" / "error_taxonomy.csv"
TASK_STATS = ROOT / "artifacts" / "data_audit" / "task_statistics.csv"
TEST_INDEX_SUMMARY = ROOT / "artifacts" / "EXP002D" / "test_index_summary.parquet"
TRAIN_CHALLENGES = Path(
    "/home/Yatsuiii/arc-agi-2-2026/competition_2026/extracted/arc-agi_training_challenges.json"
)
OUT_MANIFEST = ROOT / "artifacts" / "GEN002B" / "validation_manifest.json"

N_GROUP_A2 = 12
N_GROUP_B2 = 6
N_GROUP_C2 = 6


def _load_old_pilot() -> tuple[set[str], set[tuple[str, int]]]:
    data = json.loads(OLD_PILOT.read_text())
    rows = data["test_indices"]
    return {row["task_id"] for row in rows}, {(row["task_id"], int(row["test_index"])) for row in rows}


def _component_bucket(objects_input_mean: float) -> str:
    if objects_input_mean <= 2.0:
        return "single_or_pair"
    if objects_input_mean <= 6.0:
        return "few_components"
    if objects_input_mean <= 15.0:
        return "moderate_components"
    return "many_components"


def _object_structure(objects_input_mean: float, large_grid: bool) -> str:
    if objects_input_mean <= 2.0:
        return "dominant_object"
    if large_grid and objects_input_mean >= 15.0:
        return "dense_large_scene"
    if objects_input_mean >= 8.0:
        return "multi_object_scene"
    return "sparse_scene"


def _object_delta(in_mean: float, out_mean: float) -> str:
    if out_mean > in_mean + 1.0:
        return "object_count_increase"
    if out_mean < in_mean - 1.0:
        return "object_count_decrease"
    return "object_count_stable"


def _palette_descriptor(introduces: bool, removes: bool) -> str:
    if introduces and removes:
        return "palette_remap"
    if introduces:
        return "palette_expansion"
    if removes:
        return "palette_reduction"
    return "palette_preserving"


def _dimension_descriptor(size_relation: str, large_grid: bool, output_shape_varies: bool) -> str:
    parts = [size_relation]
    parts.append("large_grid" if large_grid else "small_grid")
    if output_shape_varies:
        parts.append("variable_output_shape")
    return "|".join(parts)


def _count_components(grid: list[list[int]]) -> int:
    h = len(grid)
    w = len(grid[0]) if h else 0
    seen: set[tuple[int, int]] = set()
    n_components = 0
    for r in range(h):
        for c in range(w):
            if grid[r][c] == 0 or (r, c) in seen:
                continue
            n_components += 1
            stack = [(r, c)]
            seen.add((r, c))
            colour = grid[r][c]
            while stack:
                rr, cc = stack.pop()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = rr + dr, cc + dc
                    if not (0 <= nr < h and 0 <= nc < w):
                        continue
                    if (nr, nc) in seen or grid[nr][nc] != colour:
                        continue
                    seen.add((nr, nc))
                    stack.append((nr, nc))
    return n_components


def _visible_task_descriptors(challenges: dict[str, dict], task_id: str) -> dict[str, object]:
    task = challenges[task_id]
    input_heights = []
    input_widths = []
    train_component_counts = []
    for pair in task["train"]:
        grid = pair["input"]
        input_heights.append(len(grid))
        input_widths.append(len(grid[0]) if grid else 0)
        train_component_counts.append(_count_components(grid))
    return {
        "max_input_height": max(input_heights),
        "max_input_width": max(input_widths),
        "mean_train_components_visible": round(sum(train_component_counts) / len(train_component_counts), 3),
        "max_train_components_visible": max(train_component_counts),
    }


def _build_pool() -> pd.DataFrame:
    taxonomy = pd.read_csv(ERROR_TAXONOMY)
    stats = pd.read_csv(TASK_STATS)
    summary = pd.read_parquet(TEST_INDEX_SUMMARY)
    challenges = json.loads(TRAIN_CHALLENGES.read_text())
    old_task_ids, old_task_indices = _load_old_pilot()

    stats_cols = [
        "task_id",
        "n_train",
        "n_input_colours",
        "n_output_colours",
        "objects_input_mean",
        "objects_output_mean",
        "size_relation",
        "output_shape_varies",
        "few_demonstrations",
        "large_grid",
        "introduces_colours",
        "removes_colours",
        "split",
    ]
    merged = (
        taxonomy.merge(summary, on=["task_id", "test_index", "oracle_hit", "native_top2_hit"], how="left")
        .merge(stats[stats_cols], on="task_id", how="left")
        .query("split == 'kaggle_training'")
        .copy()
    )
    merged = merged[~merged["task_id"].isin(old_task_ids)].copy()
    merged["old_pilot_task_overlap"] = merged["task_id"].isin(old_task_ids)
    merged["old_pilot_index_overlap"] = merged.apply(
        lambda row: (row["task_id"], int(row["test_index"])) in old_task_indices, axis=1
    )
    merged["component_bucket"] = merged["objects_input_mean"].apply(_component_bucket)
    merged["object_structure"] = merged.apply(
        lambda row: _object_structure(float(row["objects_input_mean"]), bool(row["large_grid"])), axis=1
    )
    merged["object_delta_descriptor"] = merged.apply(
        lambda row: _object_delta(float(row["objects_input_mean"]), float(row["objects_output_mean"])), axis=1
    )
    merged["palette_descriptor"] = merged.apply(
        lambda row: _palette_descriptor(bool(row["introduces_colours"]), bool(row["removes_colours"])), axis=1
    )
    merged["dimension_descriptor"] = merged.apply(
        lambda row: _dimension_descriptor(
            str(row["size_relation"]),
            bool(row["large_grid"]),
            bool(row["output_shape_varies"]),
        ),
        axis=1,
    )
    visible = {
        task_id: _visible_task_descriptors(challenges, task_id) for task_id in merged["task_id"].unique()
    }
    visible_df = pd.DataFrame.from_dict(visible, orient="index").reset_index().rename(columns={"index": "task_id"})
    merged = merged.merge(visible_df, on="task_id", how="left")
    return merged


def _pick_group(pool: pd.DataFrame, n: int) -> list[dict]:
    sort_cols = [
        "dimension_descriptor",
        "n_input_colours",
        "component_bucket",
        "object_structure",
        "palette_descriptor",
        "object_delta_descriptor",
        "task_id",
        "test_index",
    ]
    ordered = pool.sort_values(sort_cols).reset_index(drop=True)
    stride = len(ordered) / n
    picks = sorted({int(i * stride) for i in range(n)})
    while len(picks) < n:
        for candidate_i in range(len(ordered)):
            if candidate_i not in picks:
                picks.append(candidate_i)
                break
        picks = sorted(picks)
    rows = []
    for i in picks[:n]:
        row = ordered.iloc[i]
        rows.append(
            {
                "task_id": row["task_id"],
                "test_index": int(row["test_index"]),
                "compressarc_candidate_count": int(row["n_candidates_total"]),
                "compressarc_oracle_hit": bool(row["oracle_hit"]),
                "compressarc_native_top2_hit": bool(row["native_top2_hit"]),
                "size_relation": row["size_relation"],
                "large_grid": bool(row["large_grid"]),
                "n_train": int(row["n_train"]),
                "n_input_colours": int(row["n_input_colours"]),
                "n_output_colours": int(row["n_output_colours"]),
                "objects_input_mean": round(float(row["objects_input_mean"]), 3),
                "objects_output_mean": round(float(row["objects_output_mean"]), 3),
                "component_bucket": row["component_bucket"],
                "object_structure": row["object_structure"],
                "dimension_descriptor": row["dimension_descriptor"],
                "palette_descriptor": row["palette_descriptor"],
                "object_delta_descriptor": row["object_delta_descriptor"],
                "few_demonstrations": bool(row["few_demonstrations"]),
                "output_shape_varies": bool(row["output_shape_varies"]),
                "mean_train_components_visible": round(float(row["mean_train_components_visible"]), 3),
                "max_train_components_visible": int(row["max_train_components_visible"]),
                "max_input_height": int(row["max_input_height"]),
                "max_input_width": int(row["max_input_width"]),
                "old_pilot_task_overlap": bool(row["old_pilot_task_overlap"]),
                "old_pilot_index_overlap": bool(row["old_pilot_index_overlap"]),
            }
        )
    return rows


def build_validation_manifest() -> dict:
    merged = _build_pool()
    old_task_ids, old_task_indices = _load_old_pilot()

    pool_a2 = merged[~merged["oracle_hit"]]
    pool_b2 = merged[merged["oracle_hit"] & ~merged["native_top2_hit"]]
    pool_c2 = merged[merged["native_top2_hit"]]

    rows = []
    for group, pool, n in (
        ("A2", pool_a2, N_GROUP_A2),
        ("B2", pool_b2, N_GROUP_B2),
        ("C2", pool_c2, N_GROUP_C2),
    ):
        picked = _pick_group(pool, n)
        for row in picked:
            row["group"] = group
            rows.append(row)

    selected_task_ids = {row["task_id"] for row in rows}
    selected_indices = {(row["task_id"], row["test_index"]) for row in rows}
    overlap_tasks = sorted(selected_task_ids & old_task_ids)
    overlap_indices = sorted(selected_indices & old_task_indices)

    return {
        "acquisition": "GEN002B",
        "manifest_id": "GEN002B_VALIDATION_V1_TASK_DISJOINT_STRIDE24",
        "development_data_designation": "GEN002B_DEV_DIAGNOSTIC",
        "pilot_n_test_indices": len(rows),
        "group_sizes": {"A2": N_GROUP_A2, "B2": N_GROUP_B2, "C2": N_GROUP_C2},
        "selection_rule": (
            "Deterministic: remove every task_id present in the old 24-index "
            "pilot, form Group A2/B2/C2 from EXP002D's frozen CompressARC "
            "outcome labels, sort each group by (dimension_descriptor, "
            "n_input_colours, component_bucket, object_structure, "
            "palette_descriptor, object_delta_descriptor, task_id, test_index), "
            "then take an evenly-strided sample. No randomness. No selection "
            "based on expected program-synthesis success."
        ),
        "source_taxonomy": "artifacts/EXP002D/error_taxonomy.csv",
        "source_task_stats": "artifacts/data_audit/task_statistics.csv",
        "source_summary": "artifacts/EXP002D/test_index_summary.parquet",
        "source_challenges": str(TRAIN_CHALLENGES),
        "overlap_checks": {
            "old_pilot_task_count": len(old_task_ids),
            "selected_unique_task_count": len(selected_task_ids),
            "task_level_disjoint": not overlap_tasks,
            "task_overlap_count": len(overlap_tasks),
            "index_level_disjoint": not overlap_indices,
            "index_overlap_count": len(overlap_indices),
            "task_overlaps": overlap_tasks,
            "index_overlaps": overlap_indices,
        },
        "test_indices": rows,
    }


def main() -> None:
    manifest = build_validation_manifest()
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    print(f"Wrote {OUT_MANIFEST} ({manifest['pilot_n_test_indices']} test-indices)")
    for group in ("A2", "B2", "C2"):
        n = sum(1 for row in manifest["test_indices"] if row["group"] == group)
        print(f"  Group {group}: {n}")
    print(json.dumps(manifest["overlap_checks"], indent=2))


if __name__ == "__main__":
    main()
