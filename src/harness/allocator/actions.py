"""The allocator's action vocabulary, and which actions this codebase can actually execute.

`AllocationAction` (defined in `schemas.py`, imported here for convenience) is
the full Phase-1 interface. `EXECUTABLE_ACTIONS` is deliberately much
smaller: as of this commit, only `STOP` has an implementation behind it —
`MORE_NVARC`, `MORE_AUGMENTATIONS`, `MORE_TTT` and `MORE_SEEDS` would require
launching a new Kaggle GPU run, `RUN_TRM` requires a TRM checkpoint that does
not exist in this project yet (`adapters/trm.py`), and
`RUN_COMPLEMENTARY_SOLVER` has no second solver at all. `runner.py` refuses to
execute any action outside this set rather than silently no-op'ing, so a
config mistake fails loudly instead of pretending to spend compute it cannot
spend.
"""

from __future__ import annotations

from src.harness.schemas import AllocationAction

EXECUTABLE_ACTIONS: frozenset[AllocationAction] = frozenset({AllocationAction.STOP})


class ActionNotExecutable(RuntimeError):
    """Raised when something asks the harness to execute an action with no
    implementation yet, rather than treating it as a silent no-op."""


def require_executable(action: AllocationAction) -> None:
    if action not in EXECUTABLE_ACTIONS:
        raise ActionNotExecutable(
            f"{action} is defined in the harness interface but has no executor in "
            "this codebase yet (see actions.py module docstring for what's missing)."
        )
