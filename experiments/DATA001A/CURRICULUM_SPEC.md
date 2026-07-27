# DATA001-A — CURRICULUM_SPEC

## Curriculum tiers

### Tier 1 — Single transformation

Primitive one-step families such as:

- recolouring;
- translation;
- reflection;
- rotation;
- cropping;
- object deletion;
- object copying;
- bounding-box operations;
- simple symmetry completion.

### Tier 2 — Parameter inference

Tasks where the visible pairs require inference of:

- displacement;
- scale;
- colour-role mapping;
- repetition count;
- selected object attributes.

### Tier 3 — Relational transformation

Tasks driven by object relations such as:

- move relative to another object;
- modify contained objects;
- connect selected objects;
- copy according to correspondence;
- transform objects satisfying a relation.

### Tier 4 — Composition

Typed composition of two or three general transformations with explicit
compatibility constraints and bounded search depth in the generator.

### Tier 5 — Distractors and ambiguity control

Addition of irrelevant surface variation while preserving a single
demonstration-supported rule.

## Balance target

The pilot aims for a broad spread across tiers and transformation
families. Exact balance is not forced if validity gates make it
unrealistic; the achieved distribution must be reported honestly.

## Quality gates

Each family requires automatic validity tests covering:

- executability;
- demonstration consistency;
- nontriviality;
- controllable ambiguity;
- contamination screening.
