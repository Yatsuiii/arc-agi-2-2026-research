# DATA001-A — GENERATOR_SPEC

## Core design

The generator produces ARC-like tasks from structured scene programs
rather than random-pixel mutation or free-form Python synthesis.

Each accepted task must include:

- a typed executable transformation program;
- two to five visible training pairs;
- one or more test inputs with generated outputs;
- transformation-family labels;
- difficulty metadata;
- deterministic seeds;
- provenance;
- canonical hashes.

## Representation

Programs are serialized as a structured abstract syntax tree with typed
operations and explicit parameters. The representation must support:

- grid operations such as crop, overlay, mask, recolor, tiling, and
  layout changes;
- object extraction and transformation;
- colour-role transformation rather than only raw colour IDs;
- spatial and relational transformations;
- repetition and bounded composition;
- symmetry and pattern completion;
- line and ray operations.

## Scene generation

Source scenes are built from reusable scene descriptors supporting:

- varied grid dimensions;
- multiple colour roles and background choices;
- connected objects and repeated motifs;
- containers, separators, and panels;
- symmetric structures;
- sparse and dense layouts;
- distractors and relation-bearing objects.

## Acceptance gates

A generated task is accepted only if:

- the program executes successfully on every pair;
- demonstrations support a single intended rule;
- outputs stay within ARC size constraints;
- the task is not degenerate, trivial, or accidentally identity;
- the task passes contamination checks;
- no unintended alternative program collapses the task into a different
  simpler family under the local validity heuristics.
