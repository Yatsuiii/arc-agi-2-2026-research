"""EXP002-D Phase 7: top-2 decision rule (naive vs. diversity-aware)."""

from __future__ import annotations

import pandas as pd


def _pixel_distance(a, b) -> float:
    if len(a) != len(b) or len(a) == 0 or len(a[0]) != len(b[0]):
        return 1.0
    total = sum(len(row) for row in a) or 1
    diff = sum(1 for ra, rb in zip(a, b) for ca, cb in zip(ra, rb) if ca != cb)
    return diff / total


def select_top2_naive(group: pd.DataFrame, score_col: str) -> list[str]:
    top2 = group.sort_values(score_col, ascending=False).head(2)
    return top2["grid_sha1"].tolist()


def select_top2_diverse(
    group: pd.DataFrame, score_col: str, grid_lookup: dict[str, list], top_k: int = 10, min_distance: float = 0.05,
) -> list[str]:
    """Pick 1 = top score. Pick 2 = the highest-scoring candidate among the
    next `top_k` whose grid differs from pick 1 by at least `min_distance`
    pixel-mismatch fraction; falls back to naive rank-2 if none clears the
    threshold (a candidate set with only near-duplicate high scorers)."""
    ranked = group.sort_values(score_col, ascending=False)
    if len(ranked) < 2:
        return ranked["grid_sha1"].tolist()
    pick1 = ranked.iloc[0]["grid_sha1"]
    pick1_grid = grid_lookup[pick1]
    candidates = ranked.iloc[1: 1 + top_k]
    for _, row in candidates.iterrows():
        dist = _pixel_distance(grid_lookup[row["grid_sha1"]], pick1_grid)
        if dist >= min_distance:
            return [pick1, row["grid_sha1"]]
    return [pick1, ranked.iloc[1]["grid_sha1"]]


def top2_hits(
    scored: pd.DataFrame, score_col: str, grid_lookup: dict[str, list] | None = None, diverse: bool = False,
) -> pd.DataFrame:
    """One row per test-index: whether the chosen top-2 set contains a
    correct candidate, plus top-1 hit and MRR."""
    rows = []
    for (task_id, test_index), grp in scored.groupby(["task_id", "test_index"]):
        ranked = grp.sort_values(score_col, ascending=False).reset_index(drop=True)
        top1_hit = bool(ranked.iloc[0]["is_correct"]) if len(ranked) else False
        if diverse and grid_lookup is not None:
            picks = select_top2_diverse(grp, score_col, grid_lookup)
        else:
            picks = select_top2_naive(grp, score_col)
        picks_set = set(picks)
        top2_hit = bool(grp[grp["grid_sha1"].isin(picks_set)]["is_correct"].any())
        correct_rank = None
        if ranked["is_correct"].any():
            correct_rank = int(ranked[ranked["is_correct"]].index[0]) + 1
        mrr = 1.0 / correct_rank if correct_rank else 0.0
        rows.append(
            {
                "task_id": task_id, "test_index": test_index,
                "top1_hit": top1_hit, "top2_hit": top2_hit,
                "correct_rank": correct_rank, "mrr": mrr,
            }
        )
    return pd.DataFrame(rows)
