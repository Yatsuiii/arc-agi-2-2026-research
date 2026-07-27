# DATA001-B — DESCRIPTOR_CATALOG

Descriptor system V2 retains DATA001-A compatibility and adds six grouped summaries per task:

1. `grid_scale`: input/output dimensions, cell-count bins, expansion ratio bin, aspect bin, panel count, separator signature.
2. `colour_structure`: colour-count bin, background-confidence bin, entropy bin, preserved/introduced/removed-colour bins, mapping cardinality bin.
3. `object_structure`: 4/8-connectivity component bins, object-area bin, repeated-shape bin, shape-diversity bin, density bin, containment/touching bins, hole bin.
4. `relational_structure`: alignment bin, directionality bin, nearest-neighbour bin, correspondence bin, containment-depth bin, interaction-count bin, graph-degree bin.
5. `transformation_structure`: affected-object bin, shape-preservation class, movement/recolour/copy/delete flags, output-expansion bin, composition-depth bin, conditional/repetition/symmetry/panel-recompose flags.
6. `complexity`: description-length bin, inferred-parameter bin, distractor bin, ambiguity bin, visible-demo-diversity bin, example-minimum bin.

Coverage scoring is frozen as a group-aware match over these descriptor groups, with backward-compatible DATA001-A reporting retained for direct comparison.
