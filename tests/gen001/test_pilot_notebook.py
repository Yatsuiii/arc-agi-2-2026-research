from src.gen001 import validate_pilot_notebook as v


def test_build_produces_a_notebook():
    from src.gen001.build_pilot_notebook import build

    result = build()
    assert result["output"].endswith("gen001a_pilot.ipynb")
    assert len(result["patches"]) == 8


def test_all_static_checks_pass():
    for check in v.CHECKS:
        assert check() == [], f"{check.__name__} failed"
