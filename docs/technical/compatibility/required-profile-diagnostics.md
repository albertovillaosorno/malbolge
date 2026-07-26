# Required-profile diagnostics

## Status

Proposed

## Purpose

Emit deterministic diagnostics naming the required Malbolge profile/features,
required memory or address capacity, and missing runtime capability. When
`malbolge-1998` is selected, report its 59,049-word ceiling explicitly as a
historical-profile constraint.

## Scope

This document governs the following declared TODO scope:

- `compatibility/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`required-profile-diagnostics`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Programs that require an unsupported target profile fail before unsafe
  execution with deterministic diagnostics naming required
  version/features/memory and the runtime capability that is missing.
- `malbolge-1998` preserves the written 1998 machine exactly; current-language
  behavior and capacity are gated by explicit versioned profile identity.

## Failure Behavior

A profile mismatch or unsupported capability fails with an explicit requirement
diagnostic; current and `malbolge-1998` behavior are never guessed.

## Verification

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: `malbolge-1998` specification-conformance corpus plus
  current/profile boundary fixtures and exact diagnostics.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `scalable-malbolge-memory-model`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
