"""Harness configuration: one dataclass per component, loaded from YAML.

Every component is a config flag, not a code branch someone has to remember to
flip (`configs/harness_v1.yaml` is the checked-in default). `frozen_baseline`
is the one flag that must reproduce RUN-001's own selection exactly when set —
`verifier/original.py` is what that mode delegates to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class VerifierConfig:
    name: str = "B0_original_nvarc"
    """One of the names registered in `verifier/__init__.py`."""
    top_k: int = 2
    params: dict = field(default_factory=dict)


@dataclass
class AllocatorConfig:
    enabled: bool = False
    """Phase-1 default is off: EXP002 only exercises the verifier."""
    stopping_confidence_threshold: float = 0.8
    stopping_margin_threshold: float = 0.15
    max_actions_per_task: int = 0
    allowed_actions: tuple[str, ...] = ()
    """Empty means "the allocator may propose nothing" — Gate 1 default."""


@dataclass
class HarnessConfig:
    frozen_baseline: bool = True
    """When true, the runner must reproduce RUN-001's own submission exactly
    (§"Maintain a frozen baseline mode that exactly reproduces RUN-001
    selection")."""
    verifier: VerifierConfig = field(default_factory=VerifierConfig)
    allocator: AllocatorConfig = field(default_factory=AllocatorConfig)
    candidate_archive_dir: str = "artifacts/run001/run001"
    split: str = "evaluation"
    top_k_submission: int = 2

    @classmethod
    def from_yaml(cls, path: str | Path) -> "HarnessConfig":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        verifier_raw = raw.pop("verifier", {}) or {}
        allocator_raw = raw.pop("allocator", {}) or {}
        if "allowed_actions" in allocator_raw:
            allocator_raw["allowed_actions"] = tuple(allocator_raw["allowed_actions"])
        return cls(
            verifier=VerifierConfig(**verifier_raw),
            allocator=AllocatorConfig(**allocator_raw),
            **raw,
        )
