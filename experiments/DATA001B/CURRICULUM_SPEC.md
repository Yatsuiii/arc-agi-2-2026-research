# DATA001-B — CURRICULUM_SPEC

## Frozen scene modes

1. large-grid sparse
2. large-grid dense
3. high-colour role-structured
4. high-object-count clustered
5. high-object-count dispersed
6. dense touching / near-touching multi-object
7. panels and separators
8. containers and nesting
9. sequences and repeated motifs

## Frozen family set

Twelve general families:

- F1 multi-object shape-preserving movement
- F2 object correspondence
- F3 relational selection
- F4 dense object rearrangement
- F5 panel transformation
- F6 large output construction
- F7 multi-colour role mapping
- F8 container and content transformation
- F9 pattern and sequence completion
- F10 graph rewrite
- F11 occlusion and partial-shape completion
- F12 conditional multi-stage composition

## Frozen composition policy

Accepted-task target:

- depth 1: approximately 40%
- depth 2: approximately 40%
- depth 3: approximately 20%

Both syntactic and effective depth are tracked. No-op or visibly
redundant compositions do not count toward depth.

## Frozen pool-generation budget

- Attempt budget: `32000`
- Valid-pool target: at least `25000`
- Family-balanced attempt scheduling with extra weight on descriptor
  regions underrepresented in DATA001-A.

## Frozen final-corpus target

- target size: `10000`
- allowed band: `8000-12000`
- family-disjoint validation split
- direct-grid token budget under `24M`
- rare-family minimum representation is mandatory
