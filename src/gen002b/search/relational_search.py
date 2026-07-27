from __future__ import annotations

from src.gen002b.core import ArcTask, StageSummary, exact_on_train, n_solved
from src.gen002b.search.cache import SemanticCache
from src.gen002b.templates import largest_object_crop_programs, single_object_translation_programs


def run_relational_search(task: ArcTask) -> StageSummary:
    summary = StageSummary(stage="S2-B")
    cache = SemanticCache(task)
    for factory in (single_object_translation_programs, largest_object_crop_programs):
        for program in factory(task):
            summary.states_explored += 1
            solved, best_pixel = n_solved(program, task.train_pairs)
            summary.best_n_solved = max(summary.best_n_solved, solved)
            summary.best_pixel_agreement = max(summary.best_pixel_agreement, best_pixel)
            if not cache.keep(program):
                continue
            if exact_on_train(program, task.train_pairs):
                summary.exact_programs.append(program)
                summary.template_usage[program.name] += 1
    return summary
