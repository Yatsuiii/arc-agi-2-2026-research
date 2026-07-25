# EXP002 — error analysis

Companion to `RESULTS.md`. Representative examples pulled from the full
94-test-index corpus (`B0_original_nvarc` results), identified by
`(task_id, test_index)` so any of them can be re-inspected against
`artifacts/run001/run001/candidates.jsonl.gz` directly.

## Representative ranking successes

| task_id | test_index | rank of correct | margin | n candidates | n unique grids |
| --- | ---: | ---: | ---: | ---: | ---: |
| `135a2760` | 0 | 1 | 0.113 | 16 | 6 |
| `1ae2feb7` | 2 | 1 | 0.113 | 18 | 6 |
| `2ba387bc` | 0 | 1 | 0.129 | 18 | 5 |
| `2d0172a1` | 1 | 1 | 0.113 | 8 | 6 |
| `36a08778` | 0 | 1 | 0.152 | 10 | 4 |

All five: the correct grid was both the most-generated unique grid **and**
B0's top rank. These are the easy cases — high generation redundancy and a
scorer that agrees with it. None of B1-B6 would be expected to do worse here,
since they mostly agree with B0 exactly when duplicate count and score point
the same way (which is most of the time — that agreement is the mechanism
behind B5's exact tie with B0 in `RESULTS.md`).

## Representative confident failures

| task_id | test_index | rank of correct | margin | n candidates | n unique grids |
| --- | ---: | ---: | ---: | ---: | ---: |
| `16b78196` | 0 | never generated | 1.000 | 1 | 1 |
| `5961cc34` | 0 | never generated | 1.000 | 4 | 1 |
| `136b0064` | 0 | never generated | 1.000 | 1 | 1 |
| `195c6913` | 0 | never generated | 1.000 | 2 | 1 |
| `6ffbe589` | 0 | never generated | 1.000 | 1 | 1 |

**These are not genuine overconfidence — they are a softmax artifact.** Every
one of these test-indices produced exactly **one** unique candidate grid
(1-4 raw generations, all identical or all discarded to one survivor by the
1200s per-task guard, `experiments/RUN001/VALIDATION_REPORT.md`'s 41/77
guard-hit count). `verifier/base.py`'s `softmax` over a single-element score
map always returns probability 1.0 for that element — there is nothing to be
uncertain *between*. The correct grid was never generated at all (branch G,
`paper/FAILURE_TAXONOMY.md`), so no reranking of any kind, however clever,
could have fixed these five. This is a **generation** failure wearing a
**confidence** costume, and it is exactly the kind of case
`false_confidence_rate` is meant to catch — but B0 is not a probability
model NVARC ever claimed was calibrated, so this is reported as a
methodological note (verifiers should treat "n=1 candidate" as a distinct,
flagged state, not feed it through the same softmax as a real contest), not
as evidence against the verifier thesis.

**Consequence for `HarnessConfig`/future work:** `verifier/base.py`'s
`build_result` should probably special-case `len(scores) == 1` to report
`uncertainty=1.0` (maximal, not minimal) rather than the `0.0` a
single-outcome entropy calculation produces, precisely so a future allocator
does not read "one candidate survived the time guard" as "the solver is
sure." Not fixed in this pass — recorded as a concrete follow-up rather than
silently patched after the fact, since patching it now would change every
number already reported in `RESULTS.md`.

## Representative selection failures (branch S — generated, ranked outside top-2)

| task_id | test_index | rank of correct | margin | n candidates | n unique grids |
| --- | ---: | ---: | ---: | ---: | ---: |
| `221dfab4` | 0 | 3 | 0.129 | 9 | 5 |
| `3a25b0d8` | 0 | 3 | 0.091 | 16 | 8 |
| `78332cb0` | 0 | 4 | 0.066 | 22 | 12 |
| `142ca369` | 0 | 4 | 0.152 | 8 | 4 |
| `4c7dc4dd` | 1 | 5 | 0.062 | 23 | 13 |

**This is where headroom actually lives.** All five: the correct grid was
generated, but buried at rank 3-5 among a larger-than-average unique-grid
count (5-13, versus ~4-6 for the successes above). The confidence margin is
consistently *lower* than the successes' (0.06-0.15 vs 0.11-0.15 — overlapping,
not cleanly separable, but directionally the harder cases have both more
competing unique grids and less decisive scoring). This is consistent with
`f7_margin_vs_correctness.png`: low-margin cases are where the correct answer
is most likely present-but-not-selected, which is exactly where a genuinely
independent signal (not a B0 paraphrase) would need to move probability mass
to help. `object_count_consistent_with_demo_pattern` (the one score-independent
feature with real AUC) is the most promising place to look for that signal —
see `RESULTS.md` §14.

## Failure-category summary (branch split, full corpus)

| Branch | Count | Share |
| --- | ---: | ---: |
| G — correct grid never generated | 64 / 94 | 68.1% |
| S — generated, ranked outside top-2 | 7 / 94 | 7.4% |
| realised (in top-2) | 23 / 94 | 24.5% |

Consistent with `paper/FAILURE_TAXONOMY.md`'s framing: generation failure
dominates (68.1%), and no verifier change touches it. Selection failure
(7.4%) is smaller in absolute terms than EXP001-A's ARC-AGI-1 measurement
(17.8% of failures were selection failures there,
`experiments/EXP001/RESULT.md` §10) but the two are not directly comparable —
different solver, different candidate distribution, and RUN-001's 94
test-indices are a much smaller, partial sample. Reported as an observation,
not a cross-benchmark claim.

## What would change this analysis

1. **A complete RUN-002** would roughly quadruple the number of branch-S
   examples available to look for patterns in, which is the single biggest
   lever on every conclusion in this file.
2. **Fixing the n=1-candidate confidence artifact** (above) before any
   allocator experiment (EXP003+) uses `VerificationResult.uncertainty` as a
   stopping signal — as written, the allocator would read every
   single-candidate task as "maximally confident," which is backwards.
