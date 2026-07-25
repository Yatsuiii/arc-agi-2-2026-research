# EXP002-B Part 4 — clean-corpus acquisition recommendation

**Not launched. This is a plan, pre-registered before acquisition, per the
brief's "Do not launch a long GPU run without approval."**

## Why RUN-001's corpus cannot carry a decisive result

- **Contaminated.** `sorokin/qwen3_4b_grids15_sft139` was fine-tuned on
  synthetic data generated from the 120-task evaluation split's own puzzle
  descriptions (`docs/DATASET_AUDIT.md` §6.1, quoting `nvarc_2025.pdf` §2.1
  and §3.5 directly). Every accuracy number from it is a competition-
  engineering number, never clean evidence.
- **Partial.** RUN-001 is `TIMED_OUT` at 72/120 tasks
  (`experiments/RUN001/RESULTS.md`).
- **Underpowered.** Fold C, the untouched evaluation fold, has 18
  test-indices — `experiments/EXP002/RESULTS.md` already flags this as too
  small to resolve the recovered-headroom numbers it reports.
- **Narrow.** 94 test-indices in total means every downstream breakdown
  (task family, candidate-set size, margin bucket) is sparse by construction.

## Evaluating the four routes

### A. Existing clean CompressARC / ARC-AGI-1 traces (mechanism validation only)

**Already in use** — EXP001-A's H0 (`experiments/EXP001/RESULT.md` §7) and
EXP002's own H0 (`experiments/EXP002/RESULTS.md` §7) both lean on this. Zero
additional compute, MIT licensed, zero pretraining so zero contamination risk
by construction (`experiments/EXP001/PLAN.md` §6). **Hard ceiling: no candidate
grids in the archive**, only a hash and a score per candidate
(`src/analysis/headroom.py` module docstring), so `structural.py`'s features
— which is to say, everything V2 depends on — cannot be computed against it.
Also ARC-AGI-1, not ARC-AGI-2, and a structurally different solver (per-task
gradient descent, not an LLM decoder), so its candidate *distribution* is not
representative of what NVARC produces. **Verdict: keep using it for pipeline
mechanism checks (as already done); it cannot be the corpus EXP002-B's V0-V3
comparison runs on.**

### B. TRM on family-separated ARC-AGI-2 training folds

Would need: a TRM checkpoint (none exists in this project — `docs/CANDIDATE_RESEARCH_THESES.md`
lists it as a future diagnostic baseline, `RUN-002 (later, contingent): TRM
diagnostic`, `docs/BASELINE_SELECTION.md`), a licence read (not yet done, same
gap RUN-001 had for its own model before `ACCESS_REPORT.md`), and its own
Kaggle GPU run — `docs/CANDIDATE_RESEARCH_THESES.md`'s own compute row: "NVARC
TRM test-time fine-tuning: Kaggle 4xL4, ~2h for 240 tasks." The harness's own
`adapters/trm.py` is an explicit `NotImplementedError` stub for exactly this
reason. **Verdict: real candidate diversity (a second, architecturally
different solver, which is what thesis T1's routing question eventually
needs) but not the cheapest route to *this* experiment's need (more clean V0-V3
comparison data), and this session is explicitly barred from "begin TRM
routing" and "launch another 12-hour GPU run."**

### C. NVARC inference on ARC-AGI-2 training folds, as run

