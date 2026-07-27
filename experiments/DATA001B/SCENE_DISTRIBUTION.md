# DATA001-B — SCENE_DISTRIBUTION

Scene generator V2 preserves clean structured-scene provenance and adds seven explicit modes:

- `large_grid`: 145+ cell scenes with wide, tall, sparse, and dense variants.
- `high_colour`: 7-10 colour layouts with semantic foreground roles and decoy colours.
- `high_object_count`: 7-20 object scenes with repeated and unique shapes, clustered or dispersed.
- `dense_multi_object`: high occupancy, touching layouts, overlapping bounding boxes, and distractors.
- `panels_and_separators`: row/column panels, uneven panels, separator colours, and recombination layouts.
- `containers_and_nesting`: framed objects, nested containment, and content/outline structure.
- `sequences_and_patterns`: repeated motifs, missing members, period structure, and continuation layouts.

All modes remain deterministic by seed, family-disjoint across train/validation variants, and subject to ambiguity and identity rejection.
