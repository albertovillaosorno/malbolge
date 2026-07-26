# Required-profile diagnostics

## Status

Proposed

## Purpose

Emit deterministic diagnostics such as `This program requires Malbolge >= 2`,
the required memory size, and the original 59,049-word limit when historical
execution is impossible.

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
- Classic programs preserve normative 1998 specification behavior while
  extension-only behavior is gated by explicit profile identity.

## Failure Behavior

A profile mismatch or unsupported extension fails with an explicit requirement
diagnostic; classic behavior is never guessed.

## Verification

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: classic specification-conformance corpus plus
  extension/profile boundary fixtures and exact diagnostics.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `malbolge-2-extended-memory-model`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
