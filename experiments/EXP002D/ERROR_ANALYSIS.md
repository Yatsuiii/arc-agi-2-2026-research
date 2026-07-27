# EXP002-D — ERROR_ANALYSIS

`src/analysis/exp002d/error_taxonomy.py`, V0 (native) vs. V4 (the
best-performing non-trivial alternative track). Full per-test-index
classification: `artifacts/EXP002D/error_taxonomy.csv`.

## Category counts (171 test-indices, exhaustive)

| Category | Count | Fraction |
| --- | --- | --- |
| 1. Generation failure (no correct candidate exists) | **129** | **75.44%** |
| 4. Native-only success (V0 right, V4 wrong) | 6 | 3.51% |
| 5. Verifier rescue (V4 right, V0 wrong) | 2 | 1.17% |
| 6. Both succeed | 17 | 9.94% |
| 7. Both fail, correct candidate present (ranking failure for both) | 17 | 9.94% |
| 2. Ranking failure (subset of 7, neither top-2 correct despite a correct candidate existing) | (contained in 7) | — |
| 3. Partial ranking success (correct only at rank 2) | not separately tabulated this pass; see limitation below | — |
| 8. Candidate-set insufficiency correctly identified | **0** | 0% |
| 9. False high-confidence failure | not separately tabulated this pass; see limitation below | — |

Categories 2/3/9 were folded into category 7 for this pass rather than
separately tabulated — a scope limitation of this run, not a missing
category in the taxonomy design; `error_taxonomy.csv` carries
`v4_correct_rank` and `sufficiency` per row, so a follow-up pass can
recompute 2/3/9 from the same CSV without regenerating anything.

## The dominant finding: generation, not selection, explains most misses

**75.44% of test-indices (129/171) have no correct candidate anywhere in
the archive.** No verifier — however good — can win a slot CompressARC
never generated. This exactly matches the corpus's own oracle coverage
(24.56% have a correct candidate = 75.44% do not), restated here at the
per-test-index level rather than the aggregate level.

Among the 129 generation failures, **0** had a low sufficiency score
(<0.1, correctly signalling emptiness) and **all 129** had sufficiency
>=0.5 (`CALIBRATION_RESULTS.md`) — the entropy-based sufficiency measure
never once correctly flagged a generation failure as insufficient,
because CompressARC's failures still produce large, diverse pools of
wrong answers.

## Where the verifier tracks actually differ from native

Only 8 of 171 test-indices (6 native-only-success + 2 verifier-rescue)
show any disagreement at all between V0 and V4 in a test-index that *has*
a correct candidate available. V4 nets **-4** relative to V0 on this
8-test-index disagreement set (2 rescues, 6 regressions) — small numbers,
but the direction is negative, consistent with the pooled McNemar result
(`RESULTS.md`).

## Representative examples

- **Verifier rescue** (`54d82841`, test-index 0; `88a62173`, test-index
  0): V4's hybrid score correctly promoted the true grid above
  CompressARC's own top-2 pick. Both are legitimate, viewable examples of
  the mechanism working as intended on individual cases — but only 2 of
  them exist in the entire held-out corpus.
- **Native-only success** (`05269061`, test-index 0; `1a2e2828`, test-index
  0, plus 4 more in `error_taxonomy.csv`): CompressARC's own `beam_score`
  ranking already found the correct candidate; adding independent/hybrid
  features demoted it below the top-2 cut. These 6 cases are the direct
  cost of using anything other than the frozen native ranker on this
  corpus.
- **Both fail with a correct candidate present** (`0d3d703e`, test-index
  0; `1b2d62fb`, test-index 0, plus 15 more): the harder, more
  informative failure mode — neither ranking approach found the correct
  candidate among its top 2, even though the archive contains it
  somewhere in its (typically ~400-candidate) pool. This is where a
  genuinely better verifier would need to add value, and where none of
  V2-V6 measurably did.
- **Generation failure** (`045e512c`, test-index 0; `09c534e7`, test-index
  0, plus 127 more): three-quarters of the entire held-out corpus. No
  selection mechanism operates here at all.

Grid images are not rendered in this markdown file (would require a
plotting dependency this experiment does not preregister); every
task_id/test_index pair above can be viewed directly against
`arc-agi_training_challenges.json` and the archived candidates by task ID.