**Does not solve contamination.** `nvarc_2025.pdf` Table 1 states the
synthetic-data mix draws "both training and evaluation puzzles from
ARC-AGI-2" — the same puzzle-summarization-then-synthesis pipeline
`docs/DATASET_AUDIT.md` §6.1 documents for the evaluation split was, on the
project's current evidence, also applied to (at least some of) the training
split. Running RUN-001's exact frozen pipeline against training tasks instead
of evaluation tasks does not purchase a clean checkpoint; it swaps one
contaminated split for a different, unaudited one, which would be **worse**
than RUN-001 for a "clean corpus" claim because RUN-001 at least states its
contamination precisely, and a training-split run's contamination extent
(which training tasks contributed synthetic descendants, and how directly) is
not currently known and cannot be verified from public API metadata (same gap
`ACCESS_REPORT.md` #4 already recorded for the model instance's licence).
**Verdict: rejected as stated. A variant survives — see recommendation.**

### D. Leakage-controlled cross-validation folds

Not itself a candidate source — a data-hygiene requirement that applies to
whichever corpus is chosen. Already partially implemented: EXP002's fold
split (`src/analysis/exp002_verifier_eval.py::assign_folds`) stratifies and
splits by *task*, so no candidate record crosses a fold boundary, but it does
not yet check for near-duplicate task structures or synthetic-descendant
provenance across folds (`docs/DATASET_AUDIT.md` §3's canonical-duplicate
check is the relevant tool and is not yet wired into the fold builder).
**Verdict: adopt regardless of which corpus is chosen (folded into the
recommendation below), not a standalone acquisition plan.**

## Recommendation: a variant of C — CompressARC, not NVARC, on ARC-AGI-2 training folds

**Run CompressARC (the same MIT-licensed, zero-pretraining solver already
used for the mechanism test) directly against ARC-AGI-2's training split**,
not ARC-AGI-1. This is not literally option A, B, or C as posed, but it is
the direct fusion of what makes each attractive and none of what disqualifies
them:

| Criterion | Assessment |
| --- | --- |
| **Cleanliness** | **Best available.** CompressARC has no pretraining phase at all — it optimises a small model per task from scratch against that task's own demonstration pairs (`experiments/EXP001/PLAN.md` §6). There is no checkpoint to have memorised anything, on either the training or evaluation split, so this is immune to the exact contamination mechanism that disqualifies option C's literal reading. |
| **Candidate diversity** | Different from NVARC's LLM-decoder distribution (a real limitation, shared with option A), but produces genuinely independent *rankings* to compare V0-V3 logic against, and — unlike the existing ARC-AGI-1 traces — can be instrumented to persist full grids, closing option A's structural-feature gap. |
| **Compute** | `paper/COMPUTE_LEDGER.md`'s reference-system table: "CompressARC, per task, 1x RTX 4070, ~20 min." **Local GPU status is currently "not verified"** (`paper/COMPUTE_LEDGER.md` "Our available compute" table) — the first concrete precondition to check, before any of the rest of this plan, is not GPU quota (no Kaggle budget is spent here) but whether a local CUDA device exists at all. If not, CPU-only CompressARC runs are dramatically slower and the sample-size target below would need revisiting. |
| **Licence** | MIT (`docs/REFERENCE_LICENSE_AUDIT.md`), already cleared for this project's use — no new licence review needed, unlike option B's TRM checkpoint. |
| **Relevance to ARC-AGI-2** | The one real weakness: CompressARC has only ever been evaluated against ARC-AGI-1 in this project's records. Running it against ARC-AGI-2 tasks is itself a small, worthwhile side-validation (does its architecture even solve any ARC-AGI-2 training tasks at a nonzero rate?) before leaning on it for EXP002-B. |
| **Reproducibility** | CPU-comparable determinism story to the existing mechanism test (`paper/REPRODUCIBILITY.md`'s determinism policy already covers CompressARC's own reproducibility properties via EXP001-A). |

**This is a recommendation, not an authorization to run it.** It requires:
(1) confirming local GPU availability, (2) instrumenting CompressARC's
reference implementation to persist full candidate grids (it currently
persists only hash+score, per option A's own limitation above — this is code
work, not GPU work, and can happen before any run), and (3) the sample-size
target below, pre-registered before a single task is run.

## Minimum sample size, with justification

**Target: at least 500 test-indices total, split 60/20/20 by the existing
fold protocol, giving Fold C >= 100 test-indices** (versus RUN-001's 18).
Not an arbitrary round number — derived as follows.

V0 and V2 are compared on the *same* test-indices (a paired design), so the
right power calculation is McNemar's test on discordant pairs (cases where
exactly one of V0/V2 gets the top-2 hit right), not an independent
two-proportion test. From RUN-001's own error analysis
(`experiments/EXP002/ERROR_ANALYSIS.md`, branch S = 7.4% of all test-indices
generated-but-not-selected, plus whatever fraction V2 would additionally
flip), a discordance rate in the 10-15% range between two meaningfully
different rankers is a reasonable planning estimate — consistent with the
7.4pp headroom figure itself, which is a lower bound on how often *some*
reranking of the archive's own candidates could differ from B0.

Standard guidance for McNemar's test to have reasonable power (80%) to detect
a real asymmetry at a two-sided alpha of 0.05 is roughly 25-50 discordant
pairs. At a 10-15% discordance rate, that requires **170-500 test-indices**
in the fold being tested. Setting the target at the top of that range (500
total, ~100 in Fold C after the 60/20/20 split) is deliberately conservative,
because RUN-001's own discordance rate is itself a rough estimate from a
partial, contaminated corpus and could easily be an overestimate or
underestimate on clean ARC-AGI-2 training data.

**This is an order-of-magnitude estimate for planning, not a formal power
analysis** — reported as such rather than with false precision. If
acquisition produces materially fewer test-indices than this (CompressARC
may simply fail to produce a diverse candidate set on many ARC-AGI-2 training
tasks, which would itself be a finding), `experiments/EXP002B/RESULTS.md`'s
own successor must say so explicitly, the same way this file states RUN-001's
18-example Fold C was too small rather than quietly reporting a number anyway.

## What this session did instead

Per the brief's explicit scope ("do not generate new GPU candidates during
the initial implementation and mechanism tests" / "do not launch a long GPU
run without approval"), this plan is a recommendation only.
`experiments/EXP002B/RESULTS.md` runs the bounded mechanism test on
currently-available legal data (RUN-001's existing archive, same corpus as
EXP002, now scored through the fixed confidence semantics and the V0-V3
independence-enforced framework) and states plainly that its conclusions
remain preliminary until this acquisition plan — or an equivalent one — is
executed and approved separately.
