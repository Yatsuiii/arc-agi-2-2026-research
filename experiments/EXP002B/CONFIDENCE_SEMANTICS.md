# EXP002-B Part 1 — confidence-semantics bug and repair

## The bug

`experiments/EXP002/ERROR_ANALYSIS.md` ("Representative confident failures")
found it first: five test-indices where `B0_original_nvarc` reported
`confidence_margin = 1.000` and was still wrong. All five had exactly **one**
unique generated candidate. `verifier/base.py`'s original `build_result`
always ran the scores dict through `softmax`, and softmax over a single
element is `{that_element: 1.0}` by construction — there is no alternative
for it to lose probability mass to. The number was answering "does this
candidate outrank the others" (trivially yes, there are none) while every
caller was reading it as "is this candidate correct" (no evidence either
way). Those are different questions and the old schema had one field,
`probability_correct`, forced to answer both at once.

## Why this matters beyond one metric

`experiments/EXP002/PLAN.md` names calibrated confidence as the precondition
for EXP003 (early stopping) and EXP004 (compute allocation) — the harness
brief's own Gate 1 exists because building an allocator around an
uninformative confidence signal wastes the work. A stopping rule that reads
"1 unique candidate -> confidence 1.0" as license to stop early would stop
on exactly the tasks that most need more compute: the ones that produced
so little diversity that a time guard likely cut generation short, not the
ones that converged on a genuinely well-supported answer.

## The fix

`schemas.VerificationResult` gains five fields (`src/harness/schemas.py`):

| Field | Answers | For a singleton candidate set |
| --- | --- | --- |
| `ranking_confidence` | "Does the top candidate outrank the alternatives present?" | **1.0, correctly** — there are no alternatives to lose to, and this is a true statement, not a bug |
| `correctness_confidence` | "Is the top candidate actually correct?" | **backed off to an empirical prior**, never 1.0 from the mere absence of competition |
| `candidate_set_sufficiency` | "Is there enough evidence here to trust a ranking at all?" | **0.0** |
| `abstain` | "Should a caller treat this ranking as meaningful?" | **True** |
| `uncertainty_reason` | Why, in words | states the candidate count and that a prior was substituted |

`probability_correct` is kept for backward compatibility with the first
EXP002 pass's code and tests; it now equals whichever of the two questions
above a given verifier is actually positioned to answer (heuristic verifiers:
ranking; calibrated verifiers: correctness), and `uncertainty_reason` says
which.

### Sufficiency, precisely

`verifier/base.py::_sufficiency`:

```
effective_count = exp(entropy(softmax(scores)))     # features/uncertainty.py's own metric
sufficiency = 0                                       if n <= 1
            = min(1, (effective_count - 1) / 2)        otherwise
```

`effective_count` (not raw grid count) is deliberate: two duplicate copies of
the same grid and two genuinely different grids both count as "2 unique
sha1s" in the naive sense, but only the latter contributes real ranking
evidence. Using the softmax distribution's own entropy means a score
distribution concentrated on one grid (near-duplicate candidates that differ
in a way the scorer doesn't distinguish) still reports low sufficiency even
with several nominal "unique" grids present.

### Abstention threshold

`abstain = True` exactly when there are 0 or 1 unique candidates —
deliberately not a softer threshold on `sufficiency` itself. Two candidates,
however close, are two independent pieces of evidence (`candidate_set_sufficiency`
correctly reports that as low but nonzero); one candidate is zero pieces of
evidence, categorically, and that categorical distinction is what the bug
conflated with a continuous confidence number.

### The empirical prior

`singleton_prior` is a parameter on both builders (`build_result`,
`build_result_from_probabilities`), defaulting to `DEFAULT_SINGLETON_PRIOR =
0.5` ("no information") when a caller supplies nothing. `src/analysis/exp002b_verifier_eval.py`
passes the corpus's own measured oracle rate (computed on Fold A, never on
the fold being evaluated) instead of the uninformative default, so a
singleton candidate set's `correctness_confidence` reflects "how often is a
lone survivor of RUN-001's time guard actually correct, empirically" rather
than an arbitrary constant. See `RESULTS.md` §"singleton false-confidence
result" for the measured value and what it implies.

## Test coverage

`tests/harness/test_confidence_semantics.py`, 13 tests, covering:

1. **one unique wrong candidate** / **one unique correct candidate** — the
   verifier cannot and must not tell these apart (ground truth is not an
   input to `rank()`); both must receive the identical prior-backed
   `correctness_confidence`, proven by construction rather than by checking
   against a label.
2. **many duplicate generations of one unique candidate** — vote count does
   not manufacture sufficiency; still abstains.
3. **two near-tied candidates** — nonzero but low sufficiency, lower
   `ranking_confidence` than a clear winner.
4. **candidate set whose native score is high but structural evidence
   contradicts it** — exercised at the verifier-comparison level once V1
   (native-score) and V2 (structural, score-independent) exist side by side;
   see `experiments/EXP002B/RESULTS.md` for a real instance from the RUN-001
   corpus where V1 and V2 disagree.
5. **agreement across independent transformations** — `features/uncertainty.py`'s
   `seed_disagreement`/`solver_disagreement` already return `None` rather than
   a fabricated number when RUN-001's archive has nothing to disagree across
   (one TTT seed, one solver branch); unchanged by this fix, and still true.

## What is explicitly not fixed here

`correctness_confidence` for a **non-singleton** heuristic verifier (2+
unique candidates, no fitted calibration) is still just the softmax
distribution, flagged `"correctness_confidence is uncalibrated"` in
`uncertainty_reason` rather than corrected — there is no ground truth
available inside `rank()` to calibrate against, and manufacturing a
calibration mapping without labels would be a second, quieter version of the
same bug. Only `LearnedVerifier` (fit on labelled data, `verifier/learned.py`)
and `PlattCalibrator` (`verifier/calibration.py`) produce genuinely calibrated
`correctness_confidence`, and only on data disjoint from what they were fit
on.
