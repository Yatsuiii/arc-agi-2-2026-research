from src.gen002.grid import from_nested_list
from src.gen002.objects import extract_objects


def test_single_object():
    g = from_nested_list([[0, 0, 0], [0, 5, 0], [0, 0, 0]])
    objs = extract_objects(g, background=0)
    assert len(objs) == 1
    assert objs[0].area == 1
    assert objs[0].colour_set == frozenset({5})


def test_two_disjoint_objects_4_connectivity():
    g = from_nested_list([[1, 0, 2], [0, 0, 0]])
    objs = extract_objects(g, background=0, connectivity=4)
    assert len(objs) == 2


def test_diagonal_only_touching_needs_8_connectivity():
    g = from_nested_list([[1, 0], [0, 1]])
    objs4 = extract_objects(g, background=0, connectivity=4)
    objs8 = extract_objects(g, background=0, connectivity=8)
    assert len(objs4) == 2
    assert len(objs8) == 1


def test_different_colours_split_by_default():
    g = from_nested_list([[1, 2]])
    objs = extract_objects(g, background=0)
    assert len(objs) == 2


def test_multicolour_merges_touching_different_colours():
    g = from_nested_list([[1, 2]])
    objs = extract_objects(g, background=0, multicolour=True)
    assert len(objs) == 1
    assert objs[0].colour_set == frozenset({1, 2})


def test_holes_ring_has_one_hole():
    g = from_nested_list(
        [
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
        ]
    )
    objs = extract_objects(g, background=0)
    assert len(objs) == 1
    assert objs[0].holes == 1


def test_no_hole_for_solid_block():
    g = from_nested_list([[1, 1], [1, 1]])
    objs = extract_objects(g, background=0)
    assert objs[0].holes == 0


def test_shape_id_translation_invariant():
    g = from_nested_list([[1, 0, 0], [0, 0, 1]])
    objs = extract_objects(g, background=0)
    assert len(objs) == 2
    assert objs[0].shape_id == objs[1].shape_id


def test_touches_and_overlaps():
    g = from_nested_list([[1, 1, 2]])
    objs = extract_objects(g, background=0)
    a, b = objs
    assert a.touches(b)
    assert not a.overlaps(b)


def test_invalid_connectivity_rejected():
    g = from_nested_list([[1]])
    import pytest

    with pytest.raises(ValueError):
        extract_objects(g, background=0, connectivity=5)
