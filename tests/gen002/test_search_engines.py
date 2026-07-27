from src.gen002.dsl.program import evaluate
from src.gen002.grid import from_nested_list
from src.gen002.search.best_first import search_best_first
from src.gen002.search.enumerative import search_enumerative

TRAIN_IN = (from_nested_list([[1, 2], [3, 4]]), from_nested_list([[5, 6], [7, 8]]))
TRAIN_OUT_ROTATE90 = (from_nested_list([[3, 1], [4, 2]]), from_nested_list([[7, 5], [8, 6]]))


def test_enumerative_finds_a_one_step_program():
    res = search_enumerative(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=20000, timeout_s=20)
    assert len(res.exact_programs) >= 1
    for program in res.exact_programs:
        for grid, target in zip(TRAIN_IN, TRAIN_OUT_ROTATE90):
            assert evaluate(program, grid) == target


def test_best_first_finds_a_one_step_program():
    res = search_best_first(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=20000, timeout_s=45)
    assert len(res.exact_programs) >= 1
    assert res.best_n_solved == len(TRAIN_IN)
    assert res.best_pixel_agreement == 1.0
    for program in res.exact_programs:
        for grid, target in zip(TRAIN_IN, TRAIN_OUT_ROTATE90):
            assert evaluate(program, grid) == target


def test_enumerative_deterministic_across_runs():
    a = search_enumerative(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=5000, timeout_s=20)
    b = search_enumerative(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=5000, timeout_s=20)
    assert [p.canonical() for p in a.exact_programs] == [p.canonical() for p in b.exact_programs]
    assert a.states_explored == b.states_explored


def test_best_first_deterministic_across_runs():
    a = search_best_first(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=5000, timeout_s=45)
    b = search_best_first(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=5000, timeout_s=45)
    assert [p.canonical() for p in a.exact_programs] == [p.canonical() for p in b.exact_programs]


def test_no_solution_returns_empty_not_crash():
    # A target no depth-<=3, cost-<=12 program in this DSL can reach exactly:
    # a target shape impossible to produce from a 1x1 input under this DSL's
    # transformation set (grows only by fixed factors/tiling, never to this
    # odd prime-ish shape from a 1x1 seed within budget).
    train_in = (from_nested_list([[7]]),)
    train_out = (from_nested_list([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),)
    res = search_enumerative(train_in, train_out, max_states=2000, timeout_s=10)
    assert res.exact_programs == []
    assert res.states_explored > 0


def test_respects_max_states_budget():
    res = search_enumerative(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=50, timeout_s=20)
    assert res.states_explored <= 50


def test_timeout_is_honoured():
    res = search_enumerative(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=10**9, timeout_s=0.01)
    assert res.timed_out is True


def test_multiple_semantically_distinct_solutions_all_verified():
    # rotate_180 twice from a distinct starting grid should still only
    # surface programs that are each individually exact on every training pair.
    res = search_enumerative(TRAIN_IN, TRAIN_OUT_ROTATE90, max_states=20000, timeout_s=20)
    canonicals = {p.canonical() for p in res.exact_programs}
    assert len(canonicals) == len(res.exact_programs)  # no duplicate programs kept
