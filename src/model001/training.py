from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .dataset import DatasetExample


@dataclass(frozen=True)
class LoRAConfig:
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    qlora: bool = False


@dataclass(frozen=True)
class TrainingConfig:
    seed: int
    batch_size: int
    max_steps: int
    learning_rate: float
    curriculum: str
    target_mode: str
    lora: LoRAConfig

    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def balanced_batches(examples: list[DatasetExample], batch_size: int) -> list[list[DatasetExample]]:
    by_family: dict[str, list[DatasetExample]] = {}
    for example in examples:
        by_family.setdefault(example.family, []).append(example)
    families = sorted(by_family)
    batches = []
    cursor = {family: 0 for family in families}
    while True:
        batch = []
        advanced = False
        for family in families:
            group = by_family[family]
            if cursor[family] < len(group) and len(batch) < batch_size:
                batch.append(group[cursor[family]])
                cursor[family] += 1
                advanced = True
        if batch:
            batches.append(batch)
        if not advanced:
            break
    return batches


def write_checkpoint_stub(path: Path, config: TrainingConfig, step: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"step": step, "config_hash": config.config_hash()}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

