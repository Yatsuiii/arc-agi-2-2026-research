# GEN001-A — NVARC_LINEAGE_AUDIT

Identifies exactly which branch produced RUN-001, restated from
`docs/NVARC_LINEAGE.md`, `docs/NVARC_2026_T4_BASELINE_AUDIT.md`, and
`experiments/RUN001/INSTRUMENTATION_DIFF.md` — all pre-existing, already-cited
artifacts, not re-derived here except where GEN001-A adds a new fact. Per the
acceptance message's instruction, this branch is called only what the
evidence supports: **a public NVARC-lineage branch**, never "the 2026 topper
system" — no evidence anywhere in this workspace establishes that the
Kaggle-published T4x2 notebook is the exact configuration that scored on the
2026 competition leaderboard, only that it is a faithful architectural port
of NVARC's branch 1 (`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §1, §16, §20).

## Which branch produced RUN-001

`kaggle/run001_nvarc_frozen/reference_source.ipynb`
(sha256 `452dbb1f...322a6c`), sourced from Kaggle notebook
`nihilisticneuralnet/baseline-nvarc-arc-25-winning-solution-for-t4x2`
(id_no 113828488) — **branch 1 of NVARC only** (the Qwen3-4B + TTT + DFS +
augmented-rescoring path). The TRM branch and branch ensembling are absent
by construction (`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §1), which the audit
already assessed as the right engineering choice given NVARC's own reported
zero marginal contribution from ensembling at the 4B scale (`nvarc_2025.pdf`
§4.4, restated in `docs/NVARC_LINEAGE.md`).

## Upstream repository and commit SHA

No single upstream git commit SHA is checkable for the Kaggle notebook
itself — Kaggle notebooks are not git-versioned artifacts, and this
workspace only has the exported `.ipynb`, pinned by its own sha256 above.
What is git-traceable is the **training script** that produced the
checkpoint the notebook loads:
`references/score_winners/01_nvarc/ARChitects/run_sft_4b.sh` (local
checkout under `references/score_winners/01_nvarc/`, no upstream remote
recorded in this workspace — `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §3-5
traces the training config from this file, not from a resolvable commit).

## Inherited ARChitects components

Per `docs/NVARC_LINEAGE.md`'s component-provenance table, components 1
(`ArcDataset`/augmentation grammar), 2 (batched DFS), 3 (augmentation
rescoring), 5 (per-task LoRA TTT), and 7 (Qwen3-4B base) trace to
ARChitects 2024/2025 (Apache-2.0). Component 1's Apache-2.0 notice is
**stripped** in the 2026 T4x2 notebook (`docs/NVARC_2026_T4_BASELINE_AUDIT.md`
verdict item 2) — a licence-hygiene issue this audit does not resolve, only
restates as a standing caveat for `LICENSE_AUDIT.md` below.

## NVARC-original components

