"""EXP002 execution: does model-independent evidence rerank RUN-001's candidates
better than NVARC's frozen selector?

Two evidence tracks, per `experiments/EXP002/PLAN.md` and the PREP-001/harness
brief's "Separate two evidence tracks" requirement:

1. **Competition-engineering track.** RUN-001's own 72-task, 94-test-input
   candidate archive, scored against `arc-agi_evaluation_solutions.json`.
   Every number from this track is labelled CONTAMINATED (the checkpoint was
   trained on this split, `docs/DATASET_AUDIT.md` §6.1) and PARTIAL (RUN-001
   is `TIMED_OUT`, `experiments/RUN001/RESULTS.md`). Comparative numbers
   (verifier vs. B0) are less affected than absolute ones, since contamination
   shifts every baseline's numerator together — the same argument
   `experiments/EXP001/PLAN.md` §10-11 makes; this is still not clean
   evidence and is never reported as such.
2. **Mechanism test.** EXP001-A already proved, on 800 clean ARC-AGI-1 tasks
   with zero pretraining contamination, that this project's oracle-vs-realised
   headroom methodology reproduces published numbers exactly
   (`experiments/EXP001/RESULT.md` §7, H0). This script's own equivalent
   computation is checked against `experiments/RUN001/RESULTS.md`'s
   independently-published preview (30/94 generated, 23/94 selected, 7.4pp
   headroom) as its own H0 gate below, before anything else runs. A full
   structural-feature mechanism test against CompressARC's own traces is not
   possible: those traces store only a score and a hash per candidate, not
   the grid itself (`src/analysis/headroom.py` module docstring), so none of
   `structural.py`'s features are computable there.

Frozen baselines B0-B6 need no fitting and are evaluated on every test index
that has candidates. The learned baseline B7 is fit on Fold A, evaluated on
Fold C only; Fold B is reserved for calibration/threshold selection this pass
does not yet need. Task-family folds are built from
`docs/DATASET_AUDIT.md` §6.4's deterministic proxy flags, splitting by task
so no candidate record crosses a fold boundary.

Run: `python -m src.analysis.exp002_verifier_eval`
"""

from __future__ import annotations

import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from src.harness.adapters.nvarc import load_into_store
from src.harness.candidate_store import demonstration_pairs
from src.harness.candidate_store import test_inputs as get_test_inputs
from src.harness.features.generation import score_features
from src.harness.features.structural import structural_features
from src.harness.features.uncertainty import (
    augmentation_disagreement,
    duplicate_fraction,
    score_distribution_entropy,
    top_margin,
)
from src.harness.metrics import (
    auc,
    mean_reciprocal_rank,
    rank_stats,
    recovered_headroom,
)
from src.harness.schemas import TaskEvidence
from src.harness.verifier.base import build_result_from_probabilities
from src.harness.verifier.calibration import calibration_report
from src.harness.verifier.consensus import (
    AugmentationConsensusVerifier,
    DuplicateFrequencyVerifier,
    RawScoreVerifier,
    ScoreWeightedConsensusVerifier,
    SeedConsensusVerifier,
    TransformationConsistencyVerifier,
)
from src.harness.verifier.learned import LearnedVerifier
from src.harness.verifier.original import OriginalSelectionVerifier

ROOT = Path(__file__).resolve().parents[2]
COMPETITION = ROOT.parent / "competition_2026" / "extracted"
ARCHIVE_DIR = ROOT / "artifacts" / "run001" / "run001"
DATA_AUDIT = ROOT / "artifacts" / "data_audit" / "task_statistics.csv"
OUT_DIR = ROOT / "artifacts" / "EXP002"

FOLD_SEED = 20260725  # date this fold assignment was frozen; never changed post hoc
LEARNED_FEATURES = [
    "original_score",
    "normalized_score",
    "score_margin",
    "duplicate_generation_count",
    "reconstructed_score_kgmon",
    "n_augmentations_producing",
    "output_size_matches_expected",
    "introduced_colours_seen_in_demos",
    "removed_colours_seen_in_demos",
    "symmetry_agreement_with_demo_outputs",
    "object_count_consistent_with_demo_pattern",
    "tiling_pattern_consistent_with_demos",
    "is_degenerate_input_copy",
    "is_degenerate_constant_fill",
    "set_score_entropy",
    "set_top_margin",
    "set_duplicate_fraction",
    "set_augmentation_disagreement",
]

