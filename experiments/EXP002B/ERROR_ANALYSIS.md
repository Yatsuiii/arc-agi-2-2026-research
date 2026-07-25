# EXP002-B — error analysis

Companion to `RESULTS.md`.

## V0 vs. V2-heuristic: how often do they actually disagree, and who wins?

Computed directly against the real RUN-001 archive (all 94 test-indices,
full corpus — not just Fold C): V0's top-1 pick and V2-independent-heuristic's
top-1 pick **differ on 58 of 94 test-indices (61.7%)**. This is the
disagreement rate `CORPUS_REQUIREMENTS.md`'s power analysis planned around
(10-15% was the planning estimate for McNemar's test; the real rate, 62%, is
far higher — the two rankers disagree much more than expected, which is
informative on its own: V2's structural-consistency score and V0's score-vote
formula are picking out genuinely different things, not minor reorderings of
the same near-tied field).

Among those 58 disagreements, on whichever candidate each ranked first:

| | Top-1 correct | Rate |
| --- | --- | --- |
| V0 | 7 / 58 | 12.1% |
| V2-heuristic | 3 / 58 | 5.2% |

**V0 wins more often specifically on the cases where the two disagree**, more
than 2:1. This is the concrete evidence behind `RESULTS.md`'s finding that
V2 does not beat V0: it isn't that V2 is merely no better on average, it's
that on the exact subset where its judgment differs from V0's, V0's judgment
is more often right. Consistent with `paper/CLAIM_LEDGER.md`'s prior
observation (EXP002) that the archive's strongest signal really is
approximated by NVARC's own selector — restricting to score-independent
evidence removes access to that signal without (yet) replacing it with
something as good.

## A concrete disagreement: task `135a2760`, test index 0

- V0 top-1: **correct**.
- V2-heuristic top-1: **wrong**.
- 6 unique candidate grids generated for this test index.

This is the single clearest disagreement in the corpus and it favours V0.
Worth a closer look before further V2 development: does V2's structural
scoring systematically misjudge tasks like this one (e.g. a task whose
demonstration pattern doesn't reduce cleanly to the six consistency checks
`IndependentHeuristicVerifier` evaluates), or is this one example noise?
**Not resolved in this pass** — one example is not evidence of a systematic
pattern, and chasing it further at n=94 risks exactly the overfitting
`experiments/EXP002/PLAN.md`'s original REDESIGN criteria warned against
("heuristic consensus works but the learned verifier overfits" — the
symmetric risk here is hand-tuning the heuristic to fix one visible example).

## Singleton candidate sets: the confidence fix in context

9 of 94 test-indices (9.6%) produced exactly one unique candidate — a
non-trivial fraction of the corpus, not a corner case. `RESULTS.md`'s
confidence-fix section already reports the headline numbers (77.8% of these
were wrong; old behaviour reported 100% confidence on all of them, new
behaviour reports 33.3%, the measured base rate). Restated in
generation-failure terms: a singleton candidate set is a strong proxy for
`paper/FAILURE_TAXONOMY.md` branch G6 (compute exhaustion) — RUN-001's
per-task time guard bound at 1200s for 41 of 77 processed tasks
(`experiments/RUN001/VALIDATION_REPORT.md`), and a task that produced only
one candidate before its guard fired is the extreme case of that. No
reranking of any kind — V0, V1, V2, or a hypothetical V4 — can fix a
generation failure; only more compute or a different solver can. This is a
generation-failure/confidence-signal distinction, not a verification one, and
the fix's value is honesty about that distinction, not accuracy gain.

## Why V2's selective-accuracy curve failed criterion 5

`RESULTS.md`'s selective-accuracy table shows V2-independent-learned's
accuracy at 20-40% coverage (its most confident predictions) is **worse**
than at 100% coverage (0.0% vs. 5.6%) — the opposite of what a useful
confidence signal should do. Two candidate explanations, not distinguished by
this pass's data:

1. **Genuine miscalibration**: the learned model's most-confident predictions
   on Fold C are simply wrong more often, which the AUC=0.529 (barely above
   chance) is also consistent with.
2. **Small-sample instability**: at 20% coverage, "most confident" is only 4
   test-indices — a single flipped outcome moves the reported accuracy by 25
   percentage points. `RESULTS.md`'s own verdict (acquire more data before
   redesigning further) applies here specifically.

## What would resolve this

Everything in `CORPUS_REQUIREMENTS.md`'s recommendation. Two additions
specific to what this error analysis surfaced:

1. **Investigate the 58-way V0/V2 disagreement set specifically** once a
   larger corpus exists — with more examples, "does V2 lose on a particular
   task family" becomes answerable instead of anecdotal (`135a2760` above).
2. **Track singleton-candidate rate as a RUN-002 health metric.** 9.6% of
   RUN-001's test-indices produced only one candidate; if that fraction is
   similar or worse on a future run, it says the 1200s per-task guard is a
   bigger lever on final accuracy than verifier design — worth measuring
   before spending more effort on reranking logic.
