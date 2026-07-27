# GEN001-A — DEPENDENCY_MANIFEST

Every external dependency the restored NVARC-lineage branch (`NVARC_LINEAGE_AUDIT.md`)
requires to run, in one place. Nothing here is fetched or installed by this
phase — this is an inventory, not an installation script.

## Kaggle-hosted assets (not present locally)

| Asset | Kaggle reference | Role | Fetched? |
| --- | --- | --- | --- |
| Fine-tuned checkpoint | `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1` | model weights | No — file listing only, via authenticated API |
| Offline-wheel notebook | `sorokin/pip-install-unsloth-flash-patch` | installs `unsloth`, `unsloth_zoo`, pinned `numpy`/`matplotlib`/`scikit-learn`, prebuilt `flash_attn` wheel, and a binary patch to `unsloth/models/qwen3.py` | Contents read via API, not vendored |
| Competition data | `arc-prize-2026-arc-agi-2` | task files | Already local, `competition_2026/extracted/` |
| Docker image | `gcr.io/kaggle-private-byod/python@sha256:320043e14c68293f1c946585b9257123385205a58af4b94b17d31868cae4e868` | pinned runtime | Not locally reproducible; required for byte-identical behaviour |

## Python package versions (measured inside the pinned image, `paper/REPRODUCIBILITY.md`)

Python 3.11.13, torch 2.8.0+cu128, xformers 0.0.32.post2, bitsandbytes
0.48.2, unsloth 2025.9.7, plus the offline-wheel notebook's pins
(`numpy==2.2.6`, `matplotlib==3.10.6`, `scikit-learn==1.7.2`) and
`flash_attn-2.8.2+cu128torch2.8-cp311-cp311-linux_x86_64.whl` (installed
then bypassed on T4 in favour of an xformers monkeypatch,
`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §6).

## Local repository dependencies GEN001-A's own code adds

None beyond what `src/run001/archive.py` already depends on (the standard
library only: `gzip`, `hashlib`, `json`, `os`, `time`, `zlib`). GEN001-A's
adapter (Phase 6) is deliberately built to require **zero new third-party
packages for its CPU-only paths** — the mocked-generator validation path
(`experiments/GEN001A/LOCAL_VALIDATION.md`) runs with only what is already
in this repository's test environment.

## Vendoring status

Unlike CompressARC (`third_party/compressarc/`, vendored verbatim per
`paper/REPRODUCIBILITY.md`), no NVARC-lineage code is vendored into this
repository. `references/score_winners/01_nvarc/` is a local reference
checkout used for static analysis only (as `docs/NVARC_2026_T4_BASELINE_AUDIT.md`
and `docs/NVARC_LINEAGE.md` already do), not imported by any `src/` module.
`src/gen001/nvarc_adapter.py` writes its own Kaggle-embeddable module,
following the same `%%writefile`-verbatim pattern `src/run001/build_notebook.py`
and `src/run002c/build_pilot_notebook.py` already use, so the code that
would run on Kaggle stays reproducible from this repository — but it is a
new adapter module, not a copy of NVARC's own code, since NVARC's own
`arc_loader.py`/`arc_decoder.py`/`arc_solver.py` are Apache-2.0-derived work
whose notice is stripped in the reference notebook (`LICENSE_AUDIT.md`),
and this phase does not resolve that hygiene issue by copying more of it.
