from __future__ import annotations

from dataclasses import asdict, dataclass, field

Grid = list[list[int]]


@dataclass(frozen=True)
class ExamplePair:
    input: Grid
    output: Grid


@dataclass(frozen=True)
class SyntheticTask:
    task_id: str
    train: list[ExamplePair]
    test: list[ExamplePair]
    family: str
    family_bucket: str
    curriculum_tier: int
    program_id: str
    provenance: dict
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["train"] = [asdict(pair) for pair in self.train]
        payload["test"] = [asdict(pair) for pair in self.test]
        return payload

