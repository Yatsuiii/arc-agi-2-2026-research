"""Sanity checks against real, visible ARC training examples — never a
test-pair output, only demonstration inputs any solver may legally see."""

import json
from pathlib import Path

import pytest

from src.gen002.grid import background_candidates, dims, from_nested_list
from src.gen002.objects import extract_objects
from src.gen002.scene_graph import build_scene_graph

CHALLENGES = (
    Path(__file__).resolve().parents[2].parent
    / "competition_2026"
    / "extracted"
    / "arc-agi_training_challenges.json"
)


@pytest.mark.skipif(not CHALLENGES.exists(), reason="competition data not present")
def test_object_extraction_on_real_training_input():
    data = json.loads(CHALLENGES.read_text())
    task_id = sorted(data.keys())[0]
    demo_input = data[task_id]["train"][0]["input"]
    grid = from_nested_list(demo_input)

    assert dims(grid) == (len(demo_input), len(demo_input[0]))
    bg = background_candidates(grid)[0]
    objs = extract_objects(grid, background=bg, connectivity=8)
    graph = build_scene_graph(objs)
    assert graph.objects == objs
    total_cells = sum(o.area for o in objs)
    assert total_cells <= dims(grid)[0] * dims(grid)[1]
