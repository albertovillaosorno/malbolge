# Algorithm Implementations

This directory contains executable algorithm implementations and application
algorithm suites. It is organized by algorithm responsibility, not by
implementation language or hardware.

Two shapes are intentionally supported.

## Research Algorithms

Independent research algorithms keep the established layout:

```text
algorithms/<id>/
|-- experiment.toml
|-- *.rs / *.c / *.py / *.cu
|-- tests/
`-- out/
```

Their matching academic records live under `docs/research/algorithms/`.

## Reusable and Application Algorithms

Repository-wide generative infrastructure and cohesive application pipelines also
live here when algorithm identity is their primary responsibility.

Current examples:

- `algorithms/diff/`: generic source-bound tree-diff generation;
- `algorithms/doom/`: the DOOM quality, amalgamation, adapter, and generator
  family.

Application suites may contain multiple ordered stages under one application
name. Generic engines must remain independent from application policy: DOOM
knowledge belongs under `algorithms/doom/`, never in `algorithms/diff/`.

Generated local artifacts remain under Git-ignored `out/` directories. Local
third-party or user-owned source/oracle trees remain ignored and are never made
repository source merely because a generator consumes them.
