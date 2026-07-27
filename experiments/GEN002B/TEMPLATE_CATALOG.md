# GEN002-B — TEMPLATE_CATALOG

GEN002-B executed **8 template families** before the legacy fallback.

| Stage | Template | Intent |
| --- | --- | --- |
| S2-A | `identity` / rigid whole-grid transform | exact whole-grid geometric transforms |
| S2-A | `crop_non_background` | shrink to the active region under a background hypothesis |
| S2-A | `global_colour_map` | infer colour-role remapping from demonstrations |
| S2-A | `uniform_scale` | infer an integer scale factor shared across demonstrations |
| S2-A | `tile_input` | infer exact row/column repetition counts |
| S2-A | `overlay_{horizontal,vertical}_mirror` | symmetry completion by input-plus-mirror overlay |
| S2-B | `single_object_translate` | preserve one object's shape while inferring a translation vector |
| S2-B | `largest_object_crop` | select and crop the dominant object |

Template-first search remained typed and executable: every candidate
template instance had a canonical serialization, a fixed cost, and an
exact-demonstration consistency gate before test-time emission.
