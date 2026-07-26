# Custom target profile identity

- Status: Proposed
- Planning identity: `custom-target-profile-identity`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

## Purpose

Allow user-supplied target profiles with canonical hashing and explicit artifact
identity. Investigate profile-dependent encoding without making a false claim
that reverse engineering can be made cryptographically impossible.

## Proposed Model

This record defines the contract that implementation must satisfy for
`custom-target-profile-identity`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Generated artifacts bind to a canonical profile fingerprint; supplying a
  nonmatching external configuration is detected rather than silently
  interpreted under different semantics.
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
