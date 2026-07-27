from src.gen002.search.pruning import colour_set_agreement, pixel_agreement, within_budget


def test_within_budget_accepts_small_programs():
    assert within_budget(program_cost=3, program_depth=2) is True


def test_within_budget_rejects_over_cost():
    assert within_budget(program_cost=999, program_depth=1) is False


def test_within_budget_rejects_over_depth():
    assert within_budget(program_cost=1, program_depth=999) is False


def test_colour_set_agreement_full_match():
    assert colour_set_agreement(frozenset({1, 2}), frozenset({1, 2})) == 1.0


def test_colour_set_agreement_partial():
    assert colour_set_agreement(frozenset({1}), frozenset({1, 2})) == 0.5


def test_colour_set_agreement_empty_target_and_empty_predicted():
    assert colour_set_agreement(frozenset(), frozenset()) == 1.0


def test_pixel_agreement_identical():
    g = ((1, 2), (3, 4))
    assert pixel_agreement(g, g) == 1.0


def test_pixel_agreement_shape_mismatch_is_zero():
    assert pixel_agreement(((1,),), ((1, 2),)) == 0.0


def test_pixel_agreement_partial():
    a = ((1, 2), (3, 4))
    b = ((1, 9), (3, 9))
    assert pixel_agreement(a, b) == 0.5
