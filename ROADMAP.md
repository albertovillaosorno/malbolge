# Malbolge Roadmap

Generated from `.jig/roadmap.json`; do not edit this projection.

## Project

- Project started: 2026-07-26
- Current milestone: M-002
- Schedule owner: Repository owner
- Last schedule review: 2026-08-10

## Horizons

| ID | Horizon | Lanes |
| -- | ------- | ----- |
| P0 | Authority and governance | 1, 2, 3, 4 |
| P1 | Semantic and language foundations | 5, 6, 7 |
| P2 | Compiler, runtime, and accelerator core | 8, 9, 10 |
| P3 | Optimization, proof, and reusable scale | 11, 12, 13 |
| P4 | Applications, evidence, and self-hosting | 14, 15, 16 |
| P5 | Documentation and publication | 17, 18 |

## Milestones

### M-000 — Repository authority

- Start: 2026-07-26
- Target: 2026-07-26
- Finish: 2026-07-26
- State: completed
- Needs: none

### M-001 — Safe VM baseline

- Start: 2026-07-27
- Target: 2026-08-06
- Finish: 2026-08-06
- State: completed
- Needs: M-000

### M-002 — Compiler and execution core

- Start: 2026-08-07
- Target: 2026-09-30
- Finish: -
- State: active
- Needs: M-001

### M-003 — Verified optimization scale

- Start: 2026-10-01
- Target: 2026-12-31
- Finish: -
- State: planned
- Needs: M-002

### M-004 — Applications and self-hosting

- Start: 2027-01-01
- Target: 2027-06-30
- Finish: -
- State: planned
- Needs: M-003

### M-005 — Publication and historical proof

- Start: 2027-07-01
- Target: 2027-09-30
- Finish: -
- State: planned
- Needs: M-004

## Milestone Notes

- M-000 established repository and historical specification authority.
- M-001 delivered the accepted safe-Rust VM and its deterministic evidence.
- M-002 owns the first complete compiler and exact execution core.
- M-003 scales verified optimization without trusting heuristic components.
- M-004 proves real applications and practical self-hosting.
- M-005 closes reproducible publication and historical demonstration.

## Program Contract

- Defined Malbolge profiles own observable guest semantics.
- Independent deterministic verification accepts generated artifacts.
- Host parallelism never creates guest threads or reorders semantics.
- Source, IR, layout, mutation, and verifier provenance remain explicit.
- Historical compatibility never imports undefined behavior.

## Dependency Rules

- Every milestone has one stable identifier.
- Typed TODO dependencies and lanes remain execution authority.
- Horizons advance only after deterministic verifier evidence exists.
- Search and accelerator results never replace semantic verification.
- Target dates are plans and never completion claims.
