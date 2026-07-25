from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.features.structural import (  # noqa: E402
    bounding_box,
    colour_set,
    connected_components,
    demo_colour_pattern,
    expected_output_shape,
    is_periodic_tiling,
    shape,
    size_relation,
    structural_features,
    symmetry_signature,
)


def test_shape_and_colour_set():
    grid = [[1, 2], [3, 1]]
    assert shape(grid) == (2, 2)
    assert colour_set(grid) == {1, 2, 3}


def test_shape_handles_empty_grid():
    assert shape([]) == (0, 0)


def test_connected_components_single_object():
    grid = [[0, 0, 0], [0, 5, 5], [0, 0, 0]]
    components = connected_components(grid, background=0)
    assert len(components) == 1
    assert components[0]["colour"] == 5
    assert components[0]["size"] == 2


def test_connected_components_two_disjoint_objects():
    grid = [[5, 0, 5], [0, 0, 0], [5, 0, 5]]
    components = connected_components(grid, background=0)
    assert len(components) == 4  # four isolated corner cells, 4-connectivity


def test_connected_components_default_background_is_most_common_colour():
    grid = [[0, 0, 0], [0, 0, 0], [0, 0, 7]]
    components = connected_components(grid)
    assert len(components) == 1
    assert components[0]["colour"] == 7


def test_bounding_box():
    assert bounding_box({(1, 1), (2, 3)}) == (1, 2, 1, 3)
    assert bounding_box(set()) is None


def test_symmetry_signature_horizontal():
    grid = [[1, 2, 1], [3, 4, 3]]
    sig = symmetry_signature(grid)
    assert sig["h"] is True
    assert sig["v"] is False


def test_symmetry_signature_diagonal_only_for_square():
    square = [[1, 2], [2, 1]]
    assert symmetry_signature(square)["diag"] is True
    rect = [[1, 2, 3], [4, 5, 6]]
    assert symmetry_signature(rect)["diag"] is False


def test_is_periodic_tiling_detects_repeated_block():
    grid = [[1, 2, 1, 2], [1, 2, 1, 2]]
    assert is_periodic_tiling(grid) is True


def test_is_periodic_tiling_false_for_aperiodic_grid():
    grid = [[1, 2, 3], [4, 5, 6]]
    assert is_periodic_tiling(grid) is False


def test_size_relation_same():
    demos = [([[1, 2], [3, 4]], [[4, 3], [2, 1]]), ([[1]], [[1]])]
    assert size_relation(demos) == "same"


def test_size_relation_constant():
    demos = [([[1, 2]], [[9]]), ([[1, 2, 3]], [[9]])]
    assert size_relation(demos) == "constant"


def test_size_relation_scaled():
    demos = [
        ([[1]], [[1, 1], [1, 1]]),
        ([[1, 2]], [[1, 1, 2, 2], [1, 1, 2, 2]]),
    ]
    assert size_relation(demos) == "scaled"


def test_size_relation_inconsistent_and_empty():
    demos = [([[1]], [[1, 2]]), ([[1]], [[1]])]
    assert size_relation(demos) == "inconsistent"
    assert size_relation([]) == "inconsistent"


def test_expected_output_shape_same():
    demos = [([[1, 2]], [[2, 1]])]
    assert expected_output_shape([[9, 9]], demos) == (1, 2)


def test_expected_output_shape_scaled():
    # Two demos with different input shapes are needed to distinguish "scaled"
    # from "constant" (`size_relation`'s own test covers that ambiguity).
    demos = [
        ([[1]], [[1, 1], [1, 1]]),
        ([[1, 2]], [[1, 1, 2, 2], [1, 1, 2, 2]]),
    ]
    assert expected_output_shape([[9, 9]], demos) == (2, 4)


def test_expected_output_shape_none_when_inconsistent():
    demos = [([[1]], [[1, 2]]), ([[1]], [[1]])]
    assert expected_output_shape([[9]], demos) is None


def test_demo_colour_pattern():
    demos = [([[1, 2]], [[2, 3]])]
    pattern = demo_colour_pattern(demos)
    assert pattern["introduced"] == {3}
    assert pattern["removed"] == {1}
    assert pattern["preserved"] == {2}


def test_structural_features_flags_degenerate_input_copy():
    test_input = [[1, 2], [3, 4]]
    demos = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    features = structural_features(test_input, test_input, demos)
    assert features["is_degenerate_input_copy"] == 1.0


def test_structural_features_flags_constant_fill():
    test_input = [[1, 2], [3, 4]]
    candidate = [[0, 0], [0, 0]]
    demos = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    features = structural_features(candidate, test_input, demos)
    assert features["is_degenerate_constant_fill"] == 1.0


def test_structural_features_output_size_matches_expected_for_same_relation():
    test_input = [[1, 2], [3, 4]]
    good_candidate = [[9, 9], [9, 8]]
    bad_candidate = [[9, 9, 9]]
    demos = [([[5, 6], [7, 8]], [[8, 7], [6, 5]])]
    good = structural_features(good_candidate, test_input, demos)
    bad = structural_features(bad_candidate, test_input, demos)
    assert good["output_size_matches_expected"] == 1.0
    assert bad["output_size_matches_expected"] == 0.0


def test_structural_features_object_count_consistency():
    # Every demo adds exactly one object from input to output.
    demos = [
        ([[0, 0], [0, 0]], [[0, 5], [0, 0]]),
        ([[0, 0, 0]], [[0, 5, 0]]),
    ]
    test_input = [[0, 0], [0, 0]]
    consistent_candidate = [[0, 5], [0, 0]]
    features = structural_features(consistent_candidate, test_input, demos)
    assert features["object_count_consistent_with_demo_pattern"] == 1.0
