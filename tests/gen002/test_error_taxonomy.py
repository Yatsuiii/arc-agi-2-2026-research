from src.gen002.error_taxonomy import build_taxonomy, classify_failure


def test_failure_categories_are_exhaustive():
    assert classify_failure(
        has_correct_candidate=True, has_candidate=True, best_n_solved=2
    ) == "success"
    assert classify_failure(
        has_correct_candidate=False, has_candidate=True, best_n_solved=2
    ) == "generalization_failure"
    assert classify_failure(
        has_correct_candidate=False, has_candidate=False, best_n_solved=1
    ) == "search_failure"
    assert classify_failure(
        has_correct_candidate=False, has_candidate=False, best_n_solved=0
    ) == "missing_language"


def test_real_pilot_taxonomy_covers_every_index():
    import json

    from src.gen002.error_taxonomy import GEN002A_DIR

    diagnostics = json.loads(
        (GEN002A_DIR / "search_diagnostics.json").read_text()
    )
    rows, summary = build_taxonomy(diagnostics)
    assert len(rows) == 24
    assert sum(summary["category_counts"].values()) == 24
    assert set(summary["category_counts"]) <= {
        "success",
        "generalization_failure",
        "search_failure",
        "missing_language",
    }
