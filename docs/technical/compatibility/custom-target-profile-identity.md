# Custom target profile identity

## Status

Proposed

## Purpose

Allow user-supplied target profiles with canonical hashing and explicit artifact
identity. Investigate profile-dependent encoding without making a false claim
that reverse engineering can be made cryptographically impossible.

## Scope

This document governs the following declared TODO scope:

- `compatibility/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`custom-target-profile-identity`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Generated artifacts bind to a canonical profile fingerprint; supplying a
  nonmatching external configuration is detected rather than silently
  interpreted under different semantics.
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
- Prerequisite completion evidence: `canonical-malbolge-target-profile`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
