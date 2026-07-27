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
- The harness itself: `python -m pytest tests/harness/` (150 tests across
  schemas, features, verifiers (B0-B7 and V0-V3), allocator interfaces, and
  an integration test against the real RUN-001 archive proving frozen-
  baseline mode reproduces its submission exactly). `python -m pytest` at the
  repo root runs the full 228-test suite, harness included.
- EXP002-B's full mechanism test: `python -m src.analysis.exp002b_verifier_eval`
  (~2.3 s) then `python -m src.analysis.exp002b_figures` (~1 s), CPU only,
  same inputs as EXP002. `singleton_prior` is measured fresh from Fold A each
  run (deterministic given the fixed fold seed), so re-running reproduces
  `artifacts/EXP002B/exp002b_report.json` byte-for-byte.
- EXP002-C/EXP002-C2/EXP002-C3's Kaggle notebooks are regenerated, never
  hand-edited, from committed source: `python -m src.run002c.build_pilot_notebook`,
  `python -m src.run002c.build_c3c4_notebook`,
  `python -m src.run002c.build_host_probe_notebook`, and
  `python -m src.run002c.build_b1b2_notebook` embed
  `third_party/compressarc/` and `src/run002c/solve_task_cli.py` verbatim
  via `%%writefile` cells, so the code that ran on Kaggle is reproducible
  from this repository byte-for-byte — including EXP002-C3's B1/B2, whose
  orchestration changes (thread caps, affinity, vCPU-derived concurrency)
  live entirely in the generator script, never in `solve_task_cli.py` or
  any vendored module (both remain byte-identical across all three
  experiments). The runs themselves are not CPU-reproducible (real Kaggle
  2xT4 GPU time, `paper/COMPUTE_LEDGER.md`); their raw outputs are archived
  under `artifacts/EXP002C/`, `artifacts/EXP002C2/`, and `artifacts/EXP002C3/`
  (including the v1 failed/false-aborted kernel outputs from EXP002-C2,
  preserved rather than discarded, per `experiments/EXP002C/PILOT_RESULTS.md`
  §0 and `experiments/EXP002C2/ERROR_ANALYSIS.md` §1). EXP002-C3's own
  host-topology probe output (`artifacts/EXP002C3/host_probe_output/`) is
  metadata-only and trivially re-runnable but not expected to reproduce
  identical values across different Kaggle session allocations.

- ACQ-001's clean-corpus reconciliation and EXP002-D's full verifier
  evaluation are both CPU-only and reproducible from committed source and
  the immutable ACQ-001 archives: `python -m src.analysis.exp002d.corpus`,
  `.folds`, `.features`, `.run_eval`, `.stats`, `.calibration`,
  `.ablation`, `.error_taxonomy`, in that order, ~3.2 minutes total
  (`experiments/EXP002D/RESOURCE_ANALYSIS.md`). Every fold seed
  (`20260727`) and negative-sampling seed is fixed; rerunning reproduces
  `artifacts/EXP002D/metrics.json` and every other artifact byte-for-byte,
  except `HistGradientBoostingClassifier`'s own internal parallelism,
  which is deterministic given `random_state` but not guaranteed
  bit-identical across different BLAS/thread-count environments (a
  scikit-learn-level caveat, not one this project's own code introduces).

- GEN001-A's pilot preflight is fully CPU-only and reproducible from
  committed source: `python -m src.gen001.build_pilot_manifest`,
  `python -m src.gen001.build_pilot_notebook`,
  `python -m src.gen001.validate_pilot_notebook`, and
  `python -m src.gen001.pilot_runner` (the last runs a mock, schema-valid
  dry run with `checkpoint_id="MOCK"`, never a real NVARC result). Together
  with `tests/gen001/` (22 tests), these reproduce
  `artifacts/GEN001A/pilot_manifest.json`,
  `kaggle/gen001_nvarc_pilot/gen001a_pilot.ipynb`, and
  `artifacts/GEN001A/mock_pilot_output/` byte-for-byte. No GEN001-A pilot
  has actually been launched on Kaggle; there is no real-run output to
  reproduce yet.
- GEN002-B is fully CPU-only and reproducible from committed source:
  `python -m src.gen002b.build_validation_manifest`, the benchmark and
  validation runner entrypoints in `src.gen002b.runner`, and
  `python -m src.gen002b.offline_analysis`. The frozen benchmark task IDs,
  fallback budgets, and fresh validation manifest are persisted in
  `artifacts/GEN002B/frozen_config.json` and
  `artifacts/GEN002B/validation_manifest.json`. The run is deterministic
  because every stage is pure and there is no stochastic search or learned
  ranking. Expected outputs are the files listed in
  `experiments/GEN002B/ARTIFACT_MANIFEST.tsv`.

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

<!-- DATA001A:BEGIN -->
## DATA001-A reproducibility notes

- Generator version: `data001a.v1`
- Dataset manifest: `artifacts/DATA001A/dataset_manifest.json`
- Coverage manifest: `artifacts/DATA001A/coverage_metrics.json`
- Frozen local-training config hash: `7408a15bfbb7bc7ab7a2235062ec4761d5d2b382a9992103f5675cda31206db9`
- All accepted tasks carry deterministic seeds, canonical hashes, and typed program IDs.
<!-- DATA001A:END -->

<!-- DATA001B:BEGIN -->
## DATA001-B reproducibility notes

- Generator version: `data001b.v1`
- Pool manifest: `artifacts/DATA001B/pool/pool_manifest.json`
- Dataset manifest: `artifacts/DATA001B/dataset_manifest.json`
- Family manifest: `artifacts/DATA001B/family_manifest.json`
- Coverage analysis: `experiments/DATA001B/COVERAGE_ANALYSIS.md`
- Frozen selection objective: `frozen_greedy_quota_diversity_token_penalty_v1`
- All selected tasks carry deterministic seeds, canonical hashes, typed family IDs, token-cost metadata, and structured traces.
<!-- DATA001B:END -->
