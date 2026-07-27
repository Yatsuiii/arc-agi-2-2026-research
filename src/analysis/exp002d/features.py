"""EXP002-D Phase 4: feature groups F0-F6.

F0/F1 (native, score-derived) and F2/F3 (score-independent grid + train-
example consistency, via `src.harness.features.structural.structural_features`)
are computed per candidate row. F4 (candidate-set relational) is computed
within each test-index's own candidate set only. F5 (provenance) is thin in
this corpus (single CompressARC process per task, no augmentation/seed
ensemble) -- documented, not fabricated.

Score-independence enforcement follows `src.harness.features.independence`'s
pattern: every feature name used by a V2/V3 (strict score-independent) model
must be in INDEPENDENT_FEATURES, never in SCORE_DERIVED_FEATURES.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.harness.features.structural import structural_features

REPO_ROOT = Path(__file__).resolve().parents[3]
CHALLENGES_PATH = Path(
    "/home/Yatsuiii/arc-agi-2-2026/competition_2026/extracted/arc-agi_training_challenges.json"
)

# F0/F1: native, score-derived. F4 relational features are classified
# SCORE_DERIVED here too, per LEAKAGE_AUDIT.md's preregistered decision
# (beam-search revisit frequency is a search-behaviour signal, not a pure
# grid property) -- they are available only to hybrid tracks (V4/V5/V6).
SCORE_DERIVED_FEATURES = frozenset(
    {
        "beam_score_best",
        "beam_score_mean",
        "beam_score_min",
        "beam_score_percentile",
        "native_rank_or_zero",
        "multiplicity",
        "consensus_frequency",
        "distance_from_modal",
        "mean_distance_from_set",
        "discovery_order_frac",
    }
)

# F2 (structural.py's grid features) + F3 (train-example consistency,
# also inside structural_features) + F5 (thin provenance).
INDEPENDENT_FEATURES = frozenset(
    {
        "output_size_matches_expected",
        "n_colours_introduced_by_candidate",
        "n_colours_removed_by_candidate",
        "introduced_colours_seen_in_demos",
        "removed_colours_seen_in_demos",
        "symmetry_agreement_with_demo_outputs",
        "object_count",
        "object_count_consistent_with_demo_pattern",
        "tiling_pattern_consistent_with_demos",
        "is_degenerate_input_copy",
        "is_degenerate_constant_fill",
        "is_valid_grid",
        "grid_complexity",
        "contradiction_count",
        "task_steps_run",
        "task_elapsed_s",
        "task_hit_time_guard",
    }
)


class ScoreLeakageError(ValueError):
    pass


def assert_score_independent(feature_names) -> None:
    names = set(feature_names)
    leaked = sorted(names & SCORE_DERIVED_FEATURES)
    if leaked:
        raise ScoreLeakageError(f"score-derived feature(s) {leaked} may not enter a V2/V3 model")
    unknown = sorted(names - INDEPENDENT_FEATURES - SCORE_DERIVED_FEATURES)
    if unknown:
        raise ScoreLeakageError(f"feature(s) {unknown} are not classified; add to this module")


def _load_challenges() -> dict:
    return json.loads(CHALLENGES_PATH.read_text())


def _demo_pairs(task: dict) -> list[tuple[list, list]]:
    return [(pair["input"], pair["output"]) for pair in task["train"]]


def _to_nested_list(grid) -> list[list[int]]:
    """Parquet round-trips a list-of-lists column as a numpy object array of
    numpy arrays (ragged, so `.tolist()` alone does not recurse);
    `structural.py`'s functions expect plain `list[list[int]]`."""
    return [[int(cell) for cell in row] for row in grid]


def _task_summary_fields() -> dict[str, dict]:
    """Per-task steps_run/elapsed_s/hit_time_guard from ACQ-001's task_summary CSVs."""
    fields: dict[str, dict] = {}
    for shard, letter in (("shard_a", "A"), ("shard_b", "B")):
        csv_path = REPO_ROOT / f"artifacts/ACQ001/{shard}_output/acq001_{letter.lower()}/archive/task_summary.{letter}.csv"
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            fields[row["task_id"]] = {
                "task_steps_run": float(row.get("solve_seconds", 0.0) or 0.0),
                "task_elapsed_s": float(row.get("solve_seconds", 0.0) or 0.0),
                "task_hit_time_guard": float(row.get("hit_time_guard", 0.0) or 0.0),
            }
    return fields


