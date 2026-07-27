# GEN002-B — PRIMITIVE_CATALOG

Executable V2 surface frozen for this phase.

| Level | Operation | Type sketch | Cost | Failure behaviour | Basis |
| --- | --- | --- | ---: | --- | --- |
| 0 | `identity` | `Grid -> Grid` | 1 | never | canonical ARC baseline |
| 0 | `rotate_90` | `Grid -> Grid` | 1 | never | standard grid symmetry |
| 0 | `rotate_180` | `Grid -> Grid` | 1 | never | standard grid symmetry |
| 0 | `rotate_270` | `Grid -> Grid` | 1 | never | standard grid symmetry |
| 0 | `reflect_horizontal` | `Grid -> Grid` | 1 | never | standard grid symmetry |
| 0 | `reflect_vertical` | `Grid -> Grid` | 1 | never | standard grid symmetry |
| 0 | `reflect_diagonal` | `Grid -> Grid` | 1 | requires square-grid tasks to match exactly | standard grid symmetry |
| 0 | `crop_non_background` | `Grid x Background -> Grid` | 2 | empty foreground drops the program | object-centric ARC practice |
| 0 | `global_colour_map` | `Grid x Mapping -> Grid` | 2 | inconsistent train mapping drops the program | colour-role abstraction |
| 0/3 | `uniform_scale` | `Grid x Integer -> Grid` | 3 | inconsistent factor drops the program | recurrent TRAIN scaling tasks |
| 0/3 | `tile_input` | `Grid x Integer x Integer -> Grid` | 3 | inconsistent tile counts drops the program | recurrent TRAIN tiling tasks |
| 1 | `largest_object_crop` | `Grid x Background x Connectivity -> Grid` | 4 | no objects drops the program | object-centric ARC systems |
| 2 | `single_object_translate` | `Grid x Background x Connectivity x Delta -> Grid` | 5 | non-singleton or shape mismatch drops the program | object correspondence family |
| 3 | `overlay_vertical_mirror` | `Grid -> Grid` | 4 | shape mismatch drops the program | symmetry completion |
| 3 | `overlay_horizontal_mirror` | `Grid -> Grid` | 4 | shape mismatch drops the program | symmetry completion |
| 4 | `legacy_gen002_fallback` | typed GEN002 AST -> Grid | inherited | search/execution failure drops the program | bounded compositional backstop |

Supporting evidence:

- `uniform_scale` solved TRAIN task `c59eb873` on the frozen benchmark.
- `legacy_gen002_fallback` solved TRAIN task `f25fbde4` through the exact
  program `crop(scale(input,lit:Integer:2))`.
- Remaining operators are supported by recurring TRAIN/DEV pattern
  families and the selected symbolic lineage audit, but did not change the
  fresh validation result.
