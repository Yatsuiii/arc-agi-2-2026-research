from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Operation:
    kind: str
    params: dict


@dataclass(frozen=True)
class Program:
    program_id: str
    family: str
    tier: int
    operations: list[Operation]
    parameter_bindings: dict
    labels: list[str] = field(default_factory=list)
    version: str = "data001a.v1"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["operations"] = [asdict(op) for op in self.operations]
        return payload

