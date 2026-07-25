"""EXP002-B execution: score-independent verification + confidence repair.

Bounded mechanism test on the same RUN-001 archive EXP002 used — no new GPU
candidates generated, per this session's explicit scope
(`experiments/EXP002B/PLAN.md` §12, `CORPUS_REQUIREMENTS.md`). Reuses
EXP002's H0 check, fold assignment, evidence builder and feature-AUC table
verbatim (`src/analysis/exp002_verifier_eval.py`) so this pass is a
same-corpus, same-split re-evaluation under the fixed confidence semantics
and the four V0-V3 tracks, not a new experiment design.

V0-V3, per `experiments/EXP002B/PLAN.md` Part 3:
- V0 = frozen NVARC selection (`OriginalSelectionVerifier`).
- V1 = native-score control (`NativeScoreControlVerifier`) — proves the
  pipeline reproduces V0; not evidence of anything else.
- V2 = strict score-independent, heuristic and learned
  (`IndependentHeuristicVerifier`, `IndependentLearnedVerifier`) — the actual
  hypothesis.
- V3 = hybrid (`HybridVerifier`) — competition-engineering only.

`singleton_prior` for every verifier is the empirical P(correct) measured on
Fold A's own singleton (1-unique-candidate) test-indices, never on Fold B or
Fold C, so the abstention fix is itself evaluated out-of-sample.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from src.analysis.exp002_verifier_eval import (
    ARCHIVE_DIR,
    COMPETITION,
    FOLD_SEED,
    REPORTED_PREVIEW,
    assign_folds,
    build_evidence,
    check_h0,
    feature_auc_table,
    load_family_flags,
    oracle_rank,
    truth_digests,
)
from src.harness.adapters.nvarc import load_into_store
from src.harness.features.independence import INDEPENDENT_FEATURES, SCORE_DERIVED_FEATURES
from src.harness.metrics import auc, mean_reciprocal_rank, rank_stats
from src.harness.verifier.base import DEFAULT_SINGLETON_PRIOR
from src.harness.verifier.calibration import calibration_report
from src.harness.verifier.independent import (
    HybridVerifier,
    IndependentHeuristicVerifier,
    IndependentLearnedVerifier,
    NativeScoreControlVerifier,
)
from src.harness.verifier.original import OriginalSelectionVerifier

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "EXP002B"
N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 20260725
COVERAGE_GRID = (1.0, 0.8, 0.6, 0.4, 0.2)

V2_LEARNED_FEATURES = sorted(INDEPENDENT_FEATURES)
V3_HYBRID_FEATURES = sorted(INDEPENDENT_FEATURES | SCORE_DERIVED_FEATURES)


def bootstrap_ci(hits: list[bool], n_bootstrap: int = N_BOOTSTRAP, seed: int = BOOTSTRAP_SEED) -> dict | None:
    """95% bootstrap CI on the mean of a 0/1 list. `None` on an empty list."""
    if not hits:
        return None
    rng = random.Random(seed)
    n = len(hits)
    means = []
    for _ in range(n_bootstrap):
        resample = [hits[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo = means[int(n_bootstrap * 0.025)]
    hi = means[min(int(n_bootstrap * 0.975), n_bootstrap - 1)]
    return {"point": sum(hits) / n, "ci_low": lo, "ci_high": hi, "n": n}


def selective_accuracy_curve(hits: list[bool], confidences: list[float]) -> dict:
    """Accuracy among the top-coverage-fraction most-confident test-indices.

    Rising accuracy as coverage shrinks is what H2's success criterion 5
    ("selective accuracy rises as the verifier abstains on uncertain cases")
    requires; falling or flat accuracy means confidence carries no
    information about correctness even if the ranking itself has some.
    """
    order = sorted(range(len(hits)), key=lambda i: -confidences[i])
    n = len(hits)
    curve = {}
    for coverage in COVERAGE_GRID:
        k = max(1, round(coverage * n))
        subset = [hits[i] for i in order[:k]]
        curve[coverage] = {"accuracy": sum(subset) / len(subset), "n": len(subset)}
    return curve


def measure_singleton_prior(evidence_map: dict, keys: list[tuple], solutions: dict) -> float:
    """P(correct) among Fold A test-indices with exactly one unique candidate.

    The empirical prior EXP002-B's confidence fix backs off to. Measured only
    on Fold A so Fold C's evaluation of it stays out-of-sample.
    """
    hits = []
    for key in keys:
        candidate_set = evidence_map[key].candidate_set
        unique = candidate_set.unique_grid_shas()
        if len(unique) != 1:
            continue
        truth = truth_digests(solutions, key[0], key[1])
        if truth is None:
            continue
        hits.append(unique[0] in truth)
    return sum(hits) / len(hits) if hits else DEFAULT_SINGLETON_PRIOR


def evaluate_track(track_name: str, results_by_key: dict, evidence_map: dict, solutions: dict) -> dict:
    hits, ranks, ranking_confidences, correctness_confidences = [], [], [], []
    abstains = []
    singleton_hits, singleton_correctness = [], []
    per_sufficiency_bucket: dict[str, list[bool]] = {"insufficient (abstain)": [], "some": [], "sufficient": []}

    for key, result in results_by_key.items():
        truth = truth_digests(solutions, key[0], key[1])
        top2 = set(result.top_k(2))
        hit = bool(truth and (top2 & truth))
        hits.append(hit)
        abstains.append(result.abstain)

        rank = None
        if truth:
            for i, sha1 in enumerate(result.ranked_grid_shas, start=1):
                if sha1 in truth:
                    rank = i
                    break
        ranks.append(rank)

        top1 = result.ranked_grid_shas[0] if result.ranked_grid_shas else None
        ranking_confidences.append(result.ranking_confidence)
        correctness_confidences.append(result.correctness_confidence.get(top1, 0.0) if top1 else 0.0)

        if result.abstain:
            singleton_hits.append(hit)
            singleton_correctness.append(result.correctness_confidence.get(top1, 0.0) if top1 else 0.0)
            per_sufficiency_bucket["insufficient (abstain)"].append(hit)
        elif result.candidate_set_sufficiency < 0.5:
            per_sufficiency_bucket["some"].append(hit)
        else:
            per_sufficiency_bucket["sufficient"].append(hit)

    n = len(hits)
    outcomes_for_calibration = [h for h, top1 in zip(hits, (r.ranked_grid_shas[:1] for r in results_by_key.values())) if top1]
    probs_for_calibration = [
        result.correctness_confidence.get(result.ranked_grid_shas[0], 0.0)
        for result in results_by_key.values()
        if result.ranked_grid_shas
    ]

    return {
        "track": track_name,
        "n": n,
        "accuracy_top2": bootstrap_ci(hits),
        "coverage_abstained": sum(abstains) / n if n else None,
        "rank_stats": rank_stats(ranks),
        "mrr": mean_reciprocal_rank(ranks),
        "mean_ranking_confidence": statistics.fmean(ranking_confidences) if ranking_confidences else None,
        "auc_correctness_confidence_vs_hit": (
            auc(probs_for_calibration, outcomes_for_calibration) if probs_for_calibration else None
        ),
        "calibration": (
            calibration_report(probs_for_calibration, outcomes_for_calibration) if probs_for_calibration else None
        ),
        "selective_accuracy_by_coverage": selective_accuracy_curve(hits, correctness_confidences),
        "singleton_subset": {
            "n": len(singleton_hits),
            "error_rate": (1 - sum(singleton_hits) / len(singleton_hits)) if singleton_hits else None,
            "mean_correctness_confidence": (
                statistics.fmean(singleton_correctness) if singleton_correctness else None
            ),
            "false_confidence_rate_at_0.8": (
                sum(1 for c, h in zip(singleton_correctness, singleton_hits) if c >= 0.8 and not h)
                / max(1, sum(1 for c in singleton_correctness if c >= 0.8))
                if any(c >= 0.8 for c in singleton_correctness)
                else None
            ),
        },
        "accuracy_by_sufficiency_bucket": {
            bucket: (sum(vals) / len(vals) if vals else None, len(vals))
            for bucket, vals in per_sufficiency_bucket.items()
        },
    }


def main() -> dict:
    solutions = json.loads((COMPETITION / "arc-agi_evaluation_solutions.json").read_text())
    challenges = json.loads((COMPETITION / "arc-agi_evaluation_challenges.json").read_text())

    store = load_into_store(ARCHIVE_DIR)
    h0 = check_h0(store, solutions)
    if not h0["matches_published_preview"]:
        raise RuntimeError(f"H0 FAILED: got {h0}, expected {REPORTED_PREVIEW}")

    evidence_map = build_evidence(store, challenges)
    task_ids = sorted({k[0] for k in evidence_map})
    flags = load_family_flags(set(task_ids))
    fold_of_task = assign_folds(task_ids, flags)
    all_keys = list(evidence_map)
    fold_a_keys = [k for k in all_keys if fold_of_task[k[0]] == "A"]
    fold_ab_keys = [k for k in all_keys if fold_of_task[k[0]] in ("A", "B")]
    fold_c_keys = [k for k in all_keys if fold_of_task[k[0]] == "C"]

    singleton_prior = measure_singleton_prior(evidence_map, fold_a_keys, solutions)

    def grid_rows(keys):
        rows, labels = [], []
        for key in keys:
            evidence = evidence_map[key]
            truth = truth_digests(solutions, key[0], key[1])
            if truth is None:
                continue
            for sha1, features in evidence.features_by_grid.items():
                rows.append(features)
                labels.append(sha1 in truth)
        return rows, labels

    fit_rows, fit_labels = grid_rows(fold_a_keys)
    fit_dev_rows, fit_dev_labels = grid_rows(fold_ab_keys)

    v2_learned = IndependentLearnedVerifier(feature_names=V2_LEARNED_FEATURES)
    v3_hybrid = HybridVerifier(feature_names=V3_HYBRID_FEATURES)
    fit_ok = len(set(fit_labels)) >= 2
    if fit_ok:
        v2_learned.fit(fit_rows, fit_labels)
        v3_hybrid.fit(fit_rows, fit_labels)

    tracks = {
        "V0_frozen_selector": OriginalSelectionVerifier(),
        "V1_native_score_control": NativeScoreControlVerifier(),
        "V2_independent_heuristic": IndependentHeuristicVerifier(),
    }
    for verifier in tracks.values():
        verifier.singleton_prior = singleton_prior

    reports = {}
    for name, verifier in tracks.items():
        results = {key: verifier.rank(evidence_map[key]) for key in all_keys}
        reports[name] = {
            "full_corpus": evaluate_track(name, results, evidence_map, solutions),
            "fold_c_only": evaluate_track(name, {k: results[k] for k in fold_c_keys}, evidence_map, solutions),
        }

    if fit_ok:
        v2_learned.singleton_prior = singleton_prior
        v3_hybrid.singleton_prior = singleton_prior
        v2l_results = {key: v2_learned.rank(evidence_map[key]) for key in fold_c_keys}
        v3_results = {key: v3_hybrid.rank(evidence_map[key]) for key in fold_c_keys}
        reports["V2_independent_learned"] = {
            "fold_c_only": evaluate_track("V2_independent_learned", v2l_results, evidence_map, solutions),
            "full_corpus": None,
        }
        reports["V3_hybrid"] = {
            "fold_c_only": evaluate_track("V3_hybrid", v3_results, evidence_map, solutions),
            "full_corpus": None,
        }
    else:
        reports["V2_independent_learned"] = {"fold_c_only": None, "full_corpus": None}
        reports["V3_hybrid"] = {"fold_c_only": None, "full_corpus": None}

    oracle_results = {key: oracle_rank(evidence_map[key], truth_digests(solutions, key[0], key[1])) for key in all_keys}
    reports["oracle"] = {
        "full_corpus": evaluate_track("oracle", oracle_results, evidence_map, solutions),
        "fold_c_only": evaluate_track("oracle", {k: oracle_results[k] for k in fold_c_keys}, evidence_map, solutions),
    }

    feature_auc_independent_only = feature_auc_table(fit_dev_rows, fit_dev_labels, V2_LEARNED_FEATURES)

    output = {
        "h0_pipeline_check": h0,
        "corpus": {
            "track": "COMPETITION-ENGINEERING, CONTAMINATED, PARTIAL",
            "n_tasks": len(task_ids),
            "n_test_indices": len(all_keys),
            "n_fold_c_test_indices": len(fold_c_keys),
            "fold_seed": FOLD_SEED,
            "singleton_prior_measured_on_fold_a": singleton_prior,
        },
        "track_reports": reports,
        "feature_auc_independent_only_fit_dev": feature_auc_independent_only,
        "fold_of_task": fold_of_task,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "exp002b_report.json").write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n")
    return output


if __name__ == "__main__":
    result = main()
    print(json.dumps(result["h0_pipeline_check"], indent=2))
    print(json.dumps(result["corpus"], indent=2))
    print("\nFold C accuracy_top2 (point [CI]) by track:")
    for name, report in result["track_reports"].items():
        fc = report.get("fold_c_only")
        if fc and fc["accuracy_top2"]:
            acc = fc["accuracy_top2"]
            print(f"  {name:28s} {acc['point']:.3f} [{acc['ci_low']:.3f}, {acc['ci_high']:.3f}]  n={acc['n']}")
    print("\nSingleton subset false-confidence rate @0.8, by track:")
    for name, report in result["track_reports"].items():
        fc = report.get("full_corpus") or report.get("fold_c_only")
        if fc:
            print(f"  {name:28s} {fc['singleton_subset']}")
    print("\nfeature AUC, independent-only (fit/dev):")
    for name, stats in sorted(
        result["feature_auc_independent_only_fit_dev"].items(),
        key=lambda kv: (kv[1]["auc"] is None, -(kv[1]["auc"] or 0)),
    ):
        print(f"  {name:45s} auc={stats['auc']} n={stats['n']}")
