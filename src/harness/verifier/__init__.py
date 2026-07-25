"""Frozen and learned candidate rerankers.

`FROZEN_BASELINES` (B0-B6, EXP002) needs no fitting. `VERIFIER_TRACKS`
(V0-V3, EXP002-B) is the score-independence-aware framework: V0 is `B0`
itself, V1 is a relabelled `B5` (pipeline-reproduction control only), V2 is
the actual score-independent hypothesis (heuristic + learned, both enforced
by `features.independence.assert_score_independent`), V3 is an unrestricted
hybrid reported as competition-engineering evidence only
(`verifier/independent.py`'s module docstring). B7/B8 (learned, oracle) need
ground truth and therefore live in the EXP00x evaluation scripts, not here —
nothing under `verifier/` may see a correctness label outside of
`learned.LearnedVerifier.fit`.
"""

from src.harness.verifier.consensus import (
    AugmentationConsensusVerifier,
    DuplicateFrequencyVerifier,
    RawScoreVerifier,
    ScoreWeightedConsensusVerifier,
    SeedConsensusVerifier,
    TransformationConsistencyVerifier,
)
from src.harness.verifier.independent import (
    HybridVerifier,
    IndependentHeuristicVerifier,
    IndependentLearnedVerifier,
    NativeScoreControlVerifier,
)
from src.harness.verifier.learned import LearnedVerifier
from src.harness.verifier.original import OriginalSelectionVerifier

FROZEN_BASELINES = {
    "B0_original_nvarc": OriginalSelectionVerifier,
    "B1_raw_score": RawScoreVerifier,
    "B2_duplicate_frequency": DuplicateFrequencyVerifier,
    "B3_augmentation_consensus": AugmentationConsensusVerifier,
    "B4_seed_consensus": SeedConsensusVerifier,
    "B5_score_weighted_consensus": ScoreWeightedConsensusVerifier,
    "B6_transformation_consistency": TransformationConsistencyVerifier,
}

VERIFIER_TRACKS = {
    "V0_frozen_selector": OriginalSelectionVerifier,
    "V1_native_score_control": NativeScoreControlVerifier,
    "V2_independent_heuristic": IndependentHeuristicVerifier,
    # V2_independent_learned and V3_hybrid need .fit() with labelled data;
    # built directly by exp002b_verifier_eval.py, not instantiated bare here.
}

__all__ = [
    "OriginalSelectionVerifier",
    "RawScoreVerifier",
    "DuplicateFrequencyVerifier",
    "AugmentationConsensusVerifier",
    "SeedConsensusVerifier",
    "ScoreWeightedConsensusVerifier",
    "TransformationConsistencyVerifier",
    "LearnedVerifier",
    "NativeScoreControlVerifier",
    "IndependentHeuristicVerifier",
    "IndependentLearnedVerifier",
    "HybridVerifier",
    "FROZEN_BASELINES",
    "VERIFIER_TRACKS",
]
