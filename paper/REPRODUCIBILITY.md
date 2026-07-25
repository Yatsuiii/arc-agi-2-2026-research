# REPRODUCIBILITY

What a third party needs to reproduce this work, and what we currently cannot
give them.

## Pinned state

| Item | Value |
| --- | --- |
| This repository | see the SHA recorded in each `experiments/*/RESULT.md` |
| Competition data | `competition_2026/arc-prize-2026-arc-agi-2.zip`, extracted to `competition_2026/extracted/` |
| Benchmark repo | `arcprize/ARC-AGI-2` @ `f3283f727488ad98fe575ea6a5ac981e4a188e49` |
| Reference SHAs | `docs/PROJECT_STATE.md` §6 |
| Paper SHA256s | `metadata/PAPER_SHA256SUMS.txt` |

## Determinism policy

Three sources of non-determinism, handled explicitly rather than hoped away:

1. **Batched decoder non-determinism.** NVARC25 §3.3 documents that batched DFS
   is non-deterministic because decisions depend on logit values that shift with
   batch composition. They tested a batch-invariant implementation, confirmed it
   improved local precision, and rejected it for being 17% slower. **We
   therefore report candidate-set-dependent results over repeated runs, not from
   a single run**, or we fix batch composition and say so.
2. **Seeds.** Every seed used is recorded in `RESULT.md` field 4. The 2026
   notebook uses `seed=1` for TTT augmentation, `seed=2` for eval augmentation,
   `seed=42` for LoRA init and the trainer, and `hash(bk) % 1024**2` for
   rescoring augmentation. That last one depends on Python's string hash and is
   **not reproducible across processes unless `PYTHONHASHSEED` is fixed** —
   recorded here because it is exactly the kind of thing that silently breaks a
   replication.
3. **Kaggle environment.** The docker image digest is part of the record:
   `gcr.io/kaggle-private-byod/python@sha256:320043e14c68293f1c946585b9257123385205a58af4b94b17d31868cae4e868`.

## What we can reproduce today

- All dataset statistics and duplicate analysis: `python -m src.data_audit`, CPU
  only, deterministic, no external downloads, ~4 s.
- EXP001 Stage A headroom analysis: `python -m src.analysis.headroom`, CPU only,
  ~20 s, reproduces CompressARC's published accuracies exactly.
- Every claim in `docs/PROJECT_STATE.md` and `docs/REFERENCE_LICENSE_AUDIT.md`
  from the files on disk, plus the Kaggle metadata claims via the authenticated
  CLI at `~/arc-agi-2-2026/.tools/kaggle-venv/bin/kaggle`.
- The RUN-001 instrumented notebook, regenerable from the frozen reference with
  `python -m src.run001.build_notebook` and checkable with
  `python -m src.run001.validate_notebook`. The build asserts each patch anchor
  matches exactly once, so the notebook cannot drift silently.
- EXP002's full verifier evaluation: `python -m src.analysis.exp002_verifier_eval`
  (2 s) then `python -m src.analysis.exp002_figures` (~1 s), CPU only, reading
  only `artifacts/run001/run001/` and `competition_2026/extracted/`. Fold
  assignment is seeded (`FOLD_SEED = 20260725`) and deterministic; rerunning
  reproduces `artifacts/EXP002/exp002_report.json` byte-for-byte.
- The harness itself: `python -m pytest tests/harness/` (114 tests across
  schemas, features, verifiers, allocator interfaces, and an integration test
  against the real RUN-001 archive proving frozen-baseline mode reproduces
  its submission exactly). `python -m pytest` at the repo root runs the full
  184-test suite, harness included.

## RUN-001 environment, measured

Pinning the reference docker image is required, not cosmetic: under the default
image the run fails at `import torch` because the dependency kernel's cp311
wheels shadow the system torch under a cp312 interpreter. Setting
`machine_shape: NvidiaTeslaT4` is likewise required, or Kaggle allocates a single
P100 (sm60) instead of 2x T4 (sm75). Measured inside the pinned image: Python
3.11.13, torch 2.8.0+cu128, xformers 0.0.32.post2, bitsandbytes 0.48.2, unsloth
2025.9.7, 19.5 GB writable. Full evidence in
`experiments/RUN001/ACCESS_REPORT.md`.

## What we cannot reproduce, and why

| Blocker | Detail | Severity |
| --- | --- | --- |
| ~~Kaggle credentials absent~~ | **RESOLVED / never true.** OAuth credential at `~/.kaggle/credentials.json`, CLI 2.2.4 authenticated, verified 2026-07-25. `metadata/KAGGLE_DOWNLOAD_PENDING.txt` is stale — it tested for the legacy `kaggle.json`. | not a blocker |
| NVARC synthetic data not lawfully reusable | All three `sorokin/nvarc-*` Kaggle datasets carry licence `unknown`. Downloadable but not reusable. | **BLOCKING for reproducing the score driver** |
| Checkpoint and notebook licences unresolved | Kaggle exposes no licence field for model instances or kernels via the API; both need a web page | **BLOCKING for publication**, not for a private run |
| Persona verification status unknown | May gate prize eligibility and submission; does not gate API access | **BLOCKING for submission** if unverified |
| NVARC submodules not fetched | 7 repositories (BARC, re-arc, h-arc, MINI-ARC, ConceptARC, TRM@e7b6871, ARC-AGI-2) | Blocks NVARC SDG reproduction; fetchable at will |
| NVARC pretraining compute | 4 nodes x 8xH100 for 27 hours for the 4B model (`nvarc_2025.pdf` §3.1) | Permanently out of reach |
| TRM pretraining compute | 24 hours on 8xH100 (`nvarc_2025.pdf` §4.1); original TRM 3 days on 4xH100 | Out of reach; must use released checkpoints |
| ARChitects LLaDA pretraining | 175,000 steps, 39 hours on 8xH100 (`page.md`) | Out of reach |
| MindsAI, Lonnie artifacts | absent entirely | Comparison is incomplete and says so |
| ARC Prize 2026 rules text | not present locally | Blocks final licence conclusions on data reuse and prize eligibility |

## Third-party reproduction instructions

`[BLOCKED until a solver exists.]` The section will contain: exact environment,
exact commands, exact expected runtime and expected numbers with tolerances
reflecting the determinism policy above.

## Licence of this work

`[OPEN]` Not yet chosen. ARC Prize prize-eligibility has historically required
open sourcing under a permissive licence; the choice must be made before any
submission, not after.
