"""V1 (native-score control), V2 (strict score-independent), and V3 (hybrid).

`experiments/EXP002B/PLAN.md` Part 3 defines four tracks; `V0` is
`original.OriginalSelectionVerifier` (unchanged) and `V1`-`V3` live here:

- **V1** is `consensus.ScoreWeightedConsensusVerifier` relabelled — a
  from-scratch reconstruction of NVARC's own `score_kgmon`. Its only job is
  proving the evaluation pipeline can reproduce `V0` (it ties V0 exactly on
  RUN-001, `experiments/EXP002/RESULTS.md`); no independence or novelty claim
  is made about it, and `paper/CLAIM_LEDGER.md` must never cite V1 as
  evidence for anything beyond that reproduction check.
- **V2** is the actual hypothesis: a heuristic and a learned variant, both
  built only from `features/independence.INDEPENDENT_FEATURES` and checked at
  construction time by `assert_score_independent` so a score-derived feature
  cannot reach either without the check failing first.
- **V3** deliberately combines independent and score-derived evidence and is
  reported only as competition-engineering evidence
  (`experiments/EXP002B/RESULTS.md`), never as support for the
  model-independent-verification claim V2 exists to test.
"""

from __future__ import annotations

from src.harness.features.independence import INDEPENDENT_FEATURES, assert_score_independent
from src.harness.features.structural import structural_features
from src.harness.schemas import TaskEvidence, VerificationResult
from src.harness.verifier.base import Verifier, build_result
from src.harness.verifier.consensus import ScoreWeightedConsensusVerifier
from src.harness.verifier.learned import LearnedVerifier

CONSISTENCY_KEYS = (
    "output_size_matches_expected",
    "introduced_colours_seen_in_demos",
    "removed_colours_seen_in_demos",
    "symmetry_agreement_with_demo_outputs",
    "object_count_consistent_with_demo_pattern",
    "tiling_pattern_consistent_with_demos",
)
assert_score_independent(CONSISTENCY_KEYS)  # fails at import time if this list ever drifts


class NativeScoreControlVerifier(ScoreWeightedConsensusVerifier):
    """V1 — pipeline-reproduction control. See module docstring for its one job."""

    name = "V1_native_score_control"


class IndependentHeuristicVerifier(Verifier):
    """V2-heuristic — fixed structural-consistency score. No fitting, no native score.

    Ranks by count of agreeing consistency checks minus degenerate-output and
    contradiction penalties, all drawn from `INDEPENDENT_FEATURES` only.
    """

    name = "V2_independent_heuristic"

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        representative_grid: dict[str, list] = {}
        for candidate in evidence.candidate_set.candidates:
            representative_grid.setdefault(candidate.grid_sha1, candidate.grid)

        scores: dict[str, float] = {}
        if evidence.demo_pairs is not None and evidence.test_input is not None:
            for sha1, grid in representative_grid.items():
                features = structural_features(grid, evidence.test_input, evidence.demo_pairs)
                scores[sha1] = _consistency_score(features)
        else:
            scores = dict.fromkeys(representative_grid, 0.0)
        return build_result(
            evidence.task_id, evidence.test_index, scores, self.name, singleton_prior=self.singleton_prior
        )


def _consistency_score(features: dict) -> float:
    """Sum of agreeing checks minus degeneracy and contradiction penalties.

    Every summand is a feature named in `INDEPENDENT_FEATURES`
    (`features/independence.py`); this function is the one place their
    combination rule lives, so a design change to how V2-heuristic weighs
    evidence touches one function, not every call site.
    """
    values = [features[k] for k in CONSISTENCY_KEYS if features.get(k) is not None]
    score = sum(values) if values else 0.0
    score -= features.get("is_degenerate_input_copy", 0.0)
    score -= features.get("is_degenerate_constant_fill", 0.0)
    score -= 0.1 * features.get("contradiction_count", 0.0)
    return score


class IndependentLearnedVerifier(LearnedVerifier):
    """V2-learned — `LearnedVerifier` restricted to `INDEPENDENT_FEATURES`.

    The restriction is enforced, not just documented: construction raises
    `ScoreLeakageError` if `feature_names` contains anything score-derived or
    unclassified.
    """

    name = "V2_independent_learned"

    def __init__(self, feature_names: list[str] | None = None, C: float = 1.0):
        feature_names = feature_names if feature_names is not None else sorted(INDEPENDENT_FEATURES)
        assert_score_independent(feature_names)
        super().__init__(feature_names, C=C)


class HybridVerifier(LearnedVerifier):
    """V3 — native score plus independent evidence, deliberately unrestricted.

    Reported only as a competition-engineering system
    (`experiments/EXP002B/RESULTS.md`): it may win on accuracy by leaning on
    the same score V1 already reproduces, which would say nothing new about
    model-independent verification even if it does win.
    """

    name = "V3_hybrid"
