"""Deterministic replay-only control loop.

Implements the Phase-1 control loop conceptually (ingest -> evidence ->
verify -> allocate -> submission), but only ever executes what
`allocator/actions.py` marks as available. As of this commit that is `STOP`
alone, so this runner never invokes a solver and never generates a new
candidate — it replays a `CandidateStore` an adapter already built and asks a
verifier to rank what is already there. That is also what "support deterministic
replay from archived candidates without rerunning solvers" (Phase 1) requires.

`frozen_baseline=True` with `verifier.name="B0_original_nvarc"` is the mode
that must reproduce RUN-001's own `submission.json` exactly
(`config.py`'s `HarnessConfig.frozen_baseline` docstring); see
`tests/harness/test_runner.py::test_frozen_baseline_reproduces_run001_submission`
for the check against the real archive.
"""

from __future__ import annotations

from pathlib import Path

from src.harness.adapters import nvarc as nvarc_adapter
from src.harness.allocator.actions import require_executable
from src.harness.candidate_store import CandidateStore, demonstration_pairs
from src.harness.candidate_store import test_inputs as get_test_inputs
from src.harness.config import HarnessConfig
from src.harness.schemas import AllocationAction, CandidateSet, HarnessResult, TaskEvidence, TaskState
from src.harness.verifier import FROZEN_BASELINES
from src.harness.verifier.base import Verifier

PLACEHOLDER = [[0]]


def build_evidence_map(
    store: CandidateStore,
    challenges: dict | None = None,
) -> dict[tuple[str, int], TaskEvidence]:
    """One `TaskEvidence` per (task_id, test_index).

    With `challenges` supplied, iterates every task and test index the
    competition contract defines (`src/run001/validate_outputs.py`'s own
    contract check), so tasks the archive never reached still get an entry
    with an empty `CandidateSet` — exactly how RUN-001's own submission
    pre-fills every slot with a placeholder before overwriting what was
    decoded (`experiments/RUN001/BASELINE_SPEC.md` "Submission behaviour").
    Without `challenges`, iterates only what the store actually has, for
    ad hoc use without a full competition file on hand.
    """
    evidence: dict[tuple[str, int], TaskEvidence] = {}
    if challenges is not None:
        for task_id, challenge in challenges.items():
            demo_pairs = demonstration_pairs(challenge)
            inputs = get_test_inputs(challenge)
            for test_index, test_input in enumerate(inputs):
                candidate_set = store.get(task_id, test_index) or CandidateSet(
                    task_id=task_id, test_index=test_index
                )
                evidence[(task_id, test_index)] = TaskEvidence(
                    task_id=task_id,
                    test_index=test_index,
                    candidate_set=candidate_set,
                    demo_pairs=demo_pairs,
                    test_input=test_input,
                )
    else:
        for candidate_set in store.all():
            evidence[(candidate_set.task_id, candidate_set.test_index)] = TaskEvidence(
                task_id=candidate_set.task_id,
                test_index=candidate_set.test_index,
                candidate_set=candidate_set,
            )
    return evidence


def _grids_for_shas(candidate_set: CandidateSet, shas: list[str]) -> list[list[list[int]]]:
    grids = []
    for sha1 in shas:
        candidates = candidate_set.candidates_for_grid(sha1)
        if candidates:
            grids.append(candidates[0].grid)
    return grids


def run_replay_with_verifier(
    config: HarnessConfig,
    evidence_map: dict[tuple[str, int], TaskEvidence],
    verifier: Verifier,
) -> HarnessResult:
    """Rank every `TaskEvidence` with `verifier` and assemble a submission.

    Every task index is STOPped immediately after ranking: there is no live
    compute for a replay to spend more of, so `AllocationAction.STOP` is the
    only decision this loop ever makes, and it goes through
    `require_executable` so that stays true even if this function is edited
    later without noticing the allocator interface has grown teeth.
    """
    task_states: dict[str, TaskState] = {}
    submission: dict[str, list[dict]] = {}
    trace: list[dict] = []

    for (task_id, test_index), evidence in sorted(evidence_map.items()):
        result = verifier.rank(evidence)
        state = task_states.setdefault(task_id, TaskState(task_id=task_id))
        state.evidence[test_index] = evidence
        state.verification[test_index] = result

        top_k = result.top_k(config.top_k_submission)
        grids = _grids_for_shas(evidence.candidate_set, top_k)
        while len(grids) < 2:
            grids.append(PLACEHOLDER)

        submission.setdefault(task_id, [])
        submission[task_id].append({"attempt_1": grids[0], "attempt_2": grids[1]})

        require_executable(AllocationAction.STOP)
        state.stopped = True
        state.action_history.append(AllocationAction.STOP)

        trace.append(
            {
                "task_id": task_id,
                "test_index": test_index,
                "verifier": result.verifier_name,
                "top_k": top_k,
                "confidence_margin": result.confidence_margin,
                "uncertainty": result.uncertainty,
            }
        )

    return HarnessResult(
        task_states=task_states,
        submission=submission,
        trace=trace,
        config_used={"verifier": config.verifier.name, "frozen_baseline": config.frozen_baseline},
    )


def run_replay(config: HarnessConfig, challenges: dict | None = None) -> HarnessResult:
    """Load RUN-001's archive per `config` and replay it through `config.verifier`.

    Only frozen baselines (`verifier/FROZEN_BASELINES`) can be selected by
    name here, since a learned verifier needs `.fit()` called with labelled
    data first — callers that want `B7` build it themselves and call
    `run_replay_with_verifier` directly, the same way EXP002's evaluation
    script does.
    """
    store = nvarc_adapter.load_into_store(Path(config.candidate_archive_dir))
    evidence_map = build_evidence_map(store, challenges)

    verifier_cls = FROZEN_BASELINES.get(config.verifier.name)
    if verifier_cls is None:
        raise ValueError(
            f"{config.verifier.name!r} is not a frozen baseline name "
            f"(one of {sorted(FROZEN_BASELINES)}); a learned verifier must be "
            "fit and passed to run_replay_with_verifier directly."
        )
    return run_replay_with_verifier(config, evidence_map, verifier_cls())
