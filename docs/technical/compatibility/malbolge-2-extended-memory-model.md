# Malbolge 2 extended memory model

- Status: Proposed
- Planning identity: `malbolge-2-extended-memory-model`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../adr/historical-compatibility-and-malbolge-evolution.md)

## Purpose

Remove the practical 59,049-word ceiling through an explicit extension while
preserving original behavior for programs inside the historical machine. Define
multiword or paged addressing without pretending a ten-trit word can directly
address arbitrary memory.

## Proposed Model

This record defines the contract that implementation must satisfy for
`malbolge-2-extended-memory-model`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The extension permits logical addresses beyond 59048 while preserving classic
  10-trit arithmetic/crazy/rotate behavior and observational identity for
  programs that remain inside classic bounds.
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
