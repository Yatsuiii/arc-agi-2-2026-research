import inspect
from pathlib import Path

from src.gen002 import pilot_runner
from src.gen002.search.best_first import search_best_first
from src.gen002.search.enumerative import search_enumerative


def test_search_and_dsl_modules_have_no_solutions_file_reference():
    root = Path(__file__).resolve().parents[2] / "src" / "gen002"
    paths = list((root / "dsl").glob("*.py")) + list(
        (root / "search").glob("*.py")
    )
    for path in paths:
        source = path.read_text()
        assert "training_solutions" not in source
        assert "evaluation_solutions" not in source


def test_search_entry_points_have_no_test_or_ground_truth_parameter():
    forbidden = {"test", "target", "solution", "ground_truth"}
    for function in (search_enumerative, search_best_first):
        parameters = set(inspect.signature(function).parameters)
        assert not parameters & forbidden


def test_generation_runner_exposes_challenges_but_not_solutions_path():
    assert pilot_runner.TRAINING_CHALLENGES.name.endswith("_challenges.json")
    assert not hasattr(pilot_runner, "TRAINING_SOLUTIONS")
