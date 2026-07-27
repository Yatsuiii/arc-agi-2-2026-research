import json

from src.gen002.pilot_runner import (
    PILOT_MANIFEST,
    _render_candidates,
    config_hash,
    load_challenges,
    load_manifest,
    run_task,
)
from src.gen002.grid import from_nested_list
from src.gen002.search.enumerative import search_enumerative


def test_manifest_loads_24_rows():
    rows = load_manifest()
    assert len(rows) == 24


def test_manifest_matches_gen001a_exactly():
    rows = load_manifest()
    gen001a = json.loads(PILOT_MANIFEST.read_text())["test_indices"]
    assert rows == gen001a


def test_challenges_load_and_are_a_dict():
    challenges = load_challenges()
    assert isinstance(challenges, dict)
    assert len(challenges) > 0


def test_run_task_returns_json_safe_data():
    challenges = load_challenges()
    task_id = "d631b094"
    task = challenges[task_id]
    train_inputs = tuple(from_nested_list(p["input"]) for p in task["train"])
    train_outputs = tuple(from_nested_list(p["output"]) for p in task["train"])
    test_input = from_nested_list(task["test"][0]["input"])
    result = run_task(task_id, train_inputs, train_outputs, {0: test_input}, config_hash())
    # must round-trip through JSON without error -- this is the resume contract
    json.dumps(result)
    assert result["task_id"] == task_id
    assert "0" in result["per_index"]
    assert "s0_candidates" in result["per_index"]["0"]


def test_render_candidates_deduplicates_grids():
    train_in = (from_nested_list([[1, 2]]),)
    train_out = (from_nested_list([[2, 1]]),)  # reflect_horizontal, and equivalently other programs
    res = search_enumerative(train_in, train_out, max_states=20000, timeout_s=20)
    test_input = from_nested_list([[3, 4]])
    records = _render_candidates("S0", "t", 0, test_input, res, "cfg")
    grids = [tuple(map(tuple, r["candidate_grid"])) for r in records]
    assert len(grids) == len(set(grids))


def test_render_candidates_no_ground_truth_parameter():
    import inspect

    sig = inspect.signature(_render_candidates)
    assert "target" not in sig.parameters
    assert "solution" not in sig.parameters
    assert "ground_truth" not in sig.parameters
