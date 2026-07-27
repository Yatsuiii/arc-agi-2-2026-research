from src.gen002.dsl.program import make_call, make_input
from src.gen002.grid import from_nested_list
from src.gen002.search.cache import SearchCache


def test_memoizes_repeat_evaluation():
    g = from_nested_list([[1, 2], [3, 4]])
    cache = SearchCache((g,))
    program = make_call("rotate_90", (make_input(),))
    cache.evaluate_on_all(program)
    n_after_first = cache.n_evaluations
    cache.evaluate_on_all(program)
    assert cache.n_evaluations == n_after_first


def test_evaluate_on_all_returns_one_result_per_input():
    a = from_nested_list([[1]])
    b = from_nested_list([[2]])
    cache = SearchCache((a, b))
    program = make_input()
    results = cache.evaluate_on_all(program)
    assert results == (("ok", a), ("ok", b))


def test_is_dead_true_on_program_error():
    g = from_nested_list([[0, 0], [0, 0]])
    cache = SearchCache((g,))
    program = make_call("crop", (make_input(),))  # all-background grid
    assert cache.is_dead(program) is True


def test_is_dead_false_for_valid_program():
    g = from_nested_list([[1, 2], [3, 4]])
    cache = SearchCache((g,))
    program = make_call("rotate_90", (make_input(),))
    assert cache.is_dead(program) is False


def test_semantic_signature_equal_for_equivalent_programs():
    g = from_nested_list([[1, 2], [3, 4]])
    cache = SearchCache((g,))
    a = make_call("rotate_90", (make_input(),))
    b = make_call("rotate_270", (make_call("rotate_180", (make_input(),)),))
    assert cache.semantic_signature(a) == cache.semantic_signature(b)
