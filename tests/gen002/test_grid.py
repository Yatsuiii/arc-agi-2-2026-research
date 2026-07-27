from src.gen002.grid import (
    background_candidates,
    bounding_region,
    colour_histogram,
    dims,
    from_nested_list,
    periodicity,
    symmetry_axes,
    to_nested_list,
)


def test_round_trip():
    nested = [[1, 2], [3, 4]]
    assert to_nested_list(from_nested_list(nested)) == nested


def test_dims():
    g = from_nested_list([[0, 0, 0], [0, 0, 0]])
    assert dims(g) == (2, 3)


def test_colour_histogram():
    g = from_nested_list([[1, 1, 2], [2, 2, 2]])
    hist = colour_histogram(g)
    assert hist[1] == 2
    assert hist[2] == 4


def test_background_candidates_prefers_zero_on_tie():
    g = from_nested_list([[0, 5], [5, 0]])
    assert background_candidates(g)[0] == 0


def test_symmetry_horizontal():
    g = from_nested_list([[1, 2, 1], [3, 4, 3]])
    axes = symmetry_axes(g)
    assert axes["horizontal"] is True
    assert axes["vertical"] is False


def test_symmetry_diagonal_requires_square():
    g = from_nested_list([[1, 2], [2, 1]])
    assert symmetry_axes(g)["diagonal"] is True


def test_periodicity_full_grid_when_aperiodic():
    g = from_nested_list([[1, 2], [3, 4]])
    assert periodicity(g) == (2, 2)


def test_periodicity_detects_tiling():
    g = from_nested_list([[1, 2, 1, 2], [1, 2, 1, 2]])
    assert periodicity(g) == (1, 2)


def test_bounding_region():
    g = from_nested_list([[0, 0, 0], [0, 5, 0], [0, 0, 0]])
    assert bounding_region(g, background=0) == (1, 1, 1, 1)


def test_bounding_region_all_background():
    g = from_nested_list([[0, 0], [0, 0]])
    assert bounding_region(g, background=0) is None
