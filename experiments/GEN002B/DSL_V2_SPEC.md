# GEN002-B — DSL_V2_SPEC

GEN002-B V2 is a narrow, executable typed language and template layer,
frozen before the fresh validation run. It is explicitly smaller than the
full wishlist in the phase brief; the point of this pass was to test
whether a modest structured redesign could already move the held-out pilot.

## Executable surface

The implemented surface has **12 core operations** grouped across the
required abstraction levels, plus **8 executable templates** that compose
them.

### Level 0 — Grid operations

- identity
- rotate 90 / 180 / 270
- reflect horizontal / vertical / diagonal
- crop non-background region
- global colour-role map
- uniform scale
- tile input

### Level 1 — Object operations

- extract a single object under `(background, connectivity)` hypotheses
- crop the largest extracted object

### Level 2 — Relational operations

- infer single-object correspondence by preserved shape and translation

### Level 3 — Pattern operations

- uniform scaling as a pattern transform
- exact tiling
- symmetry completion by input-plus-mirror overlay

### Level 4 — Control and composition

- choose among multiple background hypotheses
- choose among 4- and 8-connectivity segmentation hypotheses
- deterministic stage ordering `S2-A -> S2-B -> S2-C`
- bounded legacy compositional fallback search

## Semantics

Every executable operation is:

- deterministic;
- pure over the provided grid(s);
- serializable through a canonical program string;
- assigned a fixed cost;
- dropped on failure rather than allowed to raise uncaught exceptions in
  the search loop.

## Known omissions

Not implemented in this V2 pass:

- separator/panel solve-and-recombine;
- explicit graph rewrite over multi-object scenes;
- line/ray propagation;
- recursive repetition counting;
- conditional multi-stage programs richer than the fixed stage routing;
- learned or heuristic parameter ranking beyond exact-demo consistency.

These omissions are deliberate and are part of the interpretation of the
fresh validation null.
