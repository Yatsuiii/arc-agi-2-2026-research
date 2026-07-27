from __future__ import annotations

from dataclasses import dataclass, field

from src.gen002b.core import ArcTask, SynthProgram, grid_sha1


@dataclass
class SemanticCache:
    task: ArcTask
    seen_signatures: set[tuple] = field(default_factory=set)

    def signature(self, program: SynthProgram) -> tuple:
        outputs = []
        for pair in self.task.train_pairs:
            try:
                outputs.append(grid_sha1(program.apply(pair.input_grid)))
            except Exception:  # noqa: BLE001
                outputs.append("ERR")
        return tuple(outputs)

    def keep(self, program: SynthProgram) -> bool:
        signature = self.signature(program)
        if signature in self.seen_signatures:
            return False
        self.seen_signatures.add(signature)
        return True
