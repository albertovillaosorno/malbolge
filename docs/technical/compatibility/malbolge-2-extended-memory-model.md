# Malbolge 2 extended memory model

## Status

Proposed

## Purpose

Remove the practical 59,049-word ceiling through an explicit extension while
preserving normative 1998 specification behavior for programs inside the classic
machine. Define multiword or paged addressing without pretending a ten-trit word
can directly address arbitrary memory.

## Scope

This document governs the following declared TODO scope:

- `compatibility/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`malbolge-2-extended-memory-model`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The extension permits logical addresses beyond 59048 while preserving classic
  10-trit arithmetic/crazy/rotate behavior and observational identity for
  programs that remain inside classic bounds.
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
  `safe-rust-malbolge-vm`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
