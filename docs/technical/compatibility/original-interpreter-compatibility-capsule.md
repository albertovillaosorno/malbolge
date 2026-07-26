# Original-interpreter compatibility capsule

- Status: Proposed
- Planning identity: `original-interpreter-compatibility-capsule`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../adr/historical-compatibility-and-malbolge-evolution.md)

## Purpose

Design an extended `.malbolge` container recognized by modern runtimes while the
1998 loader sees only a valid classic fallback, ideally using whitespace
metadata that the original loader ignores.

## Proposed Model

This record defines the contract that implementation must satisfy for
`original-interpreter-compatibility-capsule`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- One `.malbolge` capsule makes the historical interpreter execute only the
  classic fallback while the modern runtime recognizes and validates the
  whitespace extension payload deterministically.
- Classic programs inside the original defined domain remain observationally
  identical while extension-only behavior is gated by explicit profile identity.

## Failure Behavior

A profile mismatch or unsupported extension fails with an explicit requirement
diagnostic; classic behavior is never guessed.

## Verification

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: classic compatibility corpus plus extension/profile
  boundary fixtures and exact diagnostics.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
