"""Adapter: TRM candidates -> harness `Candidate`/`SelectionRecord`.

**Not implemented.** No TRM checkpoint has been run in this project; RUN-001
is NVARC-only (`experiments/RUN001/RESULTS.md`). Phase-1 requires the
`AllocationAction.RUN_TRM` interface to exist so later experiments can target
it, and Phase-6 (EXP005) explicitly gates on "TRM is reproducibly available as
a secondary solver" before this adapter may be filled in. Until then this
module exists so the interface compiles and so `runner.py` has something
concrete to refuse to call.
"""

from __future__ import annotations

from pathlib import Path

from src.harness.candidate_store import CandidateStore

TRM_AVAILABLE = False


def load_into_store(artifact_dir: Path, store: CandidateStore | None = None) -> CandidateStore:
    raise NotImplementedError(
        "TRM adapter is not implemented: no TRM run exists to load. "
        "See docs/CANDIDATE_RESEARCH_THESES.md T2 and "
        "experiments/EXP002/PLAN.md's roadmap for the EXP005 gate that "
        "must pass before this adapter is built."
    )
