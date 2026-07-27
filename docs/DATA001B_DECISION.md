# DATA001-B — DECISION

## Verdict

ADOPT COVERAGE-FIRST SYNTHETIC PIPELINE

## Why

- Clean architecture, provenance, schemas, and leakage firewall were preserved from DATA001-A.
- Against the frozen DATA001-A gate used for this phase, the selected corpus reached weighted failure-set coverage 0.147 versus the baseline 0.047 and reduced mean nearest-structure distance to 1.887 from 1.977.
- No exact or structural leakage was admitted.
- The selected corpus remains operationally feasible for a bounded future 4B QLoRA pilot.

## Next phase

Launch MODEL001-A with the frozen direct-grid pilot first.
