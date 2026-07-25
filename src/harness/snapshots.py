"""Reconstruct budget snapshots from an archive's own per-candidate timestamps.

RUN-001's notebook never emitted explicit checkpoints ("snapshot 1, snapshot
2, ..."), but every candidate record carries `generation_order` and
`cumulative_task_s` (`src/run001/archive.py` schema, populated live by the
real run, `experiments/RUN001/RESULTS.md`). That is enough to replay the
candidate set exactly as it stood at any earlier point in the task's
compute, without inventing anything the run did not actually produce — the
distinction the preregistration draws as "do not fabricate fine-grained
snapshots if only final candidates were archived" (`experiments/EXP002/PLAN.md`
is silent on this because EXP002 does not need snapshots; EXP003 will, and
this module exists now so that experiment can be built on real reconstructed
history rather than the final state alone).
"""

from __future__ import annotations

from src.harness.schemas import BudgetSnapshot, CandidateSet


def snapshots_by_generation_order(
    candidate_set: CandidateSet, cutoffs: list[int] | None = None
) -> list[BudgetSnapshot]:
    """One snapshot per cutoff: every grid whose first-seen generation_order <= cutoff.

    `cutoffs` defaults to every distinct generation_order actually present,
    i.e. the finest replay the archive supports. Candidates without a
    `generation_order` are ignored — there is no ordering to replay them at.
    """
    timed = [c for c in candidate_set.candidates if c.generation_order is not None]
    if not timed:
        return []
    timed.sort(key=lambda c: c.generation_order)

    if cutoffs is None:
        cutoffs = sorted({c.generation_order for c in timed})

    snapshots = []
    for cutoff in sorted(cutoffs):
        shas = tuple(dict.fromkeys(c.grid_sha1 for c in timed if c.generation_order <= cutoff))
        snapshots.append(
            BudgetSnapshot(
                task_id=candidate_set.task_id,
                test_index=candidate_set.test_index,
                budget=float(cutoff),
                candidate_shas=shas,
                budget_unit="generation_order",
            )
        )
    return snapshots


def snapshots_by_time(
    candidate_set: CandidateSet, n_snapshots: int = 8
) -> list[BudgetSnapshot]:
    """`n_snapshots` evenly spaced cutoffs over `cumulative_task_s`, plus the final state.

    Used where a time-based budget axis is more meaningful than a raw
    generation count (EXP003's "half budget" / "full budget" comparisons).
    """
    timed = [c for c in candidate_set.candidates if c.cumulative_task_s is not None]
    if not timed:
        return []
    timed.sort(key=lambda c: c.cumulative_task_s)
    final_time = timed[-1].cumulative_task_s
    if final_time <= 0:
        return []

    cutoffs = [final_time * (i + 1) / n_snapshots for i in range(n_snapshots)]
    snapshots = []
    for cutoff in cutoffs:
        shas = tuple(
            dict.fromkeys(c.grid_sha1 for c in timed if c.cumulative_task_s <= cutoff)
        )
        snapshots.append(
            BudgetSnapshot(
                task_id=candidate_set.task_id,
                test_index=candidate_set.test_index,
                budget=cutoff,
                candidate_shas=shas,
                budget_unit="cumulative_task_s",
            )
        )
    return snapshots