REPORTED_PREVIEW = {"oracle": 30, "selected": 23, "n": 94, "headroom_pp": 7.4}


# -- H0: pipeline check against RUN-001's own published preview ----------------------


def check_h0(store, solutions: dict) -> dict:
    oracle_hits = selected_hits = n = 0
    for candidate_set in store.all():
        truth = truth_digests(solutions, candidate_set.task_id, candidate_set.test_index)
        if truth is None:
            continue
        n += 1
        digests = {c.grid_sha1 for c in candidate_set.candidates}
        if digests & truth:
            oracle_hits += 1
        if set(candidate_set.frozen_selected(2)) & truth:
            selected_hits += 1
    result = {
        "n": n,
        "oracle_hits": oracle_hits,
        "selected_hits": selected_hits,
        "headroom_pp": round(100 * (oracle_hits - selected_hits) / n, 2) if n else None,
        "matches_published_preview": (
            n == REPORTED_PREVIEW["n"]
            and oracle_hits == REPORTED_PREVIEW["oracle"]
            and selected_hits == REPORTED_PREVIEW["selected"]
        ),
    }
    return result


# -- ground truth ------------------------------------------------------------------


def truth_digests(solutions: dict, task_id: str, test_index: int) -> set[str] | None:
    from src.run001.archive import grid_digest

    grids = solutions.get(task_id)
    if grids is None or test_index >= len(grids):
        return None
    return {grid_digest(grids[test_index])}


# -- task-family folds (docs/DATASET_AUDIT.md §6.4) -----------------------------------


def load_family_flags(task_ids: set[str]) -> dict[str, dict]:
    flags = {}
    with open(DATA_AUDIT) as handle:
        for row in csv.DictReader(handle):
            if row["task_id"] in task_ids:
                flags[row["task_id"]] = {
                    "size_relation": row["size_relation"],
                    "output_shape_varies": row["output_shape_varies"] == "True",
                    "introduces_colours": row["introduces_colours"] == "True",
                    "removes_colours": row["removes_colours"] == "True",
                    "few_demonstrations": row["few_demonstrations"] == "True",
                    "large_grid": row["large_grid"] == "True",
                }
    return flags


def assign_folds(task_ids: list[str], flags: dict[str, dict], seed: int = FOLD_SEED) -> dict[str, str]:
    """Stratify by `size_relation` (docs/DATASET_AUDIT.md §6.4's primary proxy),
    round-robin each stratum across Fold A (fit, 60%) / B (calibration, 20%) /
    C (untouched final eval, 20%), so every task lands in exactly one fold and
    small strata still spread across folds rather than collapsing into one.
    """
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for task_id in task_ids:
        stratum = flags.get(task_id, {}).get("size_relation", "unknown")
        by_stratum[stratum].append(task_id)

    rng = random.Random(seed)
    fold_of: dict[str, str] = {}
    targets = ["A", "A", "A", "B", "C"]  # 3:1:1 -> 60% / 20% / 20%
    for stratum, ids in by_stratum.items():
        ids = sorted(ids)
        rng.shuffle(ids)
        for i, task_id in enumerate(ids):
            fold_of[task_id] = targets[i % len(targets)]
    return fold_of


# -- feature assembly ----------------------------------------------------------------


