from src.gen002.grid import from_nested_list
from src.gen002.objects import extract_objects
from src.gen002.scene_graph import build_scene_graph, sort_by_colour, sort_by_position, sort_by_size


def test_adjacent_edge():
    g = from_nested_list([[1, 0, 2], [0, 0, 0]])
    objs = extract_objects(g, background=0, connectivity=8)
    graph = build_scene_graph(objs)
    # not adjacent: separated by background column
    assert not any(e.relation == "adjacent" for e in graph.edges)


def test_containment_edge():
    g = from_nested_list(
        [
            [1, 1, 1],
            [1, 2, 1],
            [1, 1, 1],
        ]
    )
    objs = extract_objects(g, background=0, multicolour=False, connectivity=4)
    assert len(objs) == 2
    graph = build_scene_graph(objs)
    assert any(e.relation == "contains" for e in graph.edges)


def test_equal_shape_edge():
    g = from_nested_list([[1, 0, 2], [0, 0, 0]])
    objs = extract_objects(g, background=0)
    graph = build_scene_graph(objs)
    assert any(e.relation == "equal_shape" for e in graph.edges)


def test_sort_by_size_descending():
    g = from_nested_list([[1, 0, 2, 2], [0, 0, 2, 2]])
    objs = extract_objects(g, background=0)
    ordered = sort_by_size(objs)
    assert ordered[0].area >= ordered[-1].area


def test_sort_by_position_reading_order():
    g = from_nested_list([[0, 2], [1, 0]])
    objs = extract_objects(g, background=0)
    ordered = sort_by_position(objs)
    assert ordered[0].bbox[0] <= ordered[-1].bbox[0]


def test_sort_by_colour_deterministic():
    g = from_nested_list([[3, 0, 1]])
    objs = extract_objects(g, background=0)
    ordered = sort_by_colour(objs)
    assert [sorted(o.colour_set) for o in ordered] == sorted(sorted(o.colour_set) for o in objs)