Component 4 (`score_kgmon`/`score_agg` selection rule), component 6 (the
16-token cut tokenizer), and the SDG pipeline (component 8, not present in
the T4x2 notebook's own code since its output is baked into the checkpoint)
are NVARC-original per the same table.

## Model architecture, checkpoint identity, tokenizer, quantization

| Field | Value |
| --- | --- |
| Base architecture | Qwen3-4B-Thinking-2507, vocabulary cut to 16 tokens |
| Parameter count | 3.63B (bf16 shards total 7,267,233,496 bytes) |
| Checkpoint | Kaggle model `sorokin/qwen3_4b_grids15_sft139/Transformers/bfloat16/1`, version timestamp 2025-11-02 |
| Tokenizer | `tokenizer.json` (1,731 bytes), `vocab.json` (94 bytes, confirming a 16-entry vocabulary) |
| Quantization at inference | 4-bit NF4 (`load_in_4bit=True`), fp16 compute (`dtype=float16`) |
| Attention backend | `attn_implementation="eager"`, monkeypatched to xformers `memory_efficient_attention` (T4 is sm75, no FlashAttention-2 support) |

Source: `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §3-9.

## Test-time adaptation

Per-task LoRA: r=256, alpha=32, dropout 0, rslora, seed 42, targets
`q,k,v,o,gate,up,down,embed_tokens,lm_head`, `lr=5e-5` cosine,
`adamw_8bit`, 1 epoch, batch 1, gradient checkpointing off. Training
augmentation `augment(n=16, seed=1)` → 8 orientations x 16 colour
permutations = 128 samples, one epoch, batch 1 → ~128 optimizer steps per
task. Source: `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §12.

## Augmentation pipeline (candidate generation)

Per test input: `augment(n=2, seed=2)` → 16 views, grouped into 8 batches of
4. Each batch runs `turbo_dfs` with cutoff `max_score = -log(0.2)`
(cumulative NLL < 1.609 nats). Candidate count is data-dependent, unbounded.
Each unique candidate is rescored under 8 fixed augmentations
(`seed=hash(bk) % 1024**2` — **not reproducible across processes unless
`PYTHONHASHSEED` is fixed**, `paper/REPRODUCIBILITY.md`). Source:
`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §13.

## Candidate-generation and selection stages

`turbo_dfs` (candidate generation, per-batch 540s guard) →
`calc_scores`/augmented rescoring → `ArcDecoder.run_selection_algo()`
defaulting to `score_kgmon` (vote count minus mean augmented NLL) → top-2
become `attempt_1`/`attempt_2`. `score_full_probmul_3` (ARChitects
product-of-experts) is present in the notebook but unused by default.
Source: `docs/NVARC_2026_T4_BASELINE_AUDIT.md` §14.

## GPU requirements

2x NVIDIA T4 (sm75, `machine_shape: NvidiaTeslaT4` required — otherwise
Kaggle allocates a single P100). Estimated 8-14 GB VRAM per GPU, activations
the dominant and least predictable term (`docs/NVARC_2026_T4_BASELINE_AUDIT.md`
§9). Docker image
`gcr.io/kaggle-private-byod/python@sha256:320043e14c68293f1c946585b9257123385205a58af4b94b17d31868cae4e868`.

## External datasets in the training mixture

`SDG/scripts/build_datasets.py` (`references/score_winners/01_nvarc/SDG/`):
`arc2_evaluation6` (all 120 ARC-AGI-2 public evaluation tasks, 6 aug, with
test-pair ground truth), `rearc` (RE-ARC, 400 puzzles x 256 aug),
`arc2_training` (all ARC-AGI-2 training tasks, 256 aug, **also including
test-pair ground truth** — see `CONTAMINATION_AUDIT.md`, this is the fact
that phase 3 turns into a corpus-specific finding), plus ConceptARC and
MINI-ARC subsets per `docs/NVARC_LINEAGE.md`'s provenance table.

## Model and code licences

Base model Apache-2.0 (Qwen3-4B-Thinking-2507). Fine-tuned checkpoint
licence **unresolved** — Kaggle exposes no licence field for model
instances via the API (`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §18,
`paper/REPRODUCIBILITY.md`). TRM upstream MIT; ARChitects upstream
Apache-2.0 with its notice stripped in the derived `arc_loader.py`.
Full detail in `LICENSE_AUDIT.md`.

## Missing files / Kaggle-specific dependencies

- Kaggle model `sorokin/qwen3_4b_grids15_sft139` — not fetched to this
  workspace; only its file listing was retrieved via the authenticated API
  (`docs/NVARC_2026_T4_BASELINE_AUDIT.md` §3-5).
- Kaggle notebook `sorokin/pip-install-unsloth-flash-patch` — offline-wheel
  dependency notebook, contents audited (`docs/NVARC_2026_T4_BASELINE_AUDIT.md`
  §6) but not vendored into this repository.
- A prebuilt `flash_attn` wheel (`github.com/mjun0812/flash-attention-prebuild-wheels`,
  requires sm80+, installed then bypassed on T4 in favour of the
  xformers monkeypatch).
- 7 NVARC submodules (BARC, re-arc, h-arc, MINI-ARC, ConceptARC, TRM,
  ARC-AGI-2) not fetched (`paper/REPRODUCIBILITY.md`).

## Modifications made during RUN-001 restoration

Exactly two sanctioned changes plus one unsanctioned-but-necessary fix,
mechanically enforced by `src/run001/build_notebook.py`'s anchor-based
patching (a mismatch aborts the build):

1. **Sanctioned — remove the 4-task debug filter** in `starter.py` (3 lines
   removed). The filter was already bypassed in rerun mode; this changes
   only interactive-mode behaviour, which is the mode RUN-001 used.
2. **Sanctioned — behaviour-neutral candidate archiving.** Five additive
   insertion points writing `CandidateArchive` records; no existing
   statement modified, reordered, or wrapped except inside a
   `try/except: pass` around the one instrumentation call site inside the
   solver loop. 366 lines added, 4 lines removed total (1 for the model
   path below, 3 for the debug filter).
3. **Not sanctioned, but necessary — the model mount path.** The reference
   notebook's hardcoded path does not exist on current Kaggle infrastructure
   (confirmed by probe kernel `run001-asset-probe` v3); replaced with a
   resolver that tries the reference path first, falling back to the
   drifted mount layout. Selects the same checkpoint either way; no solver
   property changes.

Full line-by-line accounting: `experiments/RUN001/INSTRUMENTATION_DIFF.md`.

## What GEN001-A restores, and what it does not

GEN001-A restores **nothing new** in this phase — no checkpoint is
downloaded, no notebook is re-derived. `src/gen001/nvarc_adapter.py`
(Phase 6) is written against this exact, already-audited configuration, so
that if a future GPU pilot runs, it runs the same branch RUN-001 already
validated end-to-end (`experiments/RUN001/RESULTS.md`), not a new or
differently-configured restoration.
