# Required-profile diagnostics

- Status: Proposed
- Planning identity: `required-profile-diagnostics`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

## Purpose

Emit deterministic diagnostics such as `This program requires Malbolge >= 2`,
the required memory size, and the original 59,049-word limit when historical
execution is impossible.

## Proposed Model

This record defines the contract that implementation must satisfy for
`required-profile-diagnostics`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

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

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
