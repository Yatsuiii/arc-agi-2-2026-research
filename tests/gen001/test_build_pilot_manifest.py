from src.gen001.build_pilot_manifest import N_GROUP_A, N_GROUP_B, N_GROUP_C, build_pilot_sample


def test_group_sizes():
    manifest = build_pilot_sample()
    counts = {"A": 0, "B": 0, "C": 0}
    for row in manifest["test_indices"]:
        counts[row["group"]] += 1
    assert counts == {"A": N_GROUP_A, "B": N_GROUP_B, "C": N_GROUP_C}


def test_deterministic():
    a = build_pilot_sample()
    b = build_pilot_sample()
    assert a == b


def test_no_duplicate_test_indices():
    manifest = build_pilot_sample()
    keys = [(r["task_id"], r["test_index"]) for r in manifest["test_indices"]]
    assert len(keys) == len(set(keys))


def test_group_labels_match_source_taxonomy():
    manifest = build_pilot_sample()
    for row in manifest["test_indices"]:
        if row["group"] == "A":
            assert row["compressarc_oracle_hit"] is False
        elif row["group"] == "B":
            assert row["compressarc_oracle_hit"] is True
            assert row["compressarc_native_top2_hit"] is False
        else:
            assert row["compressarc_native_top2_hit"] is True