def build_evidence(store, challenges: dict) -> dict[tuple[str, int], TaskEvidence]:
    evidence_map = {}
    for candidate_set in store.all():
        challenge = challenges.get(candidate_set.task_id)
        if challenge is None:
            continue
        demo_pairs = demonstration_pairs(challenge)
        inputs = get_test_inputs(challenge)
        test_input = inputs[candidate_set.test_index] if candidate_set.test_index < len(inputs) else None

        gen_features = score_features(candidate_set)
        set_features = {
            "set_score_entropy": score_distribution_entropy(candidate_set),
            "set_top_margin": top_margin(candidate_set),
            "set_duplicate_fraction": duplicate_fraction(candidate_set),
            "set_augmentation_disagreement": augmentation_disagreement(candidate_set),
        }

        features_by_grid = {}
        for sha1 in candidate_set.unique_grid_shas():
            row = dict(gen_features.get(sha1, {}))
            if test_input is not None:
                grid = candidate_set.candidates_for_grid(sha1)[0].grid
                row.update(structural_features(grid, test_input, demo_pairs))
            row.update(set_features)
            features_by_grid[sha1] = row

        evidence_map[(candidate_set.task_id, candidate_set.test_index)] = TaskEvidence(
            task_id=candidate_set.task_id,
            test_index=candidate_set.test_index,
            candidate_set=candidate_set,
            features_by_grid=features_by_grid,
            demo_pairs=demo_pairs,
            test_input=test_input,
        )
    return evidence_map


# -- oracle (B8) — the only place ground truth is used for ranking, and only here ------


def oracle_rank(evidence: TaskEvidence, truth: set[str] | None):
    """B8: probability 1.0 for the correct grid(s) if generated, 0.0 otherwise.

    `build_result_from_probabilities` ranks by probability, so this puts any
    generated correct grid first without needing a separate ordering step.
    """
    digests = evidence.candidate_set.unique_grid_shas()
    return build_result_from_probabilities(
        evidence.task_id,
        evidence.test_index,
        {sha1: (1.0 if (truth and sha1 in truth) else 0.0) for sha1 in digests},
        "B8_oracle",
    )


# -- evaluation ------------------------------------------------------------------------


def evaluate_verifier(verifier_name, results_by_key, evidence_map, solutions) -> dict:
    """Every EXP002 metric, computed from one verifier's ranking on every key."""
    hits = ranks = []
    hits, ranks, margins, entropies = [], [], [], []
    per_family = defaultdict(lambda: {"hit": 0, "n": 0})
    per_size_bucket = defaultdict(lambda: {"hit": 0, "n": 0})
    per_margin_bucket = defaultdict(lambda: {"hit": 0, "n": 0})
    probs_for_calibration, outcomes_for_calibration = [], []
    family_flags = load_family_flags({k[0] for k in results_by_key})

    for key, result in results_by_key.items():
        task_id, test_index = key
        evidence = evidence_map[key]
        truth = truth_digests(solutions, task_id, test_index)
        top2 = set(result.top_k(2))
        hit = bool(truth and (top2 & truth))
        hits.append(hit)

        rank = None
        if truth:
            for i, sha1 in enumerate(result.ranked_grid_shas, start=1):
                if sha1 in truth:
                    rank = i
                    break
        ranks.append(rank)
        margins.append(result.confidence_margin)
        entropies.append(result.uncertainty)

        stratum = family_flags.get(task_id, {}).get("size_relation", "unknown")
        per_family[stratum]["n"] += 1
        per_family[stratum]["hit"] += int(hit)

        n_candidates = len(evidence.candidate_set.candidates)
        bucket = "1-4" if n_candidates <= 4 else ("5-16" if n_candidates <= 16 else "17+")
        per_size_bucket[bucket]["n"] += 1
        per_size_bucket[bucket]["hit"] += int(hit)

        margin_bucket = (
            "high (>=0.3)" if result.confidence_margin >= 0.3
            else "low (<0.3)"
        )
        per_margin_bucket[margin_bucket]["n"] += 1
        per_margin_bucket[margin_bucket]["hit"] += int(hit)

        if truth and result.ranked_grid_shas:
            top1 = result.ranked_grid_shas[0]
            probs_for_calibration.append(result.probability_correct.get(top1, 0.0))
            outcomes_for_calibration.append(top1 in truth)

    n = len(hits)
    accuracy = sum(hits) / n if n else None
    calibration = (
        calibration_report(probs_for_calibration, outcomes_for_calibration)
        if probs_for_calibration
        else None
    )
    return {
        "verifier": verifier_name,
        "n": n,
        "accuracy_top2": accuracy,
        "hits": hits,
        "margins": margins,
        "ranks_of_correct_candidate": ranks,
        "rank_stats": rank_stats(ranks),
        "mrr": mean_reciprocal_rank(ranks),
        "mean_confidence_margin": statistics.fmean(margins) if margins else None,
        "auc_top1_probability_vs_correct": (
            auc(list(probs_for_calibration), list(outcomes_for_calibration))
            if probs_for_calibration
            else None
        ),
        "accuracy_by_task_family": {
            k: round(v["hit"] / v["n"], 3) if v["n"] else None for k, v in per_family.items()
        } | {f"{k}__n": v["n"] for k, v in per_family.items()},
        "accuracy_by_candidate_set_size": {
            k: round(v["hit"] / v["n"], 3) if v["n"] else None for k, v in per_size_bucket.items()
        } | {f"{k}__n": v["n"] for k, v in per_size_bucket.items()},
        "accuracy_by_margin_bucket": {
            k: round(v["hit"] / v["n"], 3) if v["n"] else None for k, v in per_margin_bucket.items()
        } | {f"{k}__n": v["n"] for k, v in per_margin_bucket.items()},
        "calibration": calibration,
    }


