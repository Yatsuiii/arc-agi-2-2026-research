from __future__ import annotations

from dataclasses import dataclass

from src.gen002.dsl.program import evaluate
from src.gen002.grid import Grid
from src.gen002.search.best_first import search_best_first
from src.gen002.search.enumerative import search_enumerative
from src.gen002b.core import ArcTask, StageSummary, SynthProgram

FALLBACK_S0_MAX_STATES = 2000
FALLBACK_S1_MAX_STATES = 5000
FALLBACK_S0_TIMEOUT_S = 2.0
FALLBACK_S1_TIMEOUT_S = 6.0


@dataclass(frozen=True)
class LegacyAdapter:
    stage: str
    family: str
    program: object

    def to_synth(self) -> SynthProgram:
        return SynthProgram(
            stage="S2-C",
            family=self.family,
            name="legacy_gen002",
            params=(("canonical", self.program.canonical()), ("cost", self.program.cost())),
            cost=self.program.cost(),
            apply_fn=lambda grid, program=self.program: evaluate(program, grid),
        )


def run_compositional_search(task: ArcTask) -> StageSummary:
    train_inputs = tuple(pair.input_grid for pair in task.train_pairs)
    train_outputs = tuple(pair.output_grid for pair in task.train_pairs)
    summary = StageSummary(stage="S2-C")

    s0 = search_enumerative(
        train_inputs,
        train_outputs,
        max_states=FALLBACK_S0_MAX_STATES,
        timeout_s=FALLBACK_S0_TIMEOUT_S,
    )
    s1 = search_best_first(
        train_inputs,
        train_outputs,
        max_states=FALLBACK_S1_MAX_STATES,
        timeout_s=FALLBACK_S1_TIMEOUT_S,
    )
    summary.states_explored = s0.states_explored + s1.states_explored
    summary.best_n_solved = max(len(train_outputs) if s0.exact_programs else 0, s1.best_n_solved)
    summary.best_pixel_agreement = max(1.0 if s0.exact_programs else 0.0, s1.best_pixel_agreement)

    seen = set()
    for family, result in (("legacy_s0", s0), ("legacy_s1", s1)):
        for program in result.exact_programs:
            synth = LegacyAdapter(stage="S2-C", family=family, program=program).to_synth()
            if synth.canonical() in seen:
                continue
            seen.add(synth.canonical())
            summary.exact_programs.append(synth)
            summary.template_usage[family] += 1
    return summary
