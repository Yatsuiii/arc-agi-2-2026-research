from __future__ import annotations

import json
import random
from dataclasses import dataclass

from .dataset import DatasetExample


@dataclass
class MockGenerationModel:
    seed: int = 0
    malformed_rate: float = 0.0

    def generate(self, example: DatasetExample, k: int = 1) -> list[str]:
        rng = random.Random(hash((self.seed, example.task_id, example.target_kind)))
        outputs = []
        for idx in range(k):
            if rng.random() < self.malformed_rate and idx == k - 1:
                outputs.append("MALFORMED")
            else:
                outputs.append(example.target_text)
        return outputs


def parse_generation(text: str):
    return json.loads(text)

