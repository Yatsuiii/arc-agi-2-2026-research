from src.gen002.oracle_analysis import run_oracle_analysis


def test_runs_against_the_real_pilot_output():
    result = run_oracle_analysis()
    assert result["n_pilot_indices"] == 24
    assert result["group_a_total"] == 12
    assert result["group_b_total"] == 6
    assert result["group_c_total"] == 6
    assert result["compressarc_oracle_pilot_subset"] == 0.5


def test_union_never_smaller_than_either_operand():
    result = run_oracle_analysis()
    assert result["union_c_p_oracle"] >= result["compressarc_oracle_pilot_subset"]
    assert result["union_c_p_oracle"] >= result["program_synthesis_union_oracle"]


def test_jaccard_in_unit_interval():
    result = run_oracle_analysis()
    assert 0.0 <= result["jaccard_c_p"] <= 1.0
