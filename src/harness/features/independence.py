"""Score-independence classification and the enforcement check built on it.

`experiments/EXP002/RESULTS.md` found that the strongest predictors of
candidate correctness were reconstructions of NVARC's own `score_kgmon`
formula (`reconstructed_score_kgmon` AUC 0.88; `duplicate_generation_count`
and `n_augmentations_producing`, both close paraphrases of the vote count
half of that formula, AUC 0.86) — discriminative because they approximate
what the frozen selector already ranks by, not because they contribute
anything a model-independent verifier could add. EXP002-B's V2 track exists
to test whether evidence genuinely outside that formula carries signal, so
every feature name in this project is classified here as one or the other,
and `assert_score_independent` makes the exclusion an enforced check rather
than a convention someone has to remember.

New feature names must be added to exactly one of the two sets below before
they may be used anywhere; `assert_score_independent` raises on anything
unclassified rather than defaulting it into either bucket.
"""

from __future__ import annotations

SCORE_DERIVED_FEATURES = frozenset(
    {
        # features/generation.py: direct functions of beam_score / score_aug / rank.
        "original_score",
        "normalized_score",
        "original_rank",
        "score_margin",
        "reconstructed_score_kgmon",
        "duplicate_generation_count",  # = votes, half of score_kgmon by definition
        "n_augmentations_producing",  # AUC 0.86 on RUN-001, near-identical to duplicate_generation_count
        "n_seeds_producing",
        "n_solver_branches_producing",
        "generation_order_first",  # search order is itself score-driven (best-first decoding)
        "time_first_appearance_s",
        "rank_stability",
        "score_stability",
        # exp002_verifier_eval.py's set-level (whole-CandidateSet) generation/uncertainty features.
        "set_score_entropy",
        "set_top_margin",
        "set_duplicate_fraction",  # = 1 - unique/total, another vote-count paraphrase
        "set_augmentation_disagreement",
    }
)
"""Every name a caller must not pass to a V2 (score-independent) verifier."""

INDEPENDENT_FEATURES = frozenset(
    {
        # features/structural.py: pure functions of (candidate grid, test input,
        # demonstration pairs). Never reads a beam_score, vote count, or
        # generation order.
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
    }
)
"""Every name that may enter the V2 pipeline. `size_relation_category` from
`structural_features` is deliberately absent — it is categorical, not
numeric, and `verifier/independent.py` does not currently one-hot it; adding
it needs an explicit encoding decision, not a silent pass-through."""


class ScoreLeakageError(ValueError):
    """Raised when a score-derived (or unclassified) feature name reaches a V2 verifier."""


def assert_score_independent(feature_names) -> None:
    """Raise if any name in `feature_names` is score-derived or unclassified.

    Called by `verifier/independent.py` before fitting or ranking, so a
    feature added to `generation.py` later cannot silently leak into V2
    without either being classified here or tripping this check.
    """
    names = set(feature_names)
    leaked = sorted(names & SCORE_DERIVED_FEATURES)
    if leaked:
        raise ScoreLeakageError(
            f"score-derived feature(s) {leaked} may not enter the V2 (score-independent) "
            "verifier pipeline; see features/independence.py SCORE_DERIVED_FEATURES"
        )
    unknown = sorted(names - INDEPENDENT_FEATURES - SCORE_DERIVED_FEATURES)
    if unknown:
        raise ScoreLeakageError(
            f"feature(s) {unknown} are not classified as independent or score-derived; "
            "add them to features/independence.py before using them in V2"
        )
