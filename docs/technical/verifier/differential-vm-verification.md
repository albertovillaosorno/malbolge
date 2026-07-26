# Differential VM verification

- Status: Proposed
- Planning identity: `differential-vm-verification`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Run the original C oracle, modern Rust VM, modern C VM, and accelerator VM on
the same valid programs and inputs and compare output, termination, state,
mutation, and instruction traces where defined.

## Proposed Model

This record defines the contract that implementation must satisfy for
`differential-vm-verification`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The historical oracle, independent C VM, and Rust VM agree on all admitted
  classic fixtures; disagreements shrink to reproducible minimal cases and block
  compatibility claims.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
