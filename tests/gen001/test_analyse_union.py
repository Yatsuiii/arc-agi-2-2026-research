from src.gen001.analyse_union import compute_union_metrics


def _candidate(task_id, test_index, grid):
    return {"kind": "candidate", "task_id": task_id, "test_index": test_index, "grid": grid}


def test_union_oracle_and_incremental_coverage():
    pilot_indices = {("t1", 0), ("t2", 0), ("t3", 0), ("t4", 0)}
    solutions = {
        "t1": [[[1]]],
        "t2": [[[2]]],
        "t3": [[[3]]],
        "t4": [[[4]]],
    }
    compressarc = [
        _candidate("t1", 0, [[1]]),  # correct
        _candidate("t2", 0, [[9]]),  # wrong
        _candidate("t3", 0, [[9]]),  # wrong
        _candidate("t4", 0, [[9]]),  # wrong
    ]
    nvarc = [
        _candidate("t1", 0, [[1]]),  # correct, overlap with compressarc
        _candidate("t2", 0, [[2]]),  # correct, incremental
        _candidate("t3", 0, [[9]]),  # wrong, neither solves
        _candidate("t4", 0, [[9]]),  # wrong
    ]

    metrics = compute_union_metrics(compressarc, nvarc, solutions, pilot_indices)

    assert metrics.n_indices == 4
    assert metrics.compressarc_oracle == 0.25
    assert metrics.nvarc_oracle == 0.5
    assert metrics.union_oracle == 0.5
    assert metrics.incremental_nvarc_coverage == 1
    assert metrics.overlap == 1
    assert metrics.compressarc_only == 0
    assert metrics.jaccard == 0.5


def test_no_pilot_indices_is_safe():
    metrics = compute_union_metrics([], [], {}, set())
    assert metrics.n_indices == 0
    assert metrics.union_oracle == 0.0
    assert metrics.jaccard == 0.0


def test_restricts_to_pilot_indices_only():
    pilot_indices = {("t1", 0)}
    solutions = {"t1": [[[1]]], "t2": [[[1]]]}
    compressarc = [_candidate("t1", 0, [[1]]), _candidate("t2", 0, [[1]])]
    nvarc = []
    metrics = compute_union_metrics(compressarc, nvarc, solutions, pilot_indices)
    assert metrics.n_indices == 1
    assert metrics.compressarc_oracle == 1.0
