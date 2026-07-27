"""EXP002-D Phase 10: bounded ablation matrix (A0-A6).

Reuses the same fold structure and fitting utilities as `run_eval.py`.
Ablations are cumulative feature-group additions, always logistic
regression except A5 (which swaps in HistGradientBoostingClassifier on
the same feature set, to separate "which features help" from "which model
family helps") and A6 (which reuses A5's scores but swaps the decision
rule from naive to diversity-aware top-2, per the acceptance spec's own
A6 description).

F2 and F3 are bundled by `structural_features` (documented in that
module's own docstring: "implemented once and reported together") -- they
cannot be cleanly separated without forking that function, so A1 already
represents F2+F3 combined, not F2 alone; recorded here as a scoping
decision, not silently glossed over.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.analysis.exp002d import verifiers as V
from src.analysis.exp002d.decision import top2_hits
from src.analysis.exp002d.run_eval import ARTIFACT_DIR, SEED, build_grid_lookup, load_data
from src.analysis.exp002d.stats import mcnemar, oracle_gap_recovery
from src.harness.metrics import brier_score, expected_calibration_error

ABLATIONS = {
    "A0_native_only": {"features": V.F0F1, "model": "beam_score", "diverse": False},
    "A1_structural": {"features": V.STRUCTURAL, "model": "logreg", "diverse": False},
    "A2_plus_provenance": {"features": V.STRUCTURAL + V.F5_PROVENANCE, "model": "logreg", "diverse": False},
    "A3_plus_relational": {"features": V.STRUCTURAL + V.F5_PROVENANCE + V.F4_RELATIONAL, "model": "logreg", "diverse": False},
    "A4_hybrid": {"features": V.FEATURE_SETS["V4"], "model": "logreg", "diverse": False},
    "A5_hybrid_hgb": {"features": V.FEATURE_SETS["V4"], "model": "hgb", "diverse": False},
    "A6_hybrid_hgb_diverse": {"features": V.FEATURE_SETS["V4"], "model": "hgb", "diverse": True},
}


def run_ablation(features: pd.DataFrame, folds: dict, name: str, spec: dict) -> tuple[pd.DataFrame, float]:
    outer_fold_of = folds["outer_fold_of_task"]
    features = features.copy()
    features["outer_fold"] = features["task_id"].map(outer_fold_of)

    start = time.time()
    all_scored = []
    for k in range(5):
        test_df = features[features["outer_fold"] == k].copy()
        fit_df = features[features["outer_fold"] != k]
        if spec["model"] == "beam_score":
            test_df["_score"] = test_df["beam_score_best"]
        else:
            model = V.fit_pointwise(fit_df, spec["features"], spec["model"], SEED)
            test_df["_score"] = V.score_pointwise(model, test_df, spec["features"])
        all_scored.append(test_df)
    runtime_s = time.time() - start
    return pd.concat(all_scored, ignore_index=True), runtime_s


def main() -> None:
    features, candidate_index, folds = load_data()
    grid_lookup = build_grid_lookup(candidate_index)
    v0 = pd.read_parquet(ARTIFACT_DIR / "test_index_summary.parquet")[["task_id", "test_index", "native_top2_hit"]]

    results = {}
    for name, spec in ABLATIONS.items():
        print(f"running {name}...")
        scored, runtime_s = run_ablation(features, folds, name, spec)
        per_test_index = top2_hits(scored, "_score", grid_lookup=grid_lookup, diverse=spec["diverse"])
        merged = per_test_index.merge(v0, on=["task_id", "test_index"])

        y = scored["is_correct"].to_numpy(dtype=int)
        s = scored["_score"].to_numpy(dtype=float)
        auroc = float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else None
        auprc = float(average_precision_score(y, s)) if y.sum() else None

        rank1 = scored.sort_values("_score", ascending=False).groupby(["task_id", "test_index"]).head(1)
        probs = np.clip(rank1["_score"].to_numpy(dtype=float), 0, 1).tolist()
        outcomes = rank1["is_correct"].tolist()

        top2_acc = float(merged["top2_hit"].mean())
        mcn = mcnemar(merged["top2_hit"], merged["native_top2_hit"])

        results[name] = {
            "top1_accuracy": float(merged["top1_hit"].mean()),
            "top2_accuracy": top2_acc,
            "oracle_gap_recovery": oracle_gap_recovery(top2_acc),
            "auroc_candidate_level": auroc,
            "auprc_candidate_level": auprc,
            "brier_score_rank1": brier_score(probs, outcomes),
            "ece_rank1": expected_calibration_error(probs, outcomes),
            "runtime_s": runtime_s,
            "n_features": len(spec["features"]),
            "mcnemar_vs_v0": mcn,
        }

    out_path = ARTIFACT_DIR / "ablation_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"wrote {out_path}")
    for name, r in results.items():
        print(f"{name}: top2={r['top2_accuracy']:.4f} gap_recovery={r['oracle_gap_recovery']} auroc={r['auroc_candidate_level']}")


if __name__ == "__main__":
    main()
