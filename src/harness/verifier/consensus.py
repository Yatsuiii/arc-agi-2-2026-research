"""B1-B6 — frozen, hand-written rerankers over archived generation/structural evidence.

None of these fit anything; each is a fixed formula over
`src/harness/features/*.py` output, evaluated once per `TaskEvidence`. They
exist to bound what a *learned* verifier (`learned.py`, B7) needs to beat: if
a fixed heuristic already matches it, the learned model is not earning its
complexity (`experiments/EXP002/PLAN.md` REDESIGN criterion "heuristic
consensus works but the learned verifier overfits").
"""

from __future__ import annotations

from src.harness.features.generation import reconstruct_score_kgmon, score_features
from src.harness.features.structural import structural_features
from src.harness.schemas import TaskEvidence, VerificationResult
from src.harness.verifier.base import Verifier, build_result


def _grouped_by_grid(evidence: TaskEvidence) -> dict[str, list]:
    by_grid: dict[str, list] = {}
    for candidate in evidence.candidate_set.candidates:
        by_grid.setdefault(candidate.grid_sha1, []).append(candidate)
    return by_grid


class RawScoreVerifier(Verifier):
    """B1 — rank by each grid's own best `beam_score`, no aggregation."""

    name = "B1_raw_score"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        features = score_features(evidence.candidate_set)
        scores = {
            sha1: f["original_score"] for sha1, f in features.items() if f["original_score"] is not None
        }
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)


class DuplicateFrequencyVerifier(Verifier):
    """B2 — rank by generation-vote count alone: how many times each grid was produced."""

    name = "B2_duplicate_frequency"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        by_grid = _grouped_by_grid(evidence)
        scores = {sha1: float(len(group)) for sha1, group in by_grid.items()}
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)


class AugmentationConsensusVerifier(Verifier):
    """B3 — rank by how many distinct augmentations produced each grid."""

    name = "B3_augmentation_consensus"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        by_grid = _grouped_by_grid(evidence)
        scores = {
            sha1: float(len({c.augmentation_key for c in group if c.augmentation_key is not None}))
            for sha1, group in by_grid.items()
        }
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)


class SeedConsensusVerifier(Verifier):
    """B4 — rank by how many distinct TTT seeds produced each grid.

    RUN-001 used a single fixed TTT seed (`experiments/RUN001/BASELINE_SPEC.md`
    "Seeds"), so on this archive every grid ties at "1 seed" and this baseline
    degenerates to an arbitrary (insertion-order) ranking. Kept in the
    comparison anyway — the degeneracy itself is a reportable fact about what
    RUN-001's archive can and cannot test, not a reason to hide the baseline.
    """

    name = "B4_seed_consensus"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        by_grid = _grouped_by_grid(evidence)
        scores = {
            sha1: float(len({c.seed for c in group if c.seed is not None}))
            for sha1, group in by_grid.items()
        }
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)


class ScoreWeightedConsensusVerifier(Verifier):
    """B5 — votes weighted by mean augmentation score: NVARC's own `score_kgmon`, reconstructed."""

    name = "B5_score_weighted_consensus"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        by_grid = _grouped_by_grid(evidence)
        scores = {}
        for sha1, group in by_grid.items():
            value = reconstruct_score_kgmon(group)
            if value is not None:
                scores[sha1] = value
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)


class TransformationConsistencyVerifier(Verifier):
    """B6 — rank by agreement with the demonstrations' structural pattern.

    Needs `evidence.demo_pairs` and `evidence.test_input`
    (`src/harness/features/structural.py`); without them every grid scores 0
    and the ranking degenerates to candidate order, same failure mode as B4
    when its own precondition is missing.
    """

    name = "B6_transformation_consistency"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        by_grid = _grouped_by_grid(evidence)
        scores = {}
        if evidence.demo_pairs is not None and evidence.test_input is not None:
            for sha1, group in by_grid.items():
                grid = group[0].grid
                features = structural_features(grid, evidence.test_input, evidence.demo_pairs)
                scores[sha1] = _consistency_score(features)
        else:
            scores = {sha1: 0.0 for sha1 in by_grid}
        return build_result(evidence.task_id, evidence.test_index, scores, self.name)


def _consistency_score(features: dict) -> float:
    """Sum of the structural checks that resolved to a value, `None`s excluded.

    Every summand is already a 0/1 (or fractional) agreement score from
    `structural_features`, so the sum is a simple, interpretable count of how
    many structural properties this candidate got right — not fit to
    anything, deliberately, since B6 is a *fixed* heuristic.
    """
    keys = (
        "output_size_matches_expected",
        "introduced_colours_seen_in_demos",
        "removed_colours_seen_in_demos",
        "symmetry_agreement_with_demo_outputs",
        "object_count_consistent_with_demo_pattern",
        "tiling_pattern_consistent_with_demos",
    )
    values = [features[k] for k in keys if features.get(k) is not None]
    score = sum(values) if values else 0.0
    # Degenerate outputs (input copy, constant fill) are always penalised,
    # regardless of which other checks fired.
    score -= features.get("is_degenerate_input_copy", 0.0)
    score -= features.get("is_degenerate_constant_fill", 0.0)
    return score
