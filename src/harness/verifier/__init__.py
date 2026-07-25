"""Frozen and learned candidate rerankers, B0-B7. B8 (oracle) needs ground truth
and therefore lives in the EXP002 evaluation script, not here — nothing under
`verifier/` may see a correctness label outside of `learned.LearnedVerifier.fit`.
"""

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

FROZEN_BASELINES = {
    "B0_original_nvarc": OriginalSelectionVerifier,
    "B1_raw_score": RawScoreVerifier,
    "B2_duplicate_frequency": DuplicateFrequencyVerifier,
    "B3_augmentation_consensus": AugmentationConsensusVerifier,
    "B4_seed_consensus": SeedConsensusVerifier,
    "B5_score_weighted_consensus": ScoreWeightedConsensusVerifier,
    "B6_transformation_consistency": TransformationConsistencyVerifier,
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
    "FROZEN_BASELINES",
]
