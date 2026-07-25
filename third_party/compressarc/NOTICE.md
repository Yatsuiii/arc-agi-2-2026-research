Vendored from `references/paper_winners/03_compressarc` (outside this repo, at
`/home/Yatsuiii/arc-agi-2-2026/references/paper_winners/03_compressarc`)
@ commit `83a22218024d46273eb32b769a906340202ffb4d`, MIT licence,
Copyright (c) 2025 Isaac Liao. `LICENSE` in this directory is the original,
unmodified.

Per `docs/REFERENCE_LICENSE_AUDIT.md` §3 ("TRM, SOAR and CompressARC code may
be vendored under MIT with the notice retained, into a clearly marked
`third_party/` tree"), this is that tree.

## Files vendored

`arc_compressor.py`, `initializers.py`, `layers.py`, `multitensor_systems.py`,
`preprocessing.py`, `scoring.py`, `solution_selection.py`, `train.py`,
`visualization.py`. Not vendored: `solve_task.py`, `parallel_train.py`,
`analyze_example.py`, `plot_accuracy.py`, `plot_problems.py`,
`list_solved_puzzles.py`, `dataset/`, `results_for_the_blog_post/` — this
project's own driver (`src/run002c/solve_task_cli.py`) replaces
`solve_task.py`/`parallel_train.py` rather than vendoring them unmodified,
because it needs to read ARC-AGI-2 task files (not the vendored ARC-AGI-1
`dataset/`) and write to this project's archive format.

## Modification: `solution_selection.py`

One change from upstream, for `EXP002-C`
(`experiments/EXP002C/PLAN.md`): `Logger` now keeps `self.solution_grids`, a
`hash -> grid` map populated the same moment a hash is scored, so a candidate's
actual grid is recoverable after training instead of only its hash. Upstream's
own recorded traces (`results_for_the_blog_post/predictions_*.npz`, the source
`src/analysis/headroom.py` reads) never had this and cannot compute structural
features from it — `experiments/EXP002B/CORPUS_REQUIREMENTS.md` option A names
this exact limitation. No other behaviour changed: training, scoring and the
top-two selection logic are untouched, so the module still reproduces
upstream's published accuracy under `python -m src.analysis.headroom`'s H0
check.
