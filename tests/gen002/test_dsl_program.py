import pytest

from src.gen002.dsl.program import evaluate, make_call, make_input, make_literal
from src.gen002.dsl.types import ProgramError, Type
from src.gen002.grid import from_nested_list


def test_input_evaluates_to_the_bound_grid():
    g = from_nested_list([[1, 2]])
    assert evaluate(make_input(), g) == g


def test_literal_evaluates_to_its_value():
    lit = make_literal(5, Type.INTEGER)
    assert evaluate(lit, from_nested_list([[0]])) == 5


def test_call_composes_and_evaluates():
    g = from_nested_list([[1, 2], [3, 4]])
    program = make_call("rotate_180", (make_input(),))
    assert evaluate(program, g) == from_nested_list([[4, 3], [2, 1]])


def test_nested_call_composes_two_primitives():
    g = from_nested_list([[1, 2]])
    inner = make_call("reflect_horizontal", (make_input(),))
    outer = make_call("rotate_180", (inner,))
    assert evaluate(outer, g) == from_nested_list([[1, 2]])


def test_type_mismatch_rejected_at_construction():
    bad_arg = make_literal("not an int", Type.BOOLEAN)
    with pytest.raises(ValueError):
        make_call("scale", (make_input(), bad_arg))


def test_wrong_arity_rejected_at_construction():
    with pytest.raises(ValueError):
        make_call("rotate_90", (make_input(), make_input()))


def test_program_error_wraps_primitive_failure():
    program = make_call("crop", (make_input(),))
    g = from_nested_list([[0, 0], [0, 0]])
    with pytest.raises(ProgramError):
        evaluate(program, g)


def test_cost_sums_node_costs():
    program = make_call(
        "recolour", (make_input(), make_literal(1, Type.COLOUR), make_literal(2, Type.COLOUR))
    )
    assert program.cost() == 1 + 0 + 1 + 1  # primitive + input + 2 literals


def test_canonical_serialization_deterministic():
    g = make_call("rotate_90", (make_input(),))
    assert g.canonical() == make_call("rotate_90", (make_input(),)).canonical()


def test_canonical_serialization_distinguishes_different_programs():
    a = make_call("rotate_90", (make_input(),))
    b = make_call("rotate_180", (make_input(),))
    assert a.canonical() != b.canonical()


def test_depth():
    leaf = make_input()
    one_deep = make_call("rotate_90", (leaf,))
    two_deep = make_call("rotate_90", (one_deep,))
    assert leaf.depth() == 0
    assert one_deep.depth() == 1
    assert two_deep.depth() == 2
