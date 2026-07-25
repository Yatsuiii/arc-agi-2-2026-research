# ABLATION_MATRIX

Which components get ablated, at what cost, and which ablations the prior work
owes us and never paid.

## Rule

Every component our paper claims contributes gets a row where it is removed or
neutralised, holding everything else fixed. A component we cannot ablate is a
component we cannot claim.

## Missing ablations in prior work

These are the gaps our audit found. Each is a cheap, publishable measurement
that nobody has reported, which makes them candidate contributions in their own
right.

| Gap | Owner | Why it matters |
| --- | --- | --- |
| `score_agg` (`score_kgmon`) vs the 2024 product-of-experts scorer | NVARC25 §3.4 calls the new one "better" after the deadline, with no isolated number | Both scorers ship side by side in the 2026 notebook with a comparison function. The delta is one cheap run and is unpublished. |
| Number of scoring augmentations | ARCH25 went 8→32; NVARC25 went to exactly 8 with a *shared* augmentation set. Neither reports a curve. | Directly a compute-vs-accuracy knob. |
| DFS probability cutoff | ARCH24 17%, ARCH25 7%, 2026 notebook 20% (`max_score = -log(0.2)`). No system reports accuracy as a function of cutoff. | The cutoff sets the candidate-set size, which is the input to any selection contribution. |
| TTT augmentation count and step count | 2026 notebook uses n=16, 1 epoch. ARCH25 used 128 steps. No curve anywhere. | The single largest per-task compute cost. |
| Contribution of TTT vs pretraining data | NVARC25 varies the data (Fig. 1) with TTT held on, never the reverse | We cannot currently say how much of 27.64% is TTT. |
| Per-branch solve sets | NVARC25 §4.4 says "about 2 or 3 puzzles solved by TRM were not solved by Qwen3" — a count, no task list | The entire empirical basis for routing rests on this and it is one sentence. |

## Our planned ablations

`[BLOCKED on Phase 12]` for the intervention rows. The infrastructure rows below
are already determined because they hold regardless of the thesis.

| ID | Ablation | Baseline held fixed | Metric | Est. compute | Status |
| --- | --- | --- | --- | --- | --- |
| AB-S1 | Selection algorithm: `score_kgmon` vs `score_full_probmul_3` vs vote-only vs first-beam | candidate sets identical, generated once | accuracy@2 on the eval split | **CPU only** | **DONE (offline half)** - RUN-001 `benchmark_selection_algos` gave score_kgmon 16.8 vs score_full_probmul_3 16.3 /72 (contaminated, notebook's own run); EXP002's B0/B1/B2/B5 give the equivalent comparison from stored `beam_score`/`score_aug[8]` alone (`experiments/EXP002/RESULTS.md`): B5 (reconstructed score_kgmon) ties B0 exactly, B1 (raw score) and B2 (vote-only) both underperform it |
| AB-S2 | Number of scoring augmentations m ∈ {1,2,4,8} | same candidate sets | accuracy@2 | CPU, reuses stored `score_aug` | **READY** — RUN-001 landed; not yet run |
| AB-G1 | DFS cutoff ∈ {0.07, 0.10, 0.20} | same checkpoint, same TTT | candidate-set size, oracle@k, accuracy@2 | GPU, one pass per setting | PLANNED |
| AB-G2 | TTT augmentations n ∈ {0, 4, 16} | same checkpoint | accuracy@2 | GPU | PLANNED |
| AB-X1 | Intervention removed | — | — | — | BLOCKED |
| AB-X2 | Intervention with each of its own sub-components removed | — | — | — | BLOCKED |

AB-S1 and AB-S2 are the important structural point: **once candidate sets with
per-augmentation scores are persisted, a whole family of selection ablations
becomes CPU-only and rerunnable in seconds.** That is why EXP001 is designed
around producing and storing that artifact rather than around a score.

## Anti-pattern guard

An ablation that changes two things at once is not an ablation. Rows above are
written so that exactly one knob moves. If a row cannot be written that way, the
component is entangled and the claim about it must be weakened accordingly.
