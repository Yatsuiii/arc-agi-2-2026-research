"""Tests for EXP002's fold assignment and feature-ablation logic.

Not an end-to-end test of `main()` (that needs the real RUN-001 archive and
competition data, exercised directly by running the module); these cover the
two pieces most load-bearing for the preregistration's data-protocol
requirements: no task crosses a fold, and per-feature AUC is computed
correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis.exp002_verifier_eval import assign_folds, feature_auc_table  # noqa: E402


def test_assign_folds_covers_every_task_exactly_once():
    task_ids = [f"t{i:03d}" for i in range(30)]
    flags = {t: {"size_relation": "same" if i % 2 else "smaller"} for i, t in enumerate(task_ids)}
    fold_of = assign_folds(task_ids, flags)
    assert set(fold_of) == set(task_ids)
    assert set(fold_of.values()) <= {"A", "B", "C"}


def test_assign_folds_is_deterministic_for_a_fixed_seed():
    task_ids = [f"t{i:03d}" for i in range(20)]
    flags = {t: {"size_relation": "same"} for t in task_ids}
    first = assign_folds(task_ids, flags, seed=42)
    second = assign_folds(task_ids, flags, seed=42)
    assert first == second


def test_assign_folds_differs_across_seeds_with_enough_tasks():
    task_ids = [f"t{i:03d}" for i in range(20)]
    flags = {t: {"size_relation": "same"} for t in task_ids}
    a = assign_folds(task_ids, flags, seed=1)
    b = assign_folds(task_ids, flags, seed=2)
    assert a != b


def test_assign_folds_roughly_60_20_20_within_a_stratum():
    task_ids = [f"t{i:03d}" for i in range(30)]
    flags = {t: {"size_relation": "same"} for t in task_ids}
    fold_of = assign_folds(task_ids, flags)
    counts = {f: sum(1 for v in fold_of.values() if v == f) for f in "ABC"}
    assert counts["A"] == 18  # 3/5 of 30
    assert counts["B"] == 6
    assert counts["C"] == 6


def test_assign_folds_missing_stratum_flag_falls_back_to_unknown_bucket():
    fold_of = assign_folds(["t1"], {})
    assert fold_of["t1"] in {"A", "B", "C"}


def test_feature_auc_table_perfect_separator():
    rows = [{"f": 1.0}, {"f": 1.0}, {"f": 0.0}, {"f": 0.0}]
    labels = [True, True, False, False]
    table = feature_auc_table(rows, labels, ["f"])
    assert table["f"]["auc"] == 1.0
    assert table["f"]["n"] == 4


def test_feature_auc_table_skips_none_values():
    rows = [{"f": 1.0}, {"f": None}, {"f": 0.0}]
    labels = [True, False, False]
    table = feature_auc_table(rows, labels, ["f"])
    assert table["f"]["n"] == 2


def test_feature_auc_table_none_when_too_few_paired_values():
    rows = [{"f": 1.0}]
    labels = [True]
    table = feature_auc_table(rows, labels, ["f"])
    assert table["f"]["auc"] is None


def test_feature_auc_table_missing_feature_name_treated_as_none():
    rows = [{"other": 1.0}, {"other": 2.0}]
    labels = [True, False]
    table = feature_auc_table(rows, labels, ["absent"])
    assert table["absent"] == {"auc": None, "n": 0}
