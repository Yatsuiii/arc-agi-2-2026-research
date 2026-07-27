import pytest

from src.gen002.dsl.primitives import PRIMITIVES, objects4
from src.gen002.dsl.types import Coordinate, Direction, ProgramError
from src.gen002.grid import from_nested_list


def _g(nested):
    return from_nested_list(nested)


def test_every_primitive_registered_with_a_positive_cost():
    assert len(PRIMITIVES) >= 30
    for prim in PRIMITIVES.values():
        assert prim.cost >= 1
        assert len(prim.params) >= 0


def test_rotate_90():
    g = _g([[1, 2], [3, 4]])
    assert PRIMITIVES["rotate_90"].func(g) == _g([[3, 1], [4, 2]])


def test_rotate_180_twice_is_identity():
    g = _g([[1, 2, 3], [4, 5, 6]])
    once = PRIMITIVES["rotate_180"].func(g)
    twice = PRIMITIVES["rotate_180"].func(once)
    assert twice == g


def test_reflect_horizontal():
    g = _g([[1, 2, 3]])
    assert PRIMITIVES["reflect_horizontal"].func(g) == _g([[3, 2, 1]])


def test_crop_removes_background_border():
    g = _g([[0, 0, 0], [0, 5, 0], [0, 0, 0]])
    assert PRIMITIVES["crop"].func(g) == _g([[5]])


def test_crop_all_background_raises():
    g = _g([[0, 0], [0, 0]])
    with pytest.raises(ProgramError):
        PRIMITIVES["crop"].func(g)


def test_pad():
    g = _g([[1]])
    out = PRIMITIVES["pad"].func(g, 1, 0)
    assert out == _g([[0, 0, 0], [0, 1, 0], [0, 0, 0]])


def test_scale():
    g = _g([[1, 2]])
    out = PRIMITIVES["scale"].func(g, 2)
    assert out == _g([[1, 1, 2, 2], [1, 1, 2, 2]])


def test_scale_out_of_range_raises():
    g = _g([[1]])
    with pytest.raises(ProgramError):
        PRIMITIVES["scale"].func(g, 0)


def test_tile():
    g = _g([[1, 2]])
    out = PRIMITIVES["tile"].func(g, 2, 1)
    assert out == _g([[1, 2], [1, 2]])


def test_translate():
    g = _g([[0, 0, 0], [0, 5, 0], [0, 0, 0]])
    out = PRIMITIVES["translate"].func(g, Direction(0, 1), 1)
    assert out == _g([[0, 0, 0], [0, 0, 5], [0, 0, 0]])


def test_recolour():
    g = _g([[1, 2], [1, 2]])
    assert PRIMITIVES["recolour"].func(g, 1, 9) == _g([[9, 2], [9, 2]])


def test_swap_colours():
    g = _g([[1, 2]])
    assert PRIMITIVES["swap_colours"].func(g, 1, 2) == _g([[2, 1]])


def test_map_colours_by_frequency():
    g = _g([[3, 3, 3, 5]])
    assert PRIMITIVES["map_colours_by_frequency"].func(g) == _g([[0, 0, 0, 1]])


def test_background_replace():
    g = _g([[0, 0, 5]])
    assert PRIMITIVES["background_replace"].func(g, 7) == _g([[7, 7, 5]])


def test_blank_grid():
    assert PRIMITIVES["blank_grid"].func(2, 3, 4) == _g([[4, 4, 4], [4, 4, 4]])


def test_blank_grid_out_of_range():
    with pytest.raises(ProgramError):
        PRIMITIVES["blank_grid"].func(0, 3, 4)


def test_objects4_then_paint():
    g = _g([[0, 5, 0], [0, 0, 0]])
    objs = objects4(g)
    out = PRIMITIVES["paint"].func(g, objs, 9)
    assert out == _g([[0, 9, 0], [0, 0, 0]])


def test_delete_object():
    g = _g([[0, 5, 0]])
    objs = objects4(g)
    assert PRIMITIVES["delete_object"].func(g, objs) == _g([[0, 0, 0]])


def test_overlay_dimension_mismatch_raises():
    a = _g([[1]])
    b = _g([[1, 2]])
    with pytest.raises(ProgramError):
        PRIMITIVES["overlay"].func(a, b)


def test_overlay_transparent_background():
    base = _g([[1, 2]])
    top = _g([[0, 9]])
    assert PRIMITIVES["overlay"].func(base, top) == _g([[1, 9]])


def test_bounding_box_and_fill_bbox():
    g = _g([[0, 0, 0], [0, 5, 0], [0, 0, 0]])
    objs = objects4(g)
    assert PRIMITIVES["bounding_box"].func(g, objs) == _g([[5]])
    filled = PRIMITIVES["fill_bbox"].func(g, objs, 3)
    assert filled == _g([[0, 0, 0], [0, 3, 0], [0, 0, 0]])


def test_outline():
    g = _g([[0, 0, 0, 0], [0, 5, 5, 0], [0, 5, 5, 0], [0, 0, 0, 0]])
    objs = objects4(g)
    out = PRIMITIVES["outline"].func(g, objs, 9)
    # every cell of a 2x2 block touches a background cell, so all 4 outlined
    assert sum(row.count(9) for row in out) == 4


def test_fill_holes():
    g = _g(
        [
            [0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 1, 0, 1, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 0, 0],
        ]
    )
    objs = objects4(g)
    out = PRIMITIVES["fill_holes"].func(g, objs, 8)
    assert out[2][2] == 8


def test_draw_line():
    g = _g([[0, 0, 0]])
    out = PRIMITIVES["draw_line"].func(g, Coordinate(0, 0), Direction(0, 1), 2, 5)
    assert out == _g([[5, 5, 0]])


def test_draw_line_nonpositive_length_raises():
    g = _g([[0]])
    with pytest.raises(ProgramError):
        PRIMITIVES["draw_line"].func(g, Coordinate(0, 0), Direction(0, 1), 0, 5)


def test_conditional():
    a, b = _g([[1]]), _g([[2]])
    assert PRIMITIVES["conditional"].func(True, a, b) == a
    assert PRIMITIVES["conditional"].func(False, a, b) == b


def test_symmetric_horizontal():
    assert PRIMITIVES["symmetric_horizontal"].func(_g([[1, 2, 1]])) is True
    assert PRIMITIVES["symmetric_horizontal"].func(_g([[1, 2, 3]])) is False


def test_equal_grids():
    a = _g([[1]])
    assert PRIMITIVES["equal_grids"].func(a, a) is True
    assert PRIMITIVES["equal_grids"].func(a, _g([[2]])) is False


def test_largest_smallest_selection():
    g = _g([[1, 0, 2, 2, 0], [0, 0, 2, 2, 0], [0, 0, 0, 0, 0]])
    objs = objects4(g)
    assert PRIMITIVES["largest"].func(objs)[0].area == 4
    assert PRIMITIVES["smallest"].func(objs)[0].area == 1


def test_largest_empty_raises():
    with pytest.raises(ProgramError):
        PRIMITIVES["largest"].func(())


def test_no_primitive_reads_a_solutions_file():
    import inspect

    import src.gen002.dsl.primitives as mod

    source = inspect.getsource(mod)
    assert "solution" not in source.lower()
    assert "ground_truth" not in source.lower()
