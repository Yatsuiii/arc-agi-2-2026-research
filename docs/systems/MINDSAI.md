# MindsAI — evidence-limited assessment

**No artifact is present in this workspace.** There is no
`references/score_winners/03_*` directory, and `references/kaggle_notebooks/` is
empty. This document records what can and cannot be concluded, and marks every
statement with its evidential status.

## Availability

| Item | Status |
| --- | --- |
| Source code | absent, and historically never open sourced |
| Checkpoints | absent |
| Kaggle notebook | absent |
| Technical report | absent |
| Third-party description | present, indirect (see below) |

MindsAI (Jack Cole, Mohamed Osman, Michael Hodel) led the ARC Prize 2024 private
leaderboard but did not open source, which under ARC Prize rules made them
ineligible for the top prize. That pattern is the reason nothing is downloadable
here.

## What the local evidence does establish

### Test-time fine-tuning originates with them

`references/score_winners/01_nvarc/nvarc_2025.pdf` §1 and reference [2]:

> "To perform well one has to use some form of training on the hidden test set
> (test-time fine-tuning or TTFT). TTFT was used by the winners of a similar
> challenge run two years ago [2]."

Reference [2] is *Jack Cole and Mohamed Osman, "Dataset-induced meta-learning
(and other tricks): Improving model efficiency on ARC", lab42.global, 2023*.

**Status: CONFIRMED by citation.** Every strong 2025 system's central mechanism
traces to this line. That single fact is the most important thing about MindsAI
for our purposes and it is well evidenced.

### Michael Hodel's RE-ARC feeds every system here

`nvarc_2025.pdf` reference [5] and Table 1 (RE-ARC, 400 puzzles, 102,392
samples, 3.2% of the NVARC mix); the ARChitects list RE-ARC first in their
pretraining data. Hodel was a MindsAI team member.

**Status: CONFIRMED.** RE-ARC's procedural generators are a MindsAI-adjacent
contribution that is public and universally used, even though the solver is not.

### The named idea: "dataset-induced meta-learning"

The title of [2] describes the mechanism: fine-tune on a large corpus of ARC-like
tasks so the model learns *how to adapt* from few demonstrations, then adapt at
test time. This is exactly the two-stage structure that NVARC and the ARChitects
both use.

**Status: INFERRED from the title and from downstream citation.** We have not
read the source and must not attribute specifics to it.

## What cannot be concluded

Every one of the 30 teardown questions that requires reading code is
unanswerable: parameter counts, tokenisation, augmentation specifics, number of
candidates, ranking rule, compute allocation, per-task adaptation details,
ablations, hidden-set failure modes.

We will not infer these from other systems' implementations. The ARChitects and
NVARC describe TTT differently from each other (rank 32 / 128 steps versus rank
256 / one epoch), so there is no single "TTT recipe" to attribute backwards.

## Uncertainty markers for the paper

If MindsAI appears in `paper/RELATED_WORK.md` or in the comparison matrix, it
appears as:

- attribution of the TTFT idea, cited through NVARC25 [2], marked as a secondary
  citation until the primary is obtained;
- a row of `UNKNOWN` in every implementation column of
  `docs/SYSTEM_COMPARISON.md`, never as blanks or as imputed values.

## Action to close the gap

Obtain the lab42.global 2023 write-up and any ARC Prize 2024 technical report
section describing MindsAI, and cite the primary source. Neither requires Kaggle
credentials. Recorded as a documentation task, not a blocker.
