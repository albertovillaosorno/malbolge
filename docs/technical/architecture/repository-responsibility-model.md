# Repository responsibility scaffold

## Status

Proposed

## Purpose

Create the responsibility-oriented topology, mixing implementation languages
inside components and retaining only the minimal root `src/` surface required by
Cargo composition.

## Scope

This document governs the following declared TODO scope:

- `TODO.md`
- `todo/`
- `docs/`
- `algorithms/`
- `compiler/`
- `vm/`
- `execution/`
- `accelerator/`
- `interop/`
- `tests/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`repository-responsibility-scaffold`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The root topology contains only responsibility boundaries that are justified
  by `TODO.md` or accepted documentation; implementation-language-only roots and
  accidental empty directories are absent.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `TODO.md`, `todo/`, `docs/`, `algorithms/`,
  `compiler/`, `vm/`, `execution/`, `accelerator/`, `interop/`, `tests/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
## References

- [Repository Responsibility
  Boundaries](../adr/repository-responsibility-boundaries.md)

### Governing ADR Paths

- `docs/technical/adr/repository-responsibility-boundaries.md`
