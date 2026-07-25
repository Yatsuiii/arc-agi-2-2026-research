from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.config import HarnessConfig  # noqa: E402
from src.harness.runner import build_evidence_map, run_replay, run_replay_with_verifier  # noqa: E402
from src.harness.schemas import AllocationAction, Candidate, SelectionRecord  # noqa: E402
from src.harness.verifier.original import OriginalSelectionVerifier  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "artifacts" / "run001" / "run001"
COMPETITION_CHALLENGES = (
    ROOT.parent / "competition_2026" / "extracted" / "arc-agi_evaluation_challenges.json"
)


def make_store_with_one_task():
    from src.harness.candidate_store import CandidateStore

    store = CandidateStore()
    store.append_candidates(
        [
            Candidate(task_id="t", test_index=0, grid=[[9]], grid_sha1="a", solver_branch="x"),
            Candidate(task_id="t", test_index=0, grid=[[8]], grid_sha1="b", solver_branch="x"),
        ]
    )
    store.append_selection(
        [
            SelectionRecord("t", 0, "a", rank=1, selected=True, algorithm="score_kgmon"),
            SelectionRecord("t", 0, "b", rank=2, selected=True, algorithm="score_kgmon"),
        ]
    )
    return store


# -- build_evidence_map ----------------------------------------------------------------


def test_build_evidence_map_without_challenges_covers_store_only():
    store = make_store_with_one_task()
    evidence = build_evidence_map(store)
    assert set(evidence) == {("t", 0)}


def test_build_evidence_map_with_challenges_includes_unreached_tasks():
    store = make_store_with_one_task()
    challenges = {
        "t": {"train": [{"input": [[1]], "output": [[2]]}], "test": [{"input": [[3]]}]},
        "unreached": {"train": [{"input": [[1]], "output": [[2]]}], "test": [{"input": [[3]]}]},
    }
    evidence = build_evidence_map(store, challenges)
    assert set(evidence) == {("t", 0), ("unreached", 0)}
    assert evidence[("unreached", 0)].candidate_set.candidates == []
    assert evidence[("t", 0)].demo_pairs == [([[1]], [[2]])]
    assert evidence[("t", 0)].test_input == [[3]]


# -- run_replay_with_verifier ----------------------------------------------------------


def test_run_replay_produces_top2_submission_and_stops_every_task():
    store = make_store_with_one_task()
    evidence = build_evidence_map(store)
    config = HarnessConfig()
    result = run_replay_with_verifier(config, evidence, OriginalSelectionVerifier())

    assert result.submission["t"] == [{"attempt_1": [[9]], "attempt_2": [[8]]}]
    assert result.task_states["t"].stopped is True
    assert result.task_states["t"].action_history == [AllocationAction.STOP]
    assert len(result.trace) == 1


def test_run_replay_pads_with_placeholder_when_fewer_than_two_candidates():
    from src.harness.candidate_store import CandidateStore

    store = CandidateStore()
    store.append_candidates(
        [Candidate(task_id="t", test_index=0, grid=[[9]], grid_sha1="a", solver_branch="x")]
    )
    store.append_selection([SelectionRecord("t", 0, "a", rank=1, selected=True, algorithm="x")])
    evidence = build_evidence_map(store)
    result = run_replay_with_verifier(HarnessConfig(), evidence, OriginalSelectionVerifier())
    assert result.submission["t"] == [{"attempt_1": [[9]], "attempt_2": [[0]]}]


def test_run_replay_handles_task_with_no_candidates_at_all():
    challenges = {"t": {"train": [], "test": [{"input": [[1]]}]}}
    from src.harness.candidate_store import CandidateStore

    evidence = build_evidence_map(CandidateStore(), challenges)
    result = run_replay_with_verifier(HarnessConfig(), evidence, OriginalSelectionVerifier())
    assert result.submission["t"] == [{"attempt_1": [[0]], "attempt_2": [[0]]}]


def test_config_used_is_recorded_in_result():
    store = make_store_with_one_task()
    evidence = build_evidence_map(store)
    config = HarnessConfig()
    result = run_replay_with_verifier(config, evidence, OriginalSelectionVerifier())
    assert result.config_used == {"verifier": "B0_original_nvarc", "frozen_baseline": True}


# -- run_replay: config loading + unknown verifier guard --------------------------------


def test_run_replay_rejects_unknown_verifier_name(tmp_path):
    config = HarnessConfig(candidate_archive_dir=str(tmp_path))
    config.verifier.name = "not_a_real_verifier"
    with pytest.raises(ValueError):
        run_replay(config)


# -- integration against the real RUN-001 archive ----------------------------------------


@pytest.mark.skipif(not ARCHIVE_DIR.exists(), reason="RUN-001 artifact not present in this checkout")
def test_frozen_baseline_reproduces_run001_submission():
    config = HarnessConfig.from_yaml(str(ROOT / "configs" / "harness_v1.yaml"))
    challenges = json.loads(COMPETITION_CHALLENGES.read_text()) if COMPETITION_CHALLENGES.exists() else None
    result = run_replay(config, challenges=challenges)

    archived = json.loads((ARCHIVE_DIR / "submission.json").read_text())
    assert set(result.submission) == set(archived)

    checked = mismatches = 0
    for task_id, entries in archived.items():
        for i, entry in enumerate(entries):
            ours = result.submission[task_id][i]
            for attempt in ("attempt_1", "attempt_2"):
                if entry[attempt] != [[0]]:
                    checked += 1
                    if entry[attempt] != ours[attempt]:
                        mismatches += 1
    assert checked > 0
    assert mismatches == 0