def feature_auc_table(rows: list[dict], labels: list[bool], feature_names: list[str]) -> dict:
    """Per-feature AUC for discriminating correct from incorrect candidates.

    This is `experiments/EXP002/PLAN.md`'s H1 check (>= 1 feature with AUC >
    0.60) and the required "feature ablation table" in one computation.
    Evaluated over individual candidate grids, not test indices, since that is
    the natural unit for "does this feature discriminate correct from
    incorrect" and gives a much larger n than the 94 test-index granularity
    everything else in this module uses.
    """
    table = {}
    for name in feature_names:
        values = [row.get(name) for row in rows]
        paired = [(v, label) for v, label in zip(values, labels) if v is not None]
        if len(paired) < 2:
            table[name] = {"auc": None, "n": len(paired)}
            continue
        scores, outcomes = zip(*paired)
        table[name] = {"auc": auc(list(scores), list(outcomes)), "n": len(paired)}
    return table


def main() -> dict:
    solutions = json.loads((COMPETITION / "arc-agi_evaluation_solutions.json").read_text())
    challenges = json.loads((COMPETITION / "arc-agi_evaluation_challenges.json").read_text())

    store = load_into_store(ARCHIVE_DIR)
    h0 = check_h0(store, solutions)
    if not h0["matches_published_preview"]:
        raise RuntimeError(
            f"H0 FAILED: pipeline does not reproduce RUN-001's published preview. "
            f"Got {h0}, expected {REPORTED_PREVIEW}. Stopping — nothing below this "
            "is trustworthy if the archive isn't being read the same way twice."
        )

    evidence_map = build_evidence(store, challenges)
    task_ids = sorted({k[0] for k in evidence_map})
    flags = load_family_flags(set(task_ids))
    fold_of_task = assign_folds(task_ids, flags)

    frozen = {
        "B0_original_nvarc": OriginalSelectionVerifier(),
        "B1_raw_score": RawScoreVerifier(),
        "B2_duplicate_frequency": DuplicateFrequencyVerifier(),
        "B3_augmentation_consensus": AugmentationConsensusVerifier(),
        "B4_seed_consensus": SeedConsensusVerifier(),
        "B5_score_weighted_consensus": ScoreWeightedConsensusVerifier(),
        "B6_transformation_consistency": TransformationConsistencyVerifier(),
    }

    all_keys = list(evidence_map)
    fold_c_keys = [k for k in all_keys if fold_of_task[k[0]] == "C"]

    reports = {}
    full_rankings = {}
    for name, verifier in frozen.items():
        results = {key: verifier.rank(evidence_map[key]) for key in all_keys}
        full_rankings[name] = results
        reports[name] = {
            "full_corpus": evaluate_verifier(name, results, evidence_map, solutions),
            "fold_c_only": evaluate_verifier(
                name, {k: results[k] for k in fold_c_keys}, evidence_map, solutions
            ),
        }

    # B8 oracle (upper bound); the only ranking allowed to see ground truth.
    oracle_results = {
        key: oracle_rank(evidence_map[key], truth_digests(solutions, key[0], key[1]))
        for key in all_keys
    }
    full_rankings["B8_oracle"] = oracle_results
    reports["B8_oracle"] = {
        "full_corpus": evaluate_verifier("B8_oracle", oracle_results, evidence_map, solutions),
        "fold_c_only": evaluate_verifier(
            "B8_oracle", {k: oracle_results[k] for k in fold_c_keys}, evidence_map, solutions
        ),
    }

    # B7 learned: fit on Fold A grids, evaluate on Fold C test indices only.
    # Feature AUC (H1) is measured on Fold A+B (fit/dev) grids, never on Fold C.
    fold_a_keys = [k for k in all_keys if fold_of_task[k[0]] == "A"]
    fold_ab_keys = [k for k in all_keys if fold_of_task[k[0]] in ("A", "B")]

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
    feature_auc = feature_auc_table(fit_dev_rows, fit_dev_labels, LEARNED_FEATURES)

    b7_report = None
    b7_feature_importances = None
    if len(set(fit_labels)) >= 2:
        learned = LearnedVerifier(feature_names=LEARNED_FEATURES)
        learned.fit(fit_rows, fit_labels)
        b7_results = {key: learned.rank(evidence_map[key]) for key in fold_c_keys}
        full_rankings["B7_learned_logistic"] = b7_results
        b7_report = evaluate_verifier("B7_learned_logistic", b7_results, evidence_map, solutions)
        b7_feature_importances = learned.feature_importances()
    reports["B7_learned_logistic"] = {"fold_c_only": b7_report, "full_corpus": None}

    # Recovered headroom (primary metric), fold-C-only for the fair comparison.
    original_acc = reports["B0_original_nvarc"]["fold_c_only"]["accuracy_top2"]
    oracle_acc = reports["B8_oracle"]["fold_c_only"]["accuracy_top2"]
    recovered = {}
    for name, report in reports.items():
        fold_c = report.get("fold_c_only")
        if fold_c is None or fold_c["accuracy_top2"] is None:
            continue
        recovered[name] = recovered_headroom(fold_c["accuracy_top2"], original_acc, oracle_acc)

    output = {
        "h0_pipeline_check": h0,
        "corpus": {
            "track": "COMPETITION-ENGINEERING, CONTAMINATED, PARTIAL",
            "n_tasks": len(task_ids),
            "n_test_indices": len(all_keys),
            "n_fold_a_tasks": sum(1 for v in fold_of_task.values() if v == "A"),
            "n_fold_b_tasks": sum(1 for v in fold_of_task.values() if v == "B"),
            "n_fold_c_tasks": sum(1 for v in fold_of_task.values() if v == "C"),
            "n_fold_c_test_indices": len(fold_c_keys),
            "fold_seed": FOLD_SEED,
        },
        "baseline_reports": reports,
        "recovered_headroom_fold_c": recovered,
        "feature_auc_fit_dev": feature_auc,
        "b7_feature_importances": b7_feature_importances,
        "fold_of_task": fold_of_task,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "exp002_report.json").write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n")
    return output


if __name__ == "__main__":
    result = main()
    print(json.dumps(result["h0_pipeline_check"], indent=2))
    print(json.dumps(result["corpus"], indent=2))
    print("\nfold-C accuracy_top2 by verifier:")
    for name, report in result["baseline_reports"].items():
        fold_c = report.get("fold_c_only")
        if fold_c:
            print(f"  {name:30s} {fold_c['accuracy_top2']}")
    print("\nrecovered headroom (fold C):")
    print(json.dumps(result["recovered_headroom_fold_c"], indent=2))
    print("\nfeature AUC (fit/dev, H1 check, >0.60 needed):")
    for name, stats in sorted(
        result["feature_auc_fit_dev"].items(),
        key=lambda kv: (kv[1]["auc"] is None, -(kv[1]["auc"] or 0)),
    ):
        print(f"  {name:45s} auc={stats['auc']} n={stats['n']}")
