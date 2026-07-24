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

- All dataset statistics and duplicate analysis: `src/data_audit/`, CPU only,
  deterministic, no external downloads. `make audit` regenerates every artifact
  under `artifacts/data_audit/`.
- Every claim in `docs/PROJECT_STATE.md` and `docs/REFERENCE_LICENSE_AUDIT.md`
  from the files on disk.

## What we cannot reproduce, and why

| Blocker | Detail | Severity |
| --- | --- | --- |
| Kaggle credentials absent | `metadata/KAGGLE_DOWNLOAD_PENDING.txt` — no `~/.kaggle/kaggle.json`. Blocks every checkpoint and dataset download. | **BLOCKING for any baseline run** |
| NVARC submodules not fetched | 7 repositories (BARC, re-arc, h-arc, MINI-ARC, ConceptARC, TRM@e7b6871, ARC-AGI-2) | Blocks NVARC SDG reproduction |
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