def compute_candidate_features(candidate_index: pd.DataFrame) -> pd.DataFrame:
    """F0/F1/F2/F3/F5 -- one row per candidate. F4 is added separately
    (compute_relational_features) since it needs the full per-test-index set."""
    challenges = _load_challenges()
    task_fields = _task_summary_fields()

    rows = []
    n = len(candidate_index)
    for i, rec in enumerate(candidate_index.itertuples(index=False)):
        if i % 10000 == 0:
            print(f"  candidate features: {i}/{n}")
        task = challenges[rec.task_id]
        demo_pairs = _demo_pairs(task)
        test_input = task["test"][rec.test_index]["input"]
        cand_grid = _to_nested_list(rec.grid)
        struct = structural_features(cand_grid, test_input, demo_pairs)

        rank = rec.native_rank if pd.notna(rec.native_rank) else 0
        row = {
            "task_id": rec.task_id,
            "test_index": rec.test_index,
            "grid_sha1": rec.grid_sha1,
            # F0/F1 native
            "beam_score_best": rec.beam_score_best,
            "beam_score_mean": rec.beam_score_mean,
            "beam_score_min": rec.beam_score_min,
            "native_rank_or_zero": rank,
            # F2+F3 (structural.py)
            **{
                k: (float(v) if isinstance(v, bool) else (v if v is not None else -1.0))
                for k, v in struct.items()
                if k != "size_relation_category"
            },
            # F5 provenance (thin)
            **task_fields.get(rec.task_id, {"task_steps_run": 0.0, "task_elapsed_s": 0.0, "task_hit_time_guard": 0.0}),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def compute_relational_features(candidate_index: pd.DataFrame) -> pd.DataFrame:
    """F4: relational to the rest of the same test-index's candidate set.

    Cross-shape pairs are trivially at distance 1.0 (no cell overlap is even
    well-defined), so pairwise Hamming distance is only computed within each
    same-shape bucket, vectorised with numpy broadcasting -- a pure-Python
    O(k^2) loop over the largest groups here (up to ~1000 candidates) would
    be too slow for this many test-indices.
    """
    import numpy as np

    rows = []
    for (task_id, test_index), sub in candidate_index.groupby(["task_id", "test_index"]):
        n_total = len(sub)
        total_mult = sub["multiplicity"].sum()
        modal_idx = sub["multiplicity"].idxmax()
        modal_shape = tuple(np.array(_to_nested_list(sub.loc[modal_idx, "grid"])).shape)
        max_order = sub["first_discovery_order"].max() or 1

        grids = [_to_nested_list(g) for g in sub["grid"].tolist()]
        shapes = [(len(g), len(g[0]) if g else 0) for g in grids]
        modal_local_idx = sub.index.get_loc(modal_idx)

        dist_from_modal = [1.0] * n_total
        sum_dist_within_bucket = [0.0] * n_total
        n_in_bucket = [0] * n_total

        by_shape: dict[tuple, list[int]] = {}
        for local_i, s in enumerate(shapes):
            by_shape.setdefault(s, []).append(local_i)

        for s, indices in by_shape.items():
            arr = np.array([grids[i] for i in indices])  # (k, H, W)
            k = len(indices)
            diff_matrix = (arr[:, None, :, :] != arr[None, :, :, :]).mean(axis=(2, 3))  # (k, k)
            for bucket_pos, local_i in enumerate(indices):
                n_in_bucket[local_i] = k
                sum_dist_within_bucket[local_i] = float(diff_matrix[bucket_pos].sum())
                if s == modal_shape:
                    modal_bucket_pos = indices.index(modal_local_idx) if modal_local_idx in indices else None
                    if modal_bucket_pos is not None:
                        dist_from_modal[local_i] = float(diff_matrix[bucket_pos, modal_bucket_pos])

        for local_i, (idx, r) in enumerate(sub.iterrows()):
            mean_dist = (
                sum_dist_within_bucket[local_i] + (n_total - n_in_bucket[local_i]) * 1.0
            ) / n_total
            rows.append(
                {
                    "task_id": task_id,
                    "test_index": test_index,
                    "grid_sha1": r["grid_sha1"],
                    "consensus_frequency": r["multiplicity"] / total_mult,
                    "distance_from_modal": dist_from_modal[local_i],
                    "mean_distance_from_set": mean_dist,
                    "discovery_order_frac": r["first_discovery_order"] / max_order if max_order else 0.0,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    out_dir = REPO_ROOT / "artifacts/EXP002D"
    candidate_index = pd.read_parquet(out_dir / "canonical_candidate_index.parquet")

    print("computing per-candidate features (F0/F1/F2/F3/F5)...")
    cand_feats = compute_candidate_features(candidate_index)
    print("computing relational features (F4)...")
    rel_feats = compute_relational_features(candidate_index)

    features = candidate_index[
        ["task_id", "test_index", "grid_sha1", "multiplicity", "is_correct", "native_selected", "family", "shard"]
    ].merge(cand_feats, on=["task_id", "test_index", "grid_sha1"]).merge(
        rel_feats, on=["task_id", "test_index", "grid_sha1"]
    )
    features["beam_score_percentile"] = features.groupby(["task_id", "test_index"])["beam_score_best"].rank(pct=True)

    path = out_dir / "candidate_features.parquet"
    features.to_parquet(path, index=False)
    print(f"wrote {path} ({len(features)} rows, {features.shape[1]} columns)")


if __name__ == "__main__":
    main()
